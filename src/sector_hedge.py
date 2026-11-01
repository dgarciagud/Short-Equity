"""SYY short book hedged with SECTOR ETFs instead of SPY (Darwinex offers the SPDR sector CFDs).

Same book as pit_backtest.py / the live rule: each month-end the 10 most overpriced S&P 500
members (max 3 per sector), equal weight, held one month, Darwinex Zero costs.
Hedges (long leg, dollar for dollar with the shorts):
  SPY            current rule
  RSP            S&P 500 equal weight (Darwinex CFD; spread not in the MT5 export, 3 bp assumed)
  50 % SPY / RSP half each
  sector ETF     each short hedged with its sector SPDR (XLC from 2018-07, XLRE from 2015-11;
                 before that, and for unknown sectors, SPY)
  50/50          half SPY, half sector ETF
  beta sector    sector ETF sized by the stock's beta to it (252 d), the rest of the dollar in SPY
Costs: stocks as in pit_backtest; ETF legs pay half spread (Darwinex MT5 export) + 0.02 USD/share
on every change of their weight, and 15 % withholding on their dividend yield.
"""
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf

import data
import pit_backtest as pb
import recent_backtest as rb
from cpz_mispricing import factors
from repo_xbrl import universe

OUT = data.ROOT / "results" / "recent" / "cobertura_sectorial"
ETF = {"Utilities": "XLU", "Consumer Staples": "XLP", "Health Care": "XLV", "Industrials": "XLI",
       "Materials": "XLB", "Financials": "XLF", "Consumer Discretionary": "XLY",
       "Information Technology": "XLK", "Energy": "XLE", "Real Estate": "XLRE", "Communication Services": "XLC"}
DIV_YIELD = {"SPY": 1.3, "RSP": 1.6, "XLU": 3.0, "XLP": 2.6, "XLV": 1.6, "XLI": 1.5, "XLB": 1.9, "XLF": 1.6, "XLY": 0.8,
             "XLK": 0.7, "XLE": 3.3, "XLRE": 3.3, "XLC": 0.9}
