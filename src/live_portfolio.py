"""Weekly orders for the whole Darwinex Zero account: SYY + within-sector value + RSP trend (beta).

Sizes come from the Carver allocation (results/recent/asignacion_carver.csv, units per unit of
equity; see carver_allocation.py):
  SYY    10 overpriced shorts (live_syy.py rule: max 3 per sector, max 3 changes a week) at
         units x capital / 10 each, hedged with the same value in SPY
  value  3 cheapest S&P 500 members of each of the 7 sector groups (sector_value.py score: B/M, E/P,
         CF/P, S/P, EBIT/EV ranked inside the group), units x capital / 21 each, each one hedged
         with a short in its sector SPDR
  beta   RSP long, units x capital x position, position = Carver EWMAC forecast / 10 x 16 % / vol
         (0..1), traded only when it moves more than 10 % (beta_ewmac.py)
The book is netted by symbol, compared with data/live/holdings.csv (columns ticker, shares, and
optionally lado = largo|corto and estrategia) and turned into orders. Darwinex: only symbols with
trade_mode 4 in data/darwinex/symbols_all.csv, max 1000 shares per symbol; a hedging account, so
reducing a position means closing part of it, never opening the opposite side.
Usage: python live_portfolio.py [--asof YYYY-MM-DD] [--capital 1000000]
"""
import argparse
import subprocess
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

import data
import recent_backtest as rb
from beta_ewmac import VOL_TARGET, forecast
from live_syy import LIVE, SEC, current_members, download, mna_flags
from sector_value import GROUP, VAL
from sector_hedge import ETF

MAX_SHARES = 1000
MIN_TRADE = 0.05          # skip a resize smaller than 5 % of the target position


def tradable():
    d = pd.read_csv(data.DATA / "darwinex" / "symbols_all.csv")
    return set(d[(d.trade_mode == 4)].symbol)


def live_prices(syms):
    p = yf.download(sorted(set(syms)), period="5d", interval="1m", auto_adjust=False, progress=False)["Close"]
    last = p.ffill().iloc[-1]
    miss = last[last.isna()].index.tolist()
    if miss:
        d = yf.download(miss, period="10d", auto_adjust=False, progress=False)["Close"].ffill().iloc[-1]
        last.update(d)
    return last, p.index[-1]


def value_picks(asof, members, tradable_syms, exclude, n_per_group=3):
    """3 cheapest tradable members of every sector group, with point-in-time SEC data."""
    sp = members.assign(mt5=members.symbol.str.replace(".", "", regex=False))
    sp = sp[sp.mt5.isin(tradable_syms) & sp.sector.isin(GROUP) & ~sp.mt5.isin(exclude)]
    cmap = dict(zip(sp.symbol, sp.cik.astype(int)))
    download(list(cmap), cmap)
    rb.CF_UNIVERSE = [(t, c) for t, c in cmap.items() if (SEC / "facts" / f"{t}.parquet").exists()]
    rb.EXTRA = False
    tab = rb.feature_tables("companyfacts")
    ins = tab["ins"][0]
    a = rb.load("annual", "companyfacts")
    a["ni"] = rb.first(a, ["netincomeloss", "profitloss"])
    a["cfo"] = rb.first(a, ["netcashprovidedbyusedinoperatingactivities"])
    a["rev"] = rb.first(a, ["revenues", "revenuefromcontractwithcustomerexcludingassessedtax"])
    a["op"] = rb.first(a, ["operatingincomeloss"])
    raw = rb._CF["raw"]
    s = raw[(raw.key == "shares") & (raw.days >= 80) & (raw.days <= 100)]
    s = pd.concat([s.groupby(["cik", "end"]).filed.min().rename("ann"),
                   s.sort_values("filed").groupby(["cik", "end"]).val.last().rename("SHR")], axis=1).reset_index()
    s["q"] = (s.end - pd.Timedelta(days=45)).dt.to_period("Q")
    f = rb.asof({"ins": (ins, ["BE", "debt", "cash"]), "an": (a, ["ni", "cfo", "rev", "op"]),
                 "shr": (s, ["SHR"])}, pd.Timestamp(asof))
    sp = sp.set_index("cik").join(f, how="inner")
    close = yf.download([t.replace(".", "-") for t in sp.symbol], period="10d", auto_adjust=False,
                        progress=False)["Close"].ffill().iloc[-1]
    close.index = [c.replace("-", ".") for c in close.index]
    sp["ME"] = sp.SHR * sp.symbol.map(close)
    me = sp.ME.where(sp.ME > 0)
    sp["BM"], sp["EP"], sp["CFP"], sp["SP"] = sp.BE / me, sp.ni / me, sp.cfo / me, sp.rev / me
    sp["EBITEV"] = sp.op / (me + sp.debt.fillna(0) - sp.cash.fillna(0))
    sp["grupo"] = sp.sector.map(GROUP)
    pct = pd.concat([sp.groupby("grupo")[v].rank(pct=True) for v in VAL], axis=1)
    sp["V"] = pct.mean(axis=1).where(pct.notna().sum(axis=1) >= 3)
    sp = sp.dropna(subset=["V"]).reset_index()
    pool = sp.sort_values("V", ascending=False).groupby("grupo").head(3 * n_per_group)
    flags = mna_flags(pool.cik, (pd.Timestamp(asof) - timedelta(days=180)).date().isoformat())
    pool = pool[pool.cik.map(flags) == ""]
    picks = pool.sort_values("V", ascending=False).groupby("grupo").head(n_per_group)
    picks["etf"] = picks.sector.map(ETF)
    return picks, sp


