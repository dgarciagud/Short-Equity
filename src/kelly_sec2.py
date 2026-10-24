"""13 JKP themes rebuilt with several indicators each (SEC + prices), point-in-time S&P 500
2012-2026, combined statically and with factor momentum (Gupta and Kelly, 2019).

Data and costs as pit_backtest.py / kelly_sec.py. New here:
  * ~55 indicators (list in INDICATORS, sign = expected direction), JKP-style definitions where
    the SEC data allow; quarterly NI with the fiscal Q4 = annual - Q1..Q3 (recent_backtest).
  * Market value ME = diluted shares of the latest quarter (value as restated in the latest
    filing, i.e. on today's split basis) x split-adjusted close (prices_close.py).
  * Seasonality aligned to the HOLDING month (t+1): returns of the same calendar month in
    past years (kelly_sec.py used month t, one month off).
Portfolios: indicator L/S = top minus bottom quintile (EW); theme = mean of its indicators;
factor-level combinations as in factor_momentum.py; stock-level books (N long / N short) on a
composite score = sum_k w_k,t x (percentile_k - 0.5), with w from each weighting scheme,
net of Darwinex Zero costs.
"""
import json

import numpy as np
import pandas as pd

import data
import pit_backtest as pb
import recent_backtest as rb
from darwinex_sim import COMM, DIV_WHT
from factor_momentum import schemes
from live_syy import SEC
from repo_xbrl import universe

OUT = data.ROOT / "results" / "kelly"
INDICATORS = {
    "Accruals": {"AC": -1, "ACNI": -1, "dWC": -1},
    "Debt Issuance": {"dDEBT": -1, "DEBTGR3": -1, "dNCL": -1},
    "Investment": {"AG": -1, "NOA": -1, "DPI2A": -1, "NI": -1, "NI3": -1, "INVGR": -1, "PPEGR": -1,
                   "SALEGR": -1, "CAGR": -1},
    "Low Leverage": {"LEV": -1, "ABE": -1, "DME": -1, "NDME": -1, "CASHAT": 1},
    "Low Risk": {"BETA": -1, "IVOL": -1, "VOL": -1, "BETA60": -1, "MAXRET": -1},
    "Momentum": {"r12_2": 1, "r6_1": 1, "r9_1": 1, "RESMOM": 1},
    "Profit Growth": {"SUE": 1, "dROA": 1, "dROE": 1, "dGM": 1, "dCFOA": 1, "NIINC": 1},
    "Profitability": {"PROF": 1, "ROE": 1, "OPBE": 1, "OPA": 1, "CFOA": 1},
    "Quality": {"ROA": 1, "ATO": 1, "GM": 1, "FSCORE": 1, "OSC": -1, "EVAR": -1},
    "Seasonality": {"SEAS1": 1, "SEAS25": 1},
    "Short-Term Reversal": {"STREV": -1, "MAX5": -1, "WREV": -1},
    "Size": {"ME": -1, "LOGA": -1},
    "Value": {"BM": 1, "EP": 1, "CFP": 1, "SP": 1, "AME": 1, "EBITEV": 1},
}
SIGN = {k: s for th in INDICATORS.values() for k, s in th.items()}
THEME_OF = {k: t for t, th in INDICATORS.items() for k in th}


def lag(df, cols, k, sfx):
    return rb.lagged(df, cols, k, sfx)


