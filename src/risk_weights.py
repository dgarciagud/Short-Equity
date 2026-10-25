"""Position sizing inside the SYY short book so that no stock dominates the risk.

Each short is hedged dollar-for-dollar with SPY, so the risk of the hedged book is
w' S w with S = covariance of the MARKET-ADJUSTED daily returns (r_i - r_SPY): what two shorts
share once the market is hedged (e.g. three utilities) shows up in S.
  S        last 126 sessions, Ledoit-Wolf shrinkage (stable with 10 names / half a year)
  ERC      equal risk contribution: w_i (S w)_i equal for every name (Maillard, Roncalli and
           Teiletche, 2010), solved by the fixed point w_i ~ 1 / (S w)_i
Schemes compared on the point-in-time backtest (pit_backtest.py rule: 10 most overpriced,
max 3 per sector, vs SPY, Darwinex Zero costs; turnover cost on |weight changes|):
  igual             1/10 (current rule)
  inversa vol.      1 / sigma_i (ignores correlations)
  ERC               equal risk contribution with correlations
  ERC 4-20 %        ERC with weights bounded to [4 %, 20 %]
  mezcla            half equal weights, half ERC
  tope de riesgo    equal weights, shrinking only the names above 15 % of the book risk
Concentration diagnostics, ex ante: largest single-name share of the book variance and the
effective number of bets 1 / sum(rc_i^2).
"""
import json

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

import data
import pit_backtest as pb
import recent_backtest as rb
from repo_xbrl import universe

OUT = data.ROOT / "results" / "recent" / "riesgo"
WINDOW = 126


def erc(S, lo=0.0, hi=1.0, iters=500):
    n = len(S)
    w = np.full(n, 1 / n)
    for _ in range(iters):
        m = S @ w
        w_new = 1 / np.maximum(m, 1e-12)
        w_new = w_new / w_new.sum()
        w_new = np.clip(w_new, lo, hi)
        w_new = w_new / w_new.sum()
        if np.abs(w_new - w).max() < 1e-10:
            break
        w = 0.5 * w + 0.5 * w_new
    return w


def risk_cap(S, cap=0.15, iters=200):
    """Start from equal weights and shrink only the names whose risk share exceeds `cap`."""
    n = len(S)
    w = np.full(n, 1 / n)
    for _ in range(iters):
        rs = risk_shares(w, S)
        if rs.max() <= cap + 1e-4:
            break
        w = w * np.minimum(1.0, np.sqrt(cap / np.maximum(rs, 1e-9)))
        w = w / w.sum()
    return w


def risk_shares(w, S):
    rc = w * (S @ w)
    return rc / rc.sum()


def weights_for(ciks, t, d, spy_d):
    """Weights for the names `ciks` at month-end t under every scheme, plus diagnostics."""
    x = d.loc[:t, ciks].iloc[-WINDOW:]
    m = spy_d.loc[x.index]
    x = x.sub(m, axis=0)
    ok = x.notna().sum() >= 60
    n = len(ciks)
    out = {"igual": np.full(n, 1 / n)}
    if ok.sum() < n:                      # not enough history for some names: keep equal weights
        for k in ("inversa vol.", "ERC", "ERC 4-20 %", "mezcla 50 % igual / 50 % ERC", "tope de riesgo 15 %"):
            out[k] = out["igual"]
        return out, None
    S = LedoitWolf().fit(x.fillna(0).values).covariance_
    iv = 1 / np.sqrt(np.diag(S))
    out["inversa vol."] = iv / iv.sum()
    out["ERC"] = erc(S)
    out["ERC 4-20 %"] = erc(S, 0.04, 0.20)
    out["mezcla 50 % igual / 50 % ERC"] = 0.5 * out["igual"] + 0.5 * out["ERC"]
    out["tope de riesgo 15 %"] = risk_cap(S, 0.15)
    return out, S


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pan = pd.read_parquet(data.ROOT / "results" / "recent" / "pit" / "panel.parquet")
    pan = pan.rename_axis("cik").reset_index()
    hist = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    uni = universe().drop_duplicates("cik")
    cik_of = {**hist, **dict(zip(uni.symbol, uni.cik))}
    d = pb.daily_returns(cik_of)
    px = pd.read_parquet(data.DATA / "prices_sp500_pit.parquet")
    spy_d = px["SPY"].pct_change(fill_method=None).reindex(d.index)
    spy_m = pd.read_csv(data.ROOT / "results" / "recent" / "pit" / "monthly.csv", index_col=0, parse_dates=True).spy
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()

    schemes = ["igual", "inversa vol.", "ERC", "ERC 4-20 %", "mezcla 50 % igual / 50 % ERC", "tope de riesgo 15 %"]
    prev = {k: pd.Series(dtype=float) for k in schemes}
    rets = {k: {} for k in schemes}
    diag = []
    for t, g in pan.groupby("date"):
        picked, cnt = [], {}
        for i in g.M.sort_values(ascending=False).index:
            s = g.at[i, "sector"]
            if cnt.get(s, 0) < 3:
                picked.append(i)
                cnt[s] = cnt.get(s, 0) + 1
            if len(picked) == 10:
                break
        ciks = g.loc[picked, "cik"].tolist()
        fwd = g.loc[picked, "fwd"].values
        W, S = weights_for(ciks, t, d, spy_d)
        for k in schemes:
            w = pd.Series(W[k], index=ciks)
            turn = w.sub(prev[k], fill_value=0).abs()
            cost = sum(turn[c] * (spr.get(c, 0.0008) + rb.COMM) for c in turn.index)
            rets[k][t] = spy_m.loc[t] - (w.values * fwd).sum() - cost - rb.DIV_WHT_SPY
            prev[k] = w
            if S is not None:
                rs = risk_shares(W[k], S)
                diag.append({"date": t, "esquema": k, "riesgo_max_1_valor_%": 100 * rs.max(),
                             "apuestas_efectivas": 1 / (rs ** 2).sum(), "peso_max_%": 100 * W[k].max(),
                             "peso_min_%": 100 * W[k].min(),
                             "vol_anual_libro_%": 100 * np.sqrt(W[k] @ S @ W[k] * 252)})
    diag = pd.DataFrame(diag)
    r = pd.DataFrame(rets)
    rows = []
    for k in schemes:
        st = rb.stats(r[k])
        dg = diag[diag.esquema == k]
        rows.append({"esquema": k, "%/mes": st["media_%mes"], "t": st["t"], "sharpe": st["sharpe"],
                     "vol_%": st["vol_%"], "max_dd_%": st["max_dd_%"], "peor_mes_%": st["peor_mes_%"],
                     "2012-2016": 100 * r[k].loc[:"2016"].mean(), "2017-2021": 100 * r[k].loc["2017":"2021"].mean(),
                     "2022-2026": 100 * r[k].loc["2022":].mean(),
                     "riesgo_max_1_valor_%": dg["riesgo_max_1_valor_%"].mean(),
                     "apuestas_efectivas": dg.apuestas_efectivas.mean(), "peso_max_%": dg["peso_max_%"].mean(),
                     "peso_min_%": dg["peso_min_%"].mean(), "vol_ex_ante_%": dg["vol_anual_libro_%"].mean()})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "resumen.csv", index=False, float_format="%.4f")
    r.to_csv(OUT / "retornos.csv", float_format="%.5f")
    diag.to_csv(OUT / "diagnostico.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