def beta_position(prev_pos):
    px = yf.download("RSP", start=(date.today() - timedelta(days=800)).isoformat(), auto_adjust=True,
                     progress=False)["Close"].squeeze().dropna()
    fc, _, _ = forecast(px)
    vol = px.pct_change().ewm(span=35).std().iloc[-1] * np.sqrt(252)
    pos = float(np.clip(fc.iloc[-1] / 10 * min(2, VOL_TARGET / vol), 0, 1))
    if prev_pos is not None and abs(pos - prev_pos) <= 0.10:
        return prev_pos, fc.iloc[-1], vol, False
    return pos, fc.iloc[-1], vol, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=str(date.today()))
    ap.add_argument("--capital", type=float, default=1_000_000)
    ap.add_argument("--holdings", default=str(data.DATA / "live" / "holdings.csv"))
    args = ap.parse_args()
    stamp = args.asof
    units = pd.read_csv(data.ROOT / "results" / "recent" / "asignacion_carver.csv", index_col=0).unidades
    usd = units * args.capital
    trad = tradable()

    # current book, signed by side
    h = pd.read_csv(args.holdings)
    if "lado" not in h:
        h["lado"] = np.where(h.ticker == "SPY", "largo", "corto")
    if "estrategia" not in h:
        h["estrategia"] = np.where(h.ticker == "SPY", "SYY_cobertura", "SYY")
    h["ticker"] = h.ticker.str.upper()
    h["signed"] = h.shares * np.where(h.lado == "largo", 1, -1)
    cur = h.groupby("ticker").signed.sum()

    # 1. SYY: ranking and rotation from live_syy.py at the new size
    syy_hold = h[h.estrategia == "SYY"][["ticker", "shares"]]
    tmp = LIVE / f"_holdings_syy_{stamp}.csv"
    syy_hold.to_csv(tmp, index=False)
    subprocess.run([sys.executable, "live_syy.py", "--asof", stamp, "--capital", str(args.capital), "--currency",
                    "USD", "--gross", f"{units['SYY']:.4f}", "--holdings", str(tmp)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    after = pd.read_csv(LIVE / f"holdings_tras_ordenes_{stamp}.csv")
    tmp.unlink(missing_ok=True)
    syy_names = [t for t in after.ticker if t != "SPY"]
    members = current_members()

    # 2. value picks (never a name that SYY is short)
    picks, scored = value_picks(stamp, members, trad, {t.replace(".", "") for t in syy_names})

    # 3. beta
    prev = h[h.estrategia == "beta"]
    prev_pos = None
    syms = syy_names + list(picks.symbol) + list(picks.etf) + ["SPY", "RSP"]
    px, ts = live_prices([s.replace(".", "-") for s in syms])
    px.index = [i.replace("-", ".") for i in px.index]
    if len(prev):
        prev_pos = prev.shares.sum() * px["RSP"] / usd["beta"]
    pos, fc, vol, changed = beta_position(prev_pos)

    # targets (signed shares) by strategy
    rows = []
    per_syy = usd["SYY"] / 10
    for t in syy_names:
        rows.append(("SYY", t, -min(MAX_SHARES, round(per_syy / px[t]))))
    syy_val = -sum(r[2] * px[r[1]] for r in rows)
    rows.append(("SYY_cobertura", "SPY", min(MAX_SHARES, round(syy_val / px["SPY"]))))
    per_val = usd["value"] / len(picks)
    vlong = []
    for _, r in picks.iterrows():
        n = min(MAX_SHARES, round(per_val / px[r.symbol]))
        rows.append(("value", r.symbol, n))
        vlong.append((r.etf, n * px[r.symbol]))
    for etf, v in pd.DataFrame(vlong, columns=["etf", "v"]).groupby("etf").v.sum().items():
        rows.append(("value_cobertura", etf, -min(MAX_SHARES, round(v / px[etf]))))
    rows.append(("beta", "RSP", min(MAX_SHARES, round(pos * usd["beta"] / px["RSP"]))))
    tgt = pd.DataFrame(rows, columns=["estrategia", "ticker", "signed"])
    net = tgt.groupby("ticker").signed.sum()

    # orders
    allsyms = sorted(set(net.index) | set(cur.index))
    orders = []
    for t in allsyms:
        a, b = cur.get(t, 0), net.get(t, 0)
        if a == b:
            continue
        p = px.get(t, np.nan)
        if b != 0 and a != 0 and np.sign(a) == np.sign(b) and abs(b - a) < MIN_TRADE * abs(b):
            continue
        if a != 0 and (b == 0 or np.sign(a) != np.sign(b)):
            orders.append((t, "Cerrar largo (vender)" if a > 0 else "Cerrar corto (comprar)", abs(a), p))
            a = 0
        if b == 0:
            continue
        d = b - a
        if a == 0:
            act = "Abrir largo (comprar)" if b > 0 else "Abrir corto (vender)"
        elif abs(b) > abs(a):
            act = "Ampliar largo (comprar)" if b > 0 else "Ampliar corto (vender)"
        else:
            act = "Reducir largo (cerrar parte, vender)" if b > 0 else "Reducir corto (cerrar parte, comprar)"
        orders.append((t, act, abs(d), p))
    o = pd.DataFrame(orders, columns=["símbolo", "acción", "acciones", "precio"])
    o["USD"] = o.acciones * o.precio
    rank = {"Cerrar": 0, "Reducir": 1, "Abrir": 2, "Ampliar": 2}
    o["orden"] = o.acción.str.split().str[0].map(rank)
    o = o.sort_values(["orden", "símbolo"]).drop(columns="orden")

    new_hold = tgt.assign(lado=np.where(tgt.signed > 0, "largo", "corto"), shares=tgt.signed.abs())
    new_hold[["ticker", "shares", "lado", "estrategia"]].to_csv(LIVE / f"cartera_objetivo_{stamp}.csv", index=False)
    gross = (tgt.signed.abs() * tgt.ticker.map(px)).sum()
    with open(LIVE / f"ordenes_cartera_{stamp}.md", "w") as fh:
        fh.write(f"# Órdenes de la cuenta completa — {stamp} (precios {ts})\n\n")
        fh.write(f"Capital {args.capital:,.0f} USD. Asignación Carver: SYY {usd['SYY']:,.0f} USD por pata, "
                 f"value {usd['value']:,.0f} USD por pata, beta hasta {usd['beta']:,.0f} USD.\n\n")
        fh.write(f"Beta: previsión EWMAC {fc:.1f}, volatilidad de RSP {100 * vol:.1f} %, posición {pos:.0%}"
                 f"{'' if changed else ' (sin cambio: dentro de la banda del 10 %)'}.\n\n")
        fh.write("## Órdenes (en este orden: cerrar, reducir, abrir/ampliar)\n\n")
        fh.write(o.round(2).to_markdown(index=False) + "\n\n")
        fh.write(f"Margen bruto tras las órdenes: {gross:,.0f} USD ({gross / args.capital:.0%} del capital).\n\n")
        fh.write("## Cartera objetivo por estrategia\n\n")
        tt = tgt.assign(precio=tgt.ticker.map(px), USD=lambda d: d.signed * d.precio)
        fh.write(tt.round(2).to_markdown(index=False) + "\n\n")
        fh.write("## Value: selección por grupo\n\n")
        cols = ["grupo", "symbol", "name", "sector", "V", "BM", "EP", "CFP", "SP", "EBITEV", "etf"]
        fh.write(picks[cols].round(3).to_markdown(index=False) + "\n")
    print(open(LIVE / f"ordenes_cartera_{stamp}.md").read())


if __name__ == "__main__":
    main()
