"""Turnover reduction for the SYY and within-sector value sleeves (point-in-time S&P 500, Zero costs).

1. Exit buffer: a name already held stays while its rank is within the best B (SYY: B of the
   whole universe, value: B of its sector group); free slots are filled with the best names
   (SYY keeps the 3-per-sector cap). B = book size is the current rule.
2. Rebalance frequency: the book is reformed every 1, 2 or 3 months; in between only names that
   drop out of the panel (delisted, left the index, no price) are replaced.
Inputs are the monthly panels already built: results/recent/pit/panel.parquet (SYY score M) and the
value panel of sector_value.py. Costs: half spread + commission on names that change (x2: the
name sold and the one bought), ETF hedge changes for value; same withholding as the base runs.
Output: results/recent/rotacion/{resumen.csv, retornos.csv}.
"""
import numpy as np
import pandas as pd
import yfinance as yf

import data
import recent_backtest as rb
import sector_value as sv
from darwinex_sim import COMM, DIV_WHT
from repo_xbrl import universe
from sector_hedge import ETF, START

OUT = data.ROOT / "results" / "recent" / "rotacion"
REC = data.ROOT / "results" / "recent"


def syy_book(f, held, buf, cap=3, n=10):
    f = f.sort_values("M", ascending=False)
    rank = pd.Series(np.arange(1, len(f) + 1), index=f.index)
    keep = [c for c in held if c in rank.index and rank[c] <= buf]
    cnt = f.loc[keep].sector.value_counts().to_dict()
    book = list(keep)
    for c, row in f.iterrows():
        if len(book) == n:
            break
        if c not in book and cnt.get(row.sector, 0) < cap:
            book.append(c)
            cnt[row.sector] = cnt.get(row.sector, 0) + 1
    return book


def run_syy(buf, every):
    pan = pd.read_parquet(REC / "pit" / "panel.parquet")
    spy = pd.read_csv(REC / "pit" / "monthly.csv", index_col=0, parse_dates=True).spy
    spr = (universe().drop_duplicates("cik").set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()
    out, rot, held = {}, {}, []
    for i, (t, f) in enumerate(pan.groupby("date")):
        f = f.copy()
        if i % every == 0:
            book = syy_book(f, held, buf)
        else:                                   # hold; replace only names that disappeared
            keep = [c for c in held if c in f.index]
            book = syy_book(f, keep, len(f)) if len(keep) < 10 else keep
        new = [c for c in book if c not in held]
        to = len(new) / len(book) if held else 1.0
        cost = 2 * to * ((np.mean([spr.get(c, 0.0008) for c in new]) if new else 0) + rb.COMM)
        out[t] = spy.loc[t] - f.fwd[book].mean() - cost - rb.DIV_WHT_SPY
        rot[t] = to
        held = book
    return pd.Series(out), pd.Series(rot)


def run_value(buf, every, k=3):
    p = sv.load_panel()
    pct = pd.concat([p.groupby(["date", "grupo"])[v].rank(pct=True) for v in sv.VAL], axis=1)
    p["V"] = pct.mean(axis=1).where(pct.notna().sum(axis=1) >= 3)
    p = p.dropna(subset=["V"])
    spr = (universe().drop_duplicates("cik").set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()
    dx = pd.read_csv(data.DATA / "darwinex" / "spread_history.csv").set_index("symbol")
    tick = sorted(set(ETF.values()) | {"SPY"})
    px = yf.download(tick, start="2011-12-01", auto_adjust=True, progress=False)["Close"].resample("ME").last()
    efwd = px.pct_change(fill_method=None).shift(-1)
    ecost = {e: dx.avg_spread_bps.get(e, 3.0) / 2 / 1e4 + 0.02 / dx.last_price.get(e, 100.0) for e in tick}

    def etf_for(s, t):
        e = ETF.get(s, "SPY")
        return e if (e not in START or t >= pd.Timestamp(START[e])) and pd.notna(efwd.at[t, e]) else "SPY"

    out, rot, held, ph = {}, {}, {}, pd.Series(dtype=float)
    dates = [t for t in sorted(p.date.unique()) if t in efwd.index]
    for i, t in enumerate(dates):
        g = p[p.date == t].set_index("cik")
        book = {}
        for grp, gg in g.groupby("grupo"):
            if len(gg) < 4 * k:
                continue
            o = gg.V.sort_values(ascending=False)
            rank = pd.Series(np.arange(1, len(o) + 1), index=o.index)
            prev = [c for c in held.get(grp, []) if c in rank.index]
            if i % every == 0:
                keep = [c for c in prev if rank[c] <= buf]
            else:
                keep = prev
            book[grp] = keep + [c for c in o.index if c not in keep][:k - len(keep)]
        names = [c for b in book.values() for c in b]
        L = g.loc[names]
        w = pd.Series(1 / len(L), index=L.index)
        hw = pd.Series(1 / len(L), index=[etf_for(s, t) for s in L.sector]).groupby(level=0).sum()
        pw = pd.Series({c: 1 / sum(len(b) for b in held.values()) for b in held.values() for c in b}) \
            if held else pd.Series(dtype=float)
        turn = w.sub(pw, fill_value=0).abs()
        hturn = hw.sub(ph, fill_value=0).abs()
        cost = sum(turn[c] * (spr.get(c, 0.0008) + COMM) for c in turn.index) + \
            sum(hturn[e] * ecost[e] for e in hturn.index)
        out[t] = L.fwd.mean() - sum(hw[e] * efwd.at[t, e] for e in hw.index) - cost - DIV_WHT
        rot[t] = turn.sum() / 2
        held, ph = book, hw
    return pd.Series(out), pd.Series(rot)


def summary(s, r, leg_usd):
    s = s.loc["2012":]
    eq = (1 + s).cumprod()
    to = r.iloc[1:].mean()
    return {"%/año": 100 * 12 * s.mean(), "sharpe": s.mean() / s.std() * np.sqrt(12),
            "max_dd_%": 100 * (eq / eq.cummax() - 1).min(), "rotación_%mes": 100 * to,
            "USD_operados/año": 2 * to * 12 * leg_usd}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    units = pd.read_csv(REC / "asignacion_carver.csv", index_col=0).unidades * 1_000_000
    rows, rets = [], {}
    for buf, every in [(10, 1), (12, 1), (15, 1), (20, 1), (30, 1), (10, 2), (10, 3), (15, 2)]:
        s, r = run_syy(buf, every)
        name = f"SYY: salir si puesto >{buf}, rebalanceo cada {every} m"
        rets[name] = s
        rows.append({"cartera": name, **summary(s, r, units["SYY"])})
        print(rows[-1], flush=True)
    for buf, every in [(3, 1), (4, 1), (5, 1), (7, 1), (3, 2), (3, 3), (5, 2)]:
        s, r = run_value(buf, every)
        name = f"value: salir si puesto >{buf} del grupo, rebalanceo cada {every} m"
        rets[name] = s
        rows.append({"cartera": name, **summary(s, r, units["value"])})
        print(rows[-1], flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "resumen.csv", index=False, float_format="%.4f")
    pd.DataFrame(rets).to_csv(OUT / "retornos.csv", float_format="%.5f")
    pd.set_option("display.width", 250)
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