START = {"XLC": "2018-07-31", "XLRE": "2015-11-30"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pan = pd.read_parquet(data.ROOT / "results" / "recent" / "pit" / "panel.parquet").rename_axis("cik").reset_index()
    uni = universe().drop_duplicates("cik")
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()
    dx = pd.read_csv(data.DATA / "darwinex" / "spread_history.csv").set_index("symbol")
    tick = sorted(set(ETF.values()) | {"SPY", "RSP"})
    px = yf.download(tick, start="2010-01-01", auto_adjust=True, progress=False)["Close"]
    me = px.resample("ME").last()
    fwd = me.pct_change(fill_method=None).shift(-1)               # return of t+1, dated t
    etf_cost = {e: dx.avg_spread_bps.get(e, 3.0) / 2 / 1e4 + 0.02 / dx.last_price.get(e, 100.0) for e in tick}
    wht = {e: 0.15 * DIV_YIELD[e] / 100 / 12 for e in tick}

    # stock betas to their sector ETF (252 daily sessions), for the beta-sized hedge
    hist = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    cik_of = {**hist, **dict(zip(uni.symbol, uni.cik))}
    d = pb.daily_returns(cik_of)
    er = px.pct_change(fill_method=None).reindex(d.index)

    def etf_for(sector, t):
        e = ETF.get(sector, "SPY")
        return e if (e not in START or t >= pd.Timestamp(START[e])) and e in fwd and pd.notna(fwd.at[t, e]) else "SPY"

    schemes = ["SPY", "RSP (S&P 500 equiponderado)", "50 % SPY / 50 % RSP", "ETF sectorial",
               "50 % SPY / 50 % sectorial", "sectorial por beta"]
    prev_s, prev_h = pd.Series(dtype=float), {k: pd.Series(dtype=float) for k in schemes}
    rows = []
    for t, g in pan.groupby("date"):
        if t not in fwd.index:
            continue
        picked, cnt = [], {}
        for i in g.M.sort_values(ascending=False).index:
            s = g.at[i, "sector"]
            if cnt.get(s, 0) < 3:
                picked.append(i)
                cnt[s] = cnt.get(s, 0) + 1
            if len(picked) == 10:
                break
        b = g.loc[picked]
        w = pd.Series(0.1, index=b.cik.values)
        turn = w.sub(prev_s, fill_value=0).abs()
        cost_s = sum(turn[c] * (spr.get(c, 0.0008) + rb.COMM) for c in turn.index)
        prev_s = w
        short_ret = (w.values * b.fwd.values).sum()
        etfs = [etf_for(s, t) for s in b.sector]
        betas = []
        for c, e in zip(b.cik, etfs):
            x = pd.concat([d[c], er[e]], axis=1).loc[:t].iloc[-252:].dropna() if c in d else pd.DataFrame()
            betas.append(np.clip(x.cov().iloc[0, 1] / x.iloc[:, 1].var(), 0, 2) if len(x) > 120 else 1.0)
        out = {"date": t, "cortos": short_ret}
        for k in schemes:
            if k == "SPY":
                hw = pd.Series({"SPY": 1.0})
            elif k.startswith("RSP"):
                hw = pd.Series({"RSP": 1.0})
            elif k == "50 % SPY / 50 % RSP":
                hw = pd.Series({"SPY": 0.5, "RSP": 0.5})
            elif k == "ETF sectorial":
                hw = pd.Series(0.1, index=etfs).groupby(level=0).sum()
            elif k.startswith("50"):
                hw = pd.concat([pd.Series({"SPY": 0.5}), pd.Series(0.05, index=etfs)]).groupby(level=0).sum()
            else:
                bb = np.array(betas)
                hw = pd.concat([pd.Series(0.1 * bb, index=etfs), pd.Series({"SPY": 0.1 * (10 - bb.sum())})]) \
                    .groupby(level=0).sum()
            hturn = hw.sub(prev_h[k], fill_value=0).abs()
            cost_h = sum(hturn[e] * etf_cost[e] for e in hturn.index)
            prev_h[k] = hw
            long_ret = sum(hw[e] * fwd.at[t, e] for e in hw.index)
            out[k] = long_ret - short_ret - cost_s - cost_h - sum(hw[e] * wht[e] for e in hw.index)
        rows.append(out)
    r = pd.DataFrame(rows).set_index("date")
    ff = factors()
    res = []
    for k in schemes:
        s = r[k]
        st = rb.stats(s)
        x = s.copy()
        x.index = x.index.to_period("M") + 1
        f = ff.reindex(x.index)[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]].dropna()
        o = sm.OLS(x.reindex(f.index), sm.add_constant(f)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        spy = fwd.SPY.reindex(s.index)
        res.append({"cobertura": k, "%/mes": st["media_%mes"], "t": st["t"], "sharpe": st["sharpe"],
                    "vol_%": st["vol_%"], "max_dd_%": st["max_dd_%"], "peor_mes_%": st["peor_mes_%"],
                    "2012-2016": 100 * s.loc[:"2016"].mean(), "2017-2021": 100 * s.loc["2017":"2021"].mean(),
                    "2022-2026": 100 * s.loc["2022":].mean(), "corr_SPY": s.corr(spy),
                    "beta_mercado": o.params["Mkt-RF"], "alfa_FF6_%mes": 100 * o.params["const"],
                    "t_alfa": o.tvalues["const"]})
    res = pd.DataFrame(res)
    res.to_csv(OUT / "resumen.csv", index=False, float_format="%.4f")
    r.to_csv(OUT / "retornos.csv", float_format="%.5f")
    # how much of the SPY-hedged return is the sector bet: sector ETFs of the shorts vs SPY
    bet = (r["SPY"] - r["ETF sectorial"])
    pd.set_option("display.width", 250)
    print(res.round(2).to_string(index=False))
    tilt = r["SPY"] - r["RSP (S&P 500 equiponderado)"]
    print(f"\nInclinación capitalización vs equiponderado (cob. SPY − cob. RSP): {100 * tilt.mean():.2f} %/mes, "
          f"t {rb.stats(tilt)['t']:.2f}")
    print(f"\nApuesta sectorial implícita (cobertura SPY − cobertura sectorial): {100 * bet.mean():.2f} %/mes, "
          f"t {rb.stats(bet)['t']:.2f}, vol {100 * bet.std() * np.sqrt(12):.1f} %; "
          f"corr. con la estrategia sectorial {bet.corr(r['ETF sectorial']):.2f}")


if __name__ == "__main__":
    main()