def accounting(cik_of):
    files = []
    for cik in set(cik_of.values()):
        tic = next((t for t, c in sorted(cik_of.items()) if c == cik and (SEC / "facts" / f"{t}.parquet").exists()), None)
        if tic:
            files.append((tic, cik))
    rb.CF_UNIVERSE = files
    rb.EXTRA = True
    tab = rb.feature_tables("companyfacts")
    tabs = {}

    ins = tab["ins"][0].copy()                                # A, L, cash, debt, ppe, inv, BE, CA, CL, AG, NOA, DPI2A
    ins["WC"] = ins.CA - ins.cash - ins.CL
    ins["NCL"] = ins.L - ins.CL
    ins = lag(ins, ["debt", "WC", "NCL", "CA"], 4, "_y")
    ins = lag(ins, ["debt"], 12, "_3y")
    ins["dWC"] = (ins.WC - ins.WC_y) / ins.A_1
    ins["dDEBT"] = (ins.debt - ins.debt_y) / ins.A_1
    ins["DEBTGR3"] = np.log((ins.debt + 1) / (ins.debt_3y + 1))
    ins["dNCL"] = (ins.NCL - ins.NCL_y) / ins.A_1
    ins["INVGR"] = (ins.inv - ins.inv_1) / ins.A_1
    ins["PPEGR"] = np.log(ins.ppe / ins.ppe_1)
    ins["CAGR"] = np.log(ins.CA / ins.CA_y)
    ins["LEV"] = ins.L / ins.A
    ins["ABE"] = ins.A / ins.BE.where(ins.BE > 0)
    ins["CASHAT"] = ins.cash / ins.A
    ins["LOGA"] = np.log(ins.A)
    tabs["ins"] = (ins, ["AG", "NOA", "DPI2A", "dWC", "dDEBT", "DEBTGR3", "dNCL", "INVGR", "PPEGR", "CAGR",
                         "LEV", "ABE", "CASHAT", "LOGA", "BE", "debt", "cash", "A"])

    # quarterly NI with Q4 filled (niw table): SUE, NI increases, earnings variability, dROA
    q = tab["niw"][0][["cik", "q", "ann", "ni"]].copy()
    assets = ins[["cik", "q", "A"]]
    q = q.merge(assets.assign(q=assets.q + 1), on=["cik", "q"], how="left")       # assets of q-1
    q["ROA"] = q.ni / q.A
    for k in range(1, 12):
        q = lag(q, ["ni"], k, f"_{k}")
    q = lag(q, ["ROA"], 4, "_y")
    chg = pd.concat([q["ni" if j == 0 else f"ni_{j}"] - q[f"ni_{j + 4}"] for j in range(0, 8)], axis=1)
    q["SUE"] = chg.iloc[:, 0] / chg.iloc[:, 1:].std(axis=1)
    inc = (chg > 0).astype(float).where(chg.notna())
    q["NIINC"] = inc.cumprod(axis=1).sum(axis=1, min_count=1)
    roa8 = pd.concat([q["ni" if j == 0 else f"ni_{j}"] for j in range(8)], axis=1).div(q.A, axis=0)
    q["EVAR"] = roa8.std(axis=1).where(roa8.notna().sum(axis=1) >= 6)
    q["dROA"] = q.ROA - q.ROA_y
    tabs["q"] = (q, ["ROA", "SUE", "NIINC", "EVAR", "dROA"])

    tabs["sh"] = tab["sh"]                                    # split-safe 1-year share growth (NI)
    tabs["osc"] = tab["osc"]

    # annual: profitability, margins, growth, F-score
    a = rb.load("annual", "companyfacts")
    a["ni"] = rb.first(a, ["netincomeloss", "profitloss"])
    a["cfo"] = rb.first(a, ["netcashprovidedbyusedinoperatingactivities"])
    a["rev"] = rb.first(a, ["revenues", "revenuefromcontractwithcustomerexcludingassessedtax"])
    cost = rb.first(a, ["costofrevenue", "costofgoodsandservicessold"])
    a["gp"] = rb.first(a, ["grossprofit"]).fillna(a.rev - cost)
    a["op"] = rb.first(a, ["operatingincomeloss"])
    a = a[["cik", "q", "ann", "ni", "cfo", "rev", "gp", "op"]].merge(
        ins[["cik", "q", "A", "A_1", "L", "BE", "CA", "CL", "debt"]], on=["cik", "q"], how="left")
    a = lag(a, ["ni", "cfo", "rev", "gp", "A", "BE", "CA", "CL", "debt"], 4, "_y")
    be = a.BE.where(a.BE > 0)
    a["AC"] = (a.ni - a.cfo) / a[["A", "A_1"]].mean(axis=1)
    a["ACNI"] = (a.ni - a.cfo) / a.ni.abs()
    a["PROF"] = a.gp / a.A
    a["ROE"] = a.ni / be
    a["OPBE"] = a.op / be
    a["OPA"] = a.op / a.A
    a["CFOA"] = a.cfo / a.A
    a["ATO"] = a.rev / a.A
    a["GM"] = a.gp / a.rev
    a["SALEGR"] = np.log(a.rev / a.rev_y)
    gm_y = a.gp_y / a.rev_y
    a["dGM"] = a.GM - gm_y
    a["dROE"] = a.ROE - a.ni_y / a.BE_y.where(a.BE_y > 0)
    a["dCFOA"] = a.CFOA - a.cfo_y / a.A_y
    roa, roa_y = a.ni / a.A_1, a.ni_y / a.A_y
    sh = tab["sh"][0][["cik", "q", "NI"]]
    a = a.merge(sh, on=["cik", "q"], how="left")
    sig = pd.concat([roa > 0, a.cfo > 0, roa > roa_y, a.cfo > a.ni, a.debt / a.A < a.debt_y / a.A_y,
                     a.CA / a.CL > a.CA_y / a.CL_y, a.NI <= 0, a.GM > gm_y, a.ATO > a.rev_y / a.A_y], axis=1)
    known = pd.concat([roa, a.cfo, roa_y, a.ni, a.debt_y, a.CL_y, a.NI, gm_y, a.rev_y], axis=1).notna()
    sig.columns = known.columns = range(9)
    nk = known.sum(axis=1).astype(float)
    a["FSCORE"] = (sig & known).sum(axis=1).astype(float) / nk.replace(0, np.nan) * 9
    a["FSCORE"] = a.FSCORE.where(nk >= 6)
    tabs["an"] = (a, ["AC", "ACNI", "PROF", "ROE", "OPBE", "OPA", "CFOA", "ATO", "GM", "SALEGR", "dGM", "dROE",
                      "dCFOA", "FSCORE", "ni", "cfo", "rev", "op"])

    # restated diluted shares per quarter (value from the LATEST filing, dated by the first one)
    raw = rb._CF["raw"]
    s = raw[(raw.key == "shares") & (raw.days >= 80) & (raw.days <= 100)]
    first = s.groupby(["cik", "end"]).filed.min().rename("ann")
    last = s.sort_values("filed").groupby(["cik", "end"]).val.last().rename("SHR")
    s = pd.concat([first, last], axis=1).reset_index()
    s["q"] = (s.end - pd.Timedelta(days=45)).dt.to_period("Q")
    s = s.sort_values("end").drop_duplicates(["cik", "q"], keep="last")
    s = lag(s, ["SHR"], 12, "_3y")
    s["NI3"] = np.log(s.SHR / s.SHR_3y)
    tabs["shr"] = (s, ["SHR", "NI3"])
    return tabs


