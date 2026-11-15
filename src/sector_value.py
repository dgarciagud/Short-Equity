"""Value WITHIN each sector, point-in-time S&P 500 2012-2026, Darwinex Zero costs.

Inputs: the SEC/price panel of the 13-theme study (branch analisis-13-familias-kelly,
results/kelly/sec2_panel.parquet: B/M, E/P, CF/P, S/P, EBIT/EV, market value, next-month return)
and the sectors of pit_backtest.py. Real estate is left out (Darwinex offers almost no REITs).
Sector groups (enough names to rank inside each one):
  Tecnología y comunicaciones, Industriales, Consumo cíclico, Salud, Financiero,
  Defensivos (consumo básico + utilities), Materias primas (materiales + energía).
Value score = mean of the within-group percentiles of B/M, E/P, CF/P, S/P, EBIT/EV (>= 3 of 5).
Portfolios (formed at each month-end, held one month, equal weights):
  factor tercile   top minus bottom third inside every group, groups averaged (gross)
  L/S k            k cheapest long and k dearest short in every group: sector- and dollar-neutral
  largo k / ETF    k cheapest long in every group, each hedged with its own sector SPDR
Costs: half spread (MT5 export, 8 bp if unknown) + commission on weight changes; ETF legs as in
sector_hedge.py; 15 % withholding on the long stocks' dividends.
"""
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf

import data
import recent_backtest as rb
from cpz_mispricing import factors
from darwinex_sim import COMM, DIV_WHT
from repo_xbrl import universe
from sector_hedge import ETF, START

