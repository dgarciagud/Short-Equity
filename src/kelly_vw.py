"""All SEC studies of the 13 JKP themes redone with VALUE WEIGHTS: capped as JKP do (argument
`tope`, default) or plain market-value weights (argument `puro`), on the
point-in-time S&P 500 2012-2026 (panel from kelly_sec2.py).

Capped value weight: weight proportional to market value ME, with ME capped each month at the
80th percentile of the S&P 500 cross-section (JKP cap at the NYSE 80th percentile), so the
largest companies cannot take over a portfolio.
  indicator L/S   top minus bottom tercile (JKP use terciles), capped VW inside each leg
  themes          mean of their indicators; combinations: static, TSFM 12m, winners-only 12m
  books           composite score, long the N best / short the N worst, capped VW inside each
                  leg; also the full top/bottom tercile. Net of Darwinex Zero costs.
The CRSP/Chen-Pelger-Zhu panel has no dollar market value (LME is a rank), so the long-history
VW view is the official JKP mega/large-cap series (kelly_jkp.py, factor_momentum.py).
"""
import sys

import numpy as np
import pandas as pd

import data
from darwinex_sim import COMM, DIV_WHT
from kelly_jkp import jkp_series
from kelly_sec2 import INDICATORS, SIGN, THEME_OF, stats, weights
from repo_xbrl import universe

OUT = data.ROOT / "results" / "kelly"
MODE = sys.argv[1] if len(sys.argv) > 1 else "tope"     # tope = capped at the 80th pct. | puro = plain ME
TAG = "vw" if MODE == "tope" else "vwpuro"


def capped(g):
    return g.ME.clip(upper=g.ME.quantile(0.8)) if MODE == "tope" else g.ME


def vw_ls(p, k, n=3):
    q = np.ceil(p.groupby("date")["P_" + k].rank(pct=True, method="first") * n)
    d = p.assign(q=q, wr=p.CW * p.fwd)
    g = d.groupby(["date", "q"])[["wr", "CW"]].sum()
    r = (g.wr / g.CW).unstack()
    return r[float(n)] - r[1.0]


def book(p, w, n, spr):
    """n = int (N best/worst names) or 'tercil'; capped value weights inside each leg."""
    prev, rows = pd.Series(dtype=float), []
    pcols = ["P_" + k for k in w.columns]
    for t, g in p.groupby("date"):
        if t not in w.index or w.loc[t].isna().all():
            continue
        wt = w.loc[t].fillna(0)
        X = g[pcols].sub(0.5)
        X.columns = w.columns
        score = (X * wt).sum(axis=1) / (X.notna() * wt.abs()).sum(axis=1)
        g = g.assign(S=score.where(X.notna().sum(axis=1) >= 0.6 * len(pcols))).dropna(subset=["S"])
        r = g.S.rank(method="first")
        k = len(g) // 3 if n == "tercil" else n
        L, S = g[r > len(g) - k], g[r <= k]
        wl, ws = L.CW / L.CW.sum(), S.CW / S.CW.sum()
        ww = pd.concat([pd.Series(wl.values, index=L.cik.values), pd.Series(-ws.values, index=S.cik.values)])
        turn = ww.sub(prev, fill_value=0).abs()
        cost = sum(turn[c] * (spr.get(c, 0.0008) + COMM) for c in turn.index)
        gross = (wl * L.fwd).sum() - (ws * S.fwd).sum()
        rows.append((t, gross, gross - cost - DIV_WHT, turn.sum() / 4, wl.max(), ws.max()))
        prev = ww
    return pd.DataFrame(rows, columns=["date", "bruto", "neto", "rotacion", "peso_max_largo", "peso_max_corto"]).set_index("date")


def main():
    p = pd.read_parquet(OUT / "sec2_panel.parquet")
    p = p[p.ME > 0].copy()
    p["CW"] = p.groupby("date", group_keys=False).apply(capped)
    uni = universe().drop_duplicates("cik")
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()

    R = pd.DataFrame({k: vw_ls(p, k) for k in SIGN})          # formation month t, realised t+1
    T = R.T.groupby(THEME_OF).mean().T
    R.to_csv(OUT / f"{TAG}_indicadores.csv", float_format="%.5f")
    T.to_csv(OUT / f"{TAG}_temas.csv", float_format="%.5f")
    ind = pd.DataFrame([{"tema": THEME_OF[k], "indicador": k, **stats(R[k])} for k in R])
    ind.to_csv(OUT / f"{TAG}_indicadores_resumen.csv", index=False, float_format="%.4f")
    th = pd.DataFrame([{"tema": t, **stats(T[t])} for t in T])

    # same-period comparison with official JKP mega caps (holding months)
    js = jkp_series()["JKP mega"]
    Th = T.copy()
    Th.index = Th.index.to_period("M") + 1
    idx = Th.index.intersection(js.index)
    th["corr_JKP_mega"] = [Th.loc[idx, t].corr(js.loc[idx, t]) for t in T]
    th["sharpe_JKP_mega_mismo_periodo"] = [js.loc[idx, t].mean() / js.loc[idx, t].std() * np.sqrt(12) for t in T]
    th.to_csv(OUT / f"{TAG}_temas_resumen.csv", index=False, float_format="%.4f")

    rows, series = [], {}
    for level, M in (("indicadores", R), ("13 temas", T)):
        for k, w in weights(M).items():
            if k == "TSFM 1m":
                continue
            fac = (w.shift(1) * M).sum(axis=1, min_count=1).where(w.shift(1).notna().any(axis=1))
            series[f"factores|{level}|{k}"] = fac
            rows.append({"cartera": f"Factores, {level}, {k} (bruto)", **stats(fac)})
    WI, WT = weights(R), weights(T)
    for scheme in ("estatico", "solo ganadores 12m", "TSFM 12m"):
        w_ind = pd.DataFrame({k: WT[scheme][THEME_OF[k]] / len(INDICATORS[THEME_OF[k]]) for k in SIGN})
        for lab, w in ((f"indicadores {scheme}", WI[scheme]), (f"temas {scheme}", w_ind)):
            for n in (50, 100, "tercil"):
                b = book(p, w.shift(1), n, spr)
                series[f"libro{n}|{lab}|neto"] = b.neto
                rows.append({"cartera": f"Libro {n}, {lab}, bruto", **stats(b.bruto)})
                rows.append({"cartera": f"Libro {n}, {lab}, neto Zero", **stats(b.neto),
                             "rotacion_%mes": 100 * b.rotacion.iloc[1:].mean(),
                             "peso_max_%": 100 * b[["peso_max_largo", "peso_max_corto"]].max(axis=1).mean()})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / f"{TAG}_resumen.csv", index=False, float_format="%.4f")
    pd.DataFrame(series).to_csv(OUT / f"{TAG}_retornos.csv", float_format="%.5f")
    pd.set_option("display.width", 260)
    print(th.round(2).to_string(index=False))
    print(ind.sort_values("sharpe", ascending=False).round(2).head(15).to_string(index=False))
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