def market(cik_of, ret, spy):
    d = pb.daily_returns(cik_of)
    px = pd.read_parquet(data.DATA / "prices_sp500_pit.parquet")
    m = px["SPY"].pct_change(fill_method=None).reindex(d.index)
    vm = m.rolling(252, min_periods=126).var()
    beta = d.rolling(252, min_periods=126).cov(m).div(vm, axis=0)
    var = d.rolling(252, min_periods=126).var()
    ivol = np.sqrt((var - beta.pow(2).mul(vm, axis=0)).clip(lower=0))
    mon = lambda x: x.resample("ME").last().reindex(ret.index)
    gm = d.groupby(d.index.to_period("M"))
    maxret = gm.max()
    max5 = gm.apply(lambda x: x.where(x.rank(ascending=False, method="first") <= 5).mean()
                    .where(x.notna().sum() >= 10))
    for z in (maxret, max5):
        z.index = z.index.to_timestamp(how="end").normalize()
    wrev = np.expm1(np.log1p(d).rolling(5, min_periods=4).sum())
    lr = np.log1p(ret)
    mret = np.log1p(spy).reindex(ret.index)
    cov60 = lr.rolling(60, min_periods=36).cov(mret)
    beta60 = cov60.div(mret.rolling(60, min_periods=36).var(), axis=0)
    res = lr.sub(beta60.shift(1).mul(mret, axis=0))                      # residual vs market, beta known at t-1
    resmom = res.shift(1).rolling(11, min_periods=11).sum() / res.shift(1).rolling(36, min_periods=24).std()
    seas = lambda ks: pd.concat([ret.shift(12 * k - 1) for k in ks]).groupby(level=0).mean()
    cnt25 = pd.concat([ret.shift(12 * k - 1).notna() for k in range(2, 6)]).groupby(level=0).sum()
    close = pd.read_parquet(data.DATA / "close_sp500_pit.parquet")
    close = close[[c for c in close if c in cik_of and c not in pb.RECYCLED]]
    cm = close.resample("ME").last()
    cm.columns = [cik_of[c] for c in cm.columns]
    cm = cm.T.groupby(level=0).first().T.reindex(ret.index)
    return {"BETA": mon(beta), "IVOL": mon(ivol), "VOL": mon(np.sqrt(var)), "BETA60": beta60,
            "MAXRET": maxret.reindex(ret.index), "MAX5": max5.reindex(ret.index), "WREV": mon(wrev),
            "r12_2": np.expm1(lr.shift(1).rolling(11, min_periods=11).sum()),
            "r6_1": np.expm1(lr.shift(1).rolling(5, min_periods=5).sum()),
            "r9_1": np.expm1(lr.shift(1).rolling(8, min_periods=8).sum()),
            "RESMOM": resmom, "STREV": ret, "SEAS1": ret.shift(11),
            "SEAS25": seas(range(2, 6)).where(cnt25 >= 2), "CLOSE": cm}