PANEL = os.environ.get("KELLY_PANEL", "/home/user/Short-Equity-13-familias-kelly/results/kelly/sec2_panel.parquet")
OUT = data.ROOT / "results" / "recent" / "value_sectorial"
VAL = ["BM", "EP", "CFP", "SP", "EBITEV"]
GROUP = {"Information Technology": "Tecnología y comunicaciones", "Communication Services": "Tecnología y comunicaciones",
         "Industrials": "Industriales", "Consumer Discretionary": "Consumo cíclico", "Health Care": "Salud",
         "Financials": "Financiero", "Consumer Staples": "Defensivos", "Utilities": "Defensivos",
         "Materials": "Materias primas", "Energy": "Materias primas"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = pd.read_parquet(PANEL, columns=["cik", "date", "fwd"] + VAL)
    sec = pd.read_parquet(data.ROOT / "results" / "recent" / "pit" / "panel.parquet", columns=["sector"])
    sec = sec.rename_axis("cik").reset_index().drop_duplicates(["cik"], keep="last").set_index("cik").sector
    p["sector"] = p.cik.map(sec)
    p["grupo"] = p.sector.map(GROUP)
    p = p.dropna(subset=["grupo", "fwd"])
    pct = pd.concat([p.groupby(["date", "grupo"])[v].rank(pct=True) for v in VAL], axis=1)
    p["V"] = pct.mean(axis=1).where(pct.notna().sum(axis=1) >= 3)
    p = p.dropna(subset=["V"])

    uni = universe().drop_duplicates("cik")
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()
    dx = pd.read_csv(data.DATA / "darwinex" / "spread_history.csv").set_index("symbol")
    tick = sorted(set(ETF.values()) | {"SPY"})
    px = yf.download(tick, start="2011-12-01", auto_adjust=True, progress=False)["Close"].resample("ME").last()
    efwd = px.pct_change(fill_method=None).shift(-1)
    ecost = {e: dx.avg_spread_bps.get(e, 3.0) / 2 / 1e4 + 0.02 / dx.last_price.get(e, 100.0) for e in tick}

    def etf_for(s, t):
        e = ETF.get(s, "SPY")
        return e if (e not in START or t >= pd.Timestamp(START[e])) and pd.notna(efwd.at[t, e]) else "SPY"

    rows, prev = [], {}
    for t, g in p.groupby("date"):
        if t not in efwd.index:
            continue
        rec = {"date": t}
        # factor tercile, groups averaged
        ls = []
        for _, gg in g.groupby("grupo"):
            r = gg.V.rank(pct=True)
            ls.append(gg.fwd[r > 2 / 3].mean() - gg.fwd[r <= 1 / 3].mean())
        rec["factor tercil (bruto)"] = np.nanmean(ls)
        for k in (2, 3, 4):
            longs, shorts = [], []
            for _, gg in g.groupby("grupo"):
                o = gg.sort_values("V")
                if len(o) >= 4 * k:
                    longs.append(o.tail(k))
                    shorts.append(o.head(k))
            L, S = pd.concat(longs), pd.concat(shorts)
            for name in (f"L/S {k} por sector", f"largo {k} por sector / ETF"):
                w = pd.Series(1 / len(L), index=L.cik.values)
                if name.startswith("L/S"):
                    w = pd.concat([w, pd.Series(-1 / len(S), index=S.cik.values)])
                    gross = L.fwd.mean() - S.fwd.mean()
                    hw = pd.Series(dtype=float)
                else:
                    etfs = [etf_for(s, t) for s in L.sector]
                    hw = pd.Series(1 / len(L), index=etfs).groupby(level=0).sum()
                    gross = L.fwd.mean() - sum(hw[e] * efwd.at[t, e] for e in hw.index)
                pw, ph = prev.get(name, (pd.Series(dtype=float), pd.Series(dtype=float)))
                turn = w.sub(pw, fill_value=0).abs()
                hturn = hw.sub(ph, fill_value=0).abs()
                cost = sum(turn[c] * (spr.get(c, 0.0008) + COMM) for c in turn.index) + \
                    sum(hturn[e] * ecost[e] for e in hturn.index)
                prev[name] = (w, hw)
                rec[name] = gross - cost - DIV_WHT
                rec[f"rot|{name}"] = turn.sum() / 2
        rows.append(rec)
    r = pd.DataFrame(rows).set_index("date")
    rot = r[[c for c in r if c.startswith("rot|")]]
    r = r.drop(columns=rot.columns)

    syy = pd.read_csv(data.ROOT / "results" / "recent" / "pit" / "strategy_returns.csv", index_col=0, parse_dates=True)
    syy = syy["Top10 límite sectorial / SPY, neto Zero"]
    spy = efwd.SPY
    ff = factors()
    res = []
    for c in r:
        s = r[c].dropna()
        st = rb.stats(s)
        x = s.copy()
        x.index = x.index.to_period("M") + 1
        f = ff.reindex(x.index)[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]].dropna()
        o = sm.OLS(x.reindex(f.index), sm.add_constant(f)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        both = (s / s.std() + syy.reindex(s.index) / syy.reindex(s.index).std()) / 2
        res.append({"cartera": c, "%/mes": st["media_%mes"], "t": st["t"], "sharpe": st["sharpe"],
                    "vol_%": st["vol_%"], "max_dd_%": st["max_dd_%"],
                    "2012-2016": 100 * s.loc[:"2016"].mean(), "2017-2021": 100 * s.loc["2017":"2021"].mean(),
                    "2022-2026": 100 * s.loc["2022":].mean(), "corr_SYY": s.corr(syy), "corr_SPY": s.corr(spy),
                    "HML": o.params["HML"], "alfa_FF6_%mes": 100 * o.params["const"], "t_alfa": o.tvalues["const"],
                    "Sharpe_50/50_con_SYY": both.mean() / both.std() * np.sqrt(12),
                    "rotacion_%mes": 100 * rot.get(f"rot|{c}", pd.Series(np.nan)).iloc[1:].mean()})
    res = pd.DataFrame(res)
    res.to_csv(OUT / "resumen.csv", index=False, float_format="%.4f")
    r.to_csv(OUT / "retornos.csv", float_format="%.5f")
    pd.set_option("display.width", 260)
    print(res.round(2).to_string(index=False))
    print("Valores por grupo (media mensual):", p.groupby(["date", "grupo"]).size().groupby("grupo").mean().round(0).to_dict())


if __name__ == "__main__":
    main()
