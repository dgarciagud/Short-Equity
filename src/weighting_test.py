"""Which parts of the SYY short book dominate, and does volatility weighting help?

Uses the point-in-time panel of pit_backtest.py (results/recent/pit/panel.parquet, 8 anomalies,
split-safe NI) and the live rule: 10 most overpriced, max 3 per sector, hedged with SPY,
Darwinex Zero costs. Everything is estimated with information available at each month-end.

1. Anomaly level: monthly return of each anomaly's overpriced quintile minus the EW market,
   its volatility and correlations, and how extreme the selected names are on each anomaly.
2. Score weights (M = weighted mean of percentiles):
     igual         the current rule, 1/8 each
     inv_vol       1/sigma of each anomaly's quintile spread, past 36 months (min 12)
     clusters      equal weight per economic group: inversion (AG, NOA, DPI2A),
                   financiacion (NI), accruals (AC), rentabilidad (PROF, ROA), momentum (r12_2)
3. Position weights within the 10 shorts:
     equiponderado the current rule
     inv_vol       1/sigma of each stock's daily returns over the past 63 sessions
Turnover cost = sum |w_t - w_{t-1}| x (half spread + commission), as in pit_backtest.py.
"""
import json

import numpy as np
import pandas as pd

import data
import pit_backtest as pb
import recent_backtest as rb
from repo_xbrl import universe

OUT = data.ROOT / "results" / "recent" / "ponderacion"
K = list(rb.SIGN)
CLUSTERS = {"AG": "inversion", "NOA": "inversion", "DPI2A": "inversion", "NI": "financiacion",
            "AC": "accruals", "PROF": "rentabilidad", "ROA": "rentabilidad", "r12_2": "momentum"}


def percentiles(p):
    return pd.concat({k: p.groupby("date")[k].rank(pct=True) * s if s > 0 else
                      p.groupby("date")[k].rank(pct=True, ascending=False) for k, s in rb.SIGN.items()}, axis=1)


def capped_top(g, score, n=10, cap=3):
    picked, cnt = [], {}
    for i in g[score].sort_values(ascending=False).index:
        s = g.at[i, "sector"]
        if cnt.get(s, 0) < cap:
            picked.append(i)
            cnt[s] = cnt.get(s, 0) + 1
        if len(picked) == n:
            break
    return picked


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = pd.read_parquet(data.ROOT / "results" / "recent" / "pit" / "panel.parquet")
    p = p.reset_index().rename(columns={"index": "cik"}) if "cik" not in p else p.reset_index(drop=True)
    pct = percentiles(p)
    pct.index = p.index
    spy = pd.read_csv(data.ROOT / "results" / "recent" / "pit" / "monthly.csv", index_col=0, parse_dates=True).spy

    # 1. anomaly quintile spreads (short-side profit: EW - overpriced quintile)
    fac = pd.DataFrame({k: p.assign(x=pct[k]).groupby("date").apply(
        lambda g: g.fwd.mean() - g.fwd[g.x > 0.8].mean()) for k in K})
    desc = pd.DataFrame({"media_%mes": 100 * fac.mean(), "vol_anual_%": 100 * fac.std() * np.sqrt(12),
                         "sharpe": fac.mean() / fac.std() * np.sqrt(12)})
    corr = fac.corr()

    # stock volatility (63 sessions) at each month-end
    hist = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    uni = universe().drop_duplicates("cik")
    cik_of = {**hist, **dict(zip(uni.symbol, uni.cik))}
    d = pb.daily_returns(cik_of)
    vol = d.rolling(63, min_periods=40).std().resample("ME").last() * np.sqrt(252)
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()

    # 2. score weights, known at t
    sig = fac.shift(1).rolling(36, min_periods=12).std()   # fac at t is realised in t+1 -> lag 1
    w_iv = (1 / sig).div((1 / sig).sum(axis=1), axis=0).fillna(1 / len(K))
    nclu = pd.Series(CLUSTERS).value_counts()
    w_cl = pd.Series({k: 1 / len(nclu) / nclu[CLUSTERS[k]] for k in K})
    schemes = {"igual": None, "inv_vol": w_iv, "clusters": w_cl}

    rows, rets, extreme = [], {}, []
    for sname, w in schemes.items():
        for pos in ("equiponderado", "inv_vol"):
            prev, r, picks = pd.Series(dtype=float), {}, {}
            for t, g in p.groupby("date"):
                q = pct.loc[g.index]
                if w is None:
                    wt = pd.Series(1.0, index=K)
                elif isinstance(w, pd.DataFrame):
                    wt = w.loc[t]
                else:
                    wt = w
                num = q.mul(wt, axis=1).sum(axis=1, min_count=1)
                den = q.notna().mul(wt, axis=1).sum(axis=1)
                g = g.assign(S=(num / den).where(q.notna().sum(axis=1) >= 5))
                g = g.dropna(subset=["S"])
                top = capped_top(g, "S")
                if pos == "equiponderado":
                    ww = pd.Series(1 / len(top), index=g.loc[top, "cik"].values)
                else:
                    v = vol.loc[t].reindex(g.loc[top, "cik"].values)
                    v = v.fillna(v.median())
                    ww = (1 / v) / (1 / v).sum()
                fwd = pd.Series(g.loc[top, "fwd"].values, index=ww.index)
                turn = ww.sub(prev, fill_value=0).abs()
                cost = sum(turn[c] * (spr.get(c, 0.0008) + rb.COMM) for c in turn.index)
                r[t] = spy.loc[t] - (ww * fwd).sum() - cost - rb.DIV_WHT_SPY
                prev = ww
                if sname == "igual" and pos == "equiponderado":
                    extreme.append(q.loc[top].mean())
                    # share of short-book variance from the 3 most volatile names (diagonal approx.)
                    v = vol.loc[t].reindex(ww.index).fillna(vol.loc[t].median())
                    rc = (ww * v) ** 2
                    picks[t] = rc.nlargest(3).sum() / rc.sum()
            s = pd.Series(r)
            rets[f"{sname} | {pos}"] = s
            st = rb.stats(s)
            st.update(puntuacion=sname, posiciones=pos,
                      **{f"{a}-{b}": 100 * s.loc[a:b].mean() for a, b in
                         (("2012", "2016"), ("2017", "2021"), ("2022", "2026"))})
            rows.append(st)
            if picks:
                top3 = pd.Series(picks)

    res = pd.DataFrame(rows)
    res = res[["puntuacion", "posiciones"] + [c for c in res if c not in ("puntuacion", "posiciones")]]
    res.to_csv(OUT / "resumen.csv", index=False, float_format="%.4f")
    desc.to_csv(OUT / "anomalias_vol.csv", float_format="%.4f")
    corr.to_csv(OUT / "anomalias_corr.csv", float_format="%.3f")
    pd.DataFrame(rets).to_csv(OUT / "retornos.csv", float_format="%.5f")
    ext = pd.DataFrame(extreme).mean()
    w_iv.to_csv(OUT / "pesos_inv_vol.csv", float_format="%.4f")
    pd.set_option("display.width", 250)
    print(desc.round(2).to_string())
    print(corr.round(2).to_string())
    print("\nPercentil medio de los 10 cortos en cada anomalía:\n", (100 * ext).round(0).to_string())
    print("\nPeso medio inv_vol:\n", (100 * w_iv.loc["2014":].mean()).round(1).to_string())
    print("\nPeso de clusters:\n", (100 * w_cl).round(1).to_string())
    print(f"\nCuota de la varianza del libro corto de los 3 valores más volátiles: {100 * top3.mean():.0f}%")
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