def build_panel(cik_of, tabs, ret, mk):
    mem = pb.membership()
    fwd = ret.shift(-1)
    rows = []
    for t in ret.index[(ret.index >= "2012-01-31") & (ret.index <= ret.index[-2])]:
        lst = mem[mem.index <= t].iloc[-1]
        members = {cik_of[x] for x in lst if x in cik_of}
        f = rb.asof(tabs, t).replace([np.inf, -np.inf], np.nan)
        f = f[f.index.isin(members)].copy()
        for k in ("BETA", "IVOL", "VOL", "BETA60", "MAXRET", "MAX5", "WREV", "r12_2", "r6_1", "r9_1", "RESMOM",
                  "STREV", "SEAS1", "SEAS25"):
            f[k] = mk[k].loc[t].reindex(f.index)
        f["ME"] = f.SHR * mk["CLOSE"].loc[t].reindex(f.index)
        me = f.ME.where(f.ME > 0)
        f["BM"] = f.BE / me
        f["EP"] = f.ni / me
        f["CFP"] = f.cfo / me
        f["SP"] = f.rev / me
        f["AME"] = f.A / me
        f["DME"] = f.debt / me
        f["NDME"] = (f.debt - f.cash) / me
        f["EBITEV"] = f.op / (me + f.debt.fillna(0) - f.cash.fillna(0))
        f["fwd"] = fwd.loc[t].reindex(f.index)
        rows.append(f.dropna(subset=["fwd"]).assign(date=t))
    p = pd.concat(rows).rename_axis("cik").reset_index()
    for k, s in SIGN.items():
        p["P_" + k] = p.groupby("date")[k].rank(pct=True, ascending=s > 0)
    return p


def ls_returns(p):
    out = {}
    for k in SIGN:
        q = np.ceil(p.groupby("date")["P_" + k].rank(pct=True, method="first") * 5)
        g = p.assign(q=q).groupby(["date", "q"]).fwd.mean().unstack()
        out[k] = g.get(5.0) - g.get(1.0)
    return pd.DataFrame(out)


def weights(R):
    """Weights known at the formation month t (factor returns R are dated by formation month)."""
    sig = R.rolling(36, min_periods=24).std()
    p12 = R.rolling(12, min_periods=12).sum()
    raw = {"estatico": 1 / sig, "TSFM 12m": np.sign(p12) / sig, "solo ganadores 12m": (p12 > 0) / sig,
           "TSFM 1m": np.sign(R) / sig}
    out = {}
    for k, w in raw.items():
        w = w.where(sig.notna() & p12.notna())
        out[k] = w.div(w.abs().sum(axis=1), axis=0)
    return out


def book(p, w, n, spr):
    """N long / N short on the composite sum_k w_k (P_k - 0.5); w: months x indicators."""
    prev, rows = pd.Series(dtype=float), []
    pcols = ["P_" + k for k in w.columns]
    for t, g in p.groupby("date"):
        if t not in w.index or w.loc[t].isna().all():
            continue
        wt = w.loc[t].fillna(0)
        X = g[pcols].sub(0.5)
        X.columns = w.columns
        score = (X * wt).sum(axis=1) / (X.notna() * wt.abs()).sum(axis=1)
        score = score.where(X.notna().sum(axis=1) >= 0.6 * len(pcols))
        g = g.assign(S=score).dropna(subset=["S"])
        r = g.S.rank(method="first")
        L, S = g[r > len(g) - n], g[r <= n]
        ww = pd.concat([pd.Series(1 / n, index=L.cik.values), pd.Series(-1 / n, index=S.cik.values)])
        turn = ww.sub(prev, fill_value=0).abs()
        cost = sum(turn[c] * (spr.get(c, 0.0008) + COMM) for c in turn.index)
        gross = L.fwd.mean() - S.fwd.mean()
        rows.append((t, gross, gross - cost - DIV_WHT, turn.sum() / 4))
        prev = ww
    return pd.DataFrame(rows, columns=["date", "bruto", "neto", "rotacion"]).set_index("date")


def stats(s):
    s = s.dropna()
    eq = (1 + s).cumprod()
    return {"%/mes": 100 * s.mean(), "t": rb.stats(s)["t"], "sharpe": s.mean() / s.std() * np.sqrt(12),
            "vol_%": 100 * s.std() * np.sqrt(12), "max_dd_%": 100 * (eq / eq.cummax() - 1).min(),
            "2013-2016": 100 * s.loc["2013":"2016"].mean(), "2017-2021": 100 * s.loc["2017":"2021"].mean(),
            "2022-2026": 100 * s.loc["2022":].mean(), "meses": len(s)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    hist = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    uni = universe().drop_duplicates("cik")
    cik_of = {**hist, **dict(zip(uni.symbol, uni.cik))}
    ret, spy = pb.monthly_returns(cik_of)
    tabs = accounting(cik_of)
    mk = market(cik_of, ret, spy)
    p = build_panel(cik_of, tabs, ret, mk)
    p.to_parquet(OUT / "sec2_panel.parquet")
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()

    R = ls_returns(p)                                   # dated by formation month t (realised in t+1)
    T = R.T.groupby(THEME_OF).mean().T                  # themes
    R.to_csv(OUT / "sec2_indicadores.csv", float_format="%.5f")
    ind = pd.DataFrame([{"tema": THEME_OF[k], "indicador": k, "cobertura": p[k].notna().mean(), **stats(R[k])}
                        for k in R])
    ind.to_csv(OUT / "sec2_indicadores_resumen.csv", index=False, float_format="%.4f")

    rows, series = [], {}
    for level, M in (("indicadores", R), ("13 temas", T)):
        W = weights(M.shift(0))
        for k, w in W.items():
            fac = (w.shift(1) * M).sum(axis=1, min_count=1).where(w.shift(1).notna().any(axis=1))
            series[f"factores|{level}|{k}"] = fac
            rows.append({"cartera": f"Factores, {level}, {k} (bruto)", **stats(fac)})
    # stock books: weights on indicators (themes: each indicator gets its theme's weight / n indicators)
    WI = weights(R)
    WT = weights(T)
    for scheme in ("estatico", "solo ganadores 12m", "TSFM 12m"):
        w_theme = WT[scheme]
        w_ind = pd.DataFrame({k: w_theme[THEME_OF[k]] / len(INDICATORS[THEME_OF[k]]) for k in SIGN})
        for lab, w in ((f"indicadores {scheme}", WI[scheme]), (f"temas {scheme}", w_ind)):
            for n in (25, 50):
                b = book(p, w.shift(1), n, spr)          # weights from factor returns known at t
                series[f"libro{n}|{lab}|neto"] = b.neto
                rows.append({"cartera": f"Libro {n}/{n}, {lab}, bruto", **stats(b.bruto)})
                rows.append({"cartera": f"Libro {n}/{n}, {lab}, neto Zero", **stats(b.neto),
                             "rotacion_%mes": 100 * b.rotacion.iloc[1:].mean()})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "sec2_resumen.csv", index=False, float_format="%.4f")
    pd.DataFrame(series).to_csv(OUT / "sec2_retornos.csv", float_format="%.5f")
    T.to_csv(OUT / "sec2_temas.csv", float_format="%.5f")
    pd.set_option("display.width", 250)
    print(ind.round(2).to_string(index=False))
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
