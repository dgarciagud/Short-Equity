"""Stambaugh-Yu-Yuan (2015) mispricing score on the Chen-Pelger-Zhu panel.

CPZ (CRSP/Compustat, delisted firms included, 1967-2016): each row holds the
characteristics known at the end of the previous month (cross-sectional ranks in
[-0.5, 0.5]) and the excess return of the row's month. 8 of the 11 SYY anomalies
are available; financial distress, O-score and composite equity issues are not.

M = average of the 8 anomaly percentiles, oriented so that a high percentile means
the anomaly predicts LOW returns (overpriced). Shorts = top quintile of M.
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

import data

OUT = data.ROOT / "results" / "cpz"
OUT.mkdir(parents=True, exist_ok=True)

# +1: high value -> overpriced (low future return); -1: low value -> overpriced
ANOMALIES = {
    "NI": +1,          # net stock issues (Ritter; Loughran-Ritter; Fama-French)
    "AC": +1,          # total/operating accruals (Sloan 1996)
    "NOA": +1,         # net operating assets (Hirshleifer et al. 2004)
    "r12_2": -1,       # momentum (Jegadeesh-Titman 1993)
    "PROF": -1,        # gross profitability (Novy-Marx 2013)
    "Investment": +1,  # asset growth (Cooper-Gulen-Schill 2008)
    "ROA": -1,         # return on assets (Fama-French 2006; Chen-Novy-Marx-Zhang)
    "DPI2A": +1,       # investment-to-assets (Titman-Wei-Xie 2004)
}
# float = LME rank cut-off; int = top-N stocks by LME each month (500 ~ S&P 500 by count)
SIZES = {"Todas": -1.0, "Grandes (top 30% LME)": 0.2, "Top 500 (≈S&P 500)": 500,
         "Mega (top 10% LME)": 0.4}


def size_filter(p, cut):
    if isinstance(cut, int):
        return p[p.groupby("month").LME.rank(ascending=False, method="first") <= cut].copy()
    return p[p.LME > cut].copy()
COST = 0.0010  # one-way, for net figures


def load():
    cols = ["date", "firm", "ret", "IdioVol", "LME"] + list(ANOMALIES)
    p = pd.read_parquet(data.DATA / "cpz_panel.parquet", columns=cols)
    p["month"] = p.date.dt.to_period("M")  # month of the return; chars are lagged
    for k, s in ANOMALIES.items():
        p["pct_" + k] = s * p[k] + 0.5
    pct = [c for c in p if c.startswith("pct_")]
    p["M"] = p[pct].mean(axis=1)
    p["M_sin_mom"] = p[[c for c in pct if c != "pct_r12_2"]].mean(axis=1)
    return p


def factors():
    f = pd.read_parquet(data.DATA / "ff" / "ff5_monthly.parquet")
    m = pd.read_parquet(data.DATA / "ff" / "mom_monthly.parquet")
    f = f.merge(m, on="timestamp")
    f["month"] = pd.to_datetime(f.timestamp).dt.to_period("M")
    return f.set_index("month").drop(columns="timestamp")


def bins(x, n):
    return np.ceil(x.rank(method="first", pct=True) * n).clip(1, n)


def tstat(r, lags=3):
    r = r.dropna()
    return sm.OLS(r.values, np.ones(len(r))).fit(cov_type="HAC", cov_kwds={"maxlags": lags}).tvalues[0]


def alpha(r, ff, cols):
    r = r.dropna()
    x = ff.reindex(r.index)[cols].dropna()
    y = r.reindex(x.index)
    res = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    return res.params["const"], res.tvalues["const"]


def summarize(r, ff):
    a3, t3 = alpha(r, ff, ["Mkt-RF", "SMB", "HML"])
    a6, t6 = alpha(r, ff, ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"])
    return {"media_%mes": 100 * r.mean(), "t": tstat(r), "alfa_FF3_%mes": 100 * a3, "t_FF3": t3,
            "alfa_FF6_%mes": 100 * a6, "t_FF6": t6, "vol_anual_%": 100 * r.std() * np.sqrt(12),
            "sharpe": r.mean() / r.std() * np.sqrt(12), "meses": r.notna().sum()}


def turnover(p, mask):
    """Average one-way turnover of an EW portfolio defined by mask (fraction replaced)."""
    w = p[mask].assign(w=1.0).groupby("month").w.transform(lambda s: 1 / len(s))
    W = p[mask].assign(w=w).pivot_table(index="month", columns="firm", values="w", fill_value=0)
    return 0.5 * W.diff().abs().sum(axis=1).iloc[1:].mean()


def main():
    p, ff = load(), factors()
    rows, series = [], {}

    # 1. each anomaly's direction, verified in 1967-1986 and over the full sample
    for k in list(ANOMALIES) + ["M", "M_sin_mom"]:
        col = k if k in ("M", "M_sin_mom") else "pct_" + k
        q = p.groupby("month")[col].transform(lambda x: bins(x, 5))
        r = p.groupby([p.month, q]).ret.mean().unstack()
        ls = r[1.0] - r[5.0]  # underpriced - overpriced
        for per, sl in (("1967-1986", slice("1967", "1986")), ("1967-2016", slice(None))):
            s = ls.loc[sl]
            rows.append({"bloque": "anomalia", "nombre": k, "periodo": per,
                         **summarize(s, ff), "corto_Q5_%mes": 100 * r[5.0].loc[sl].mean()})
    pd.DataFrame(rows).to_csv(OUT / "anomalias.csv", index=False, float_format="%.4f")

    # 2. M quintiles by size bucket, short leg and hedges
    res = []
    for sz, cut in SIZES.items():
        d = size_filter(p, cut)
        d["qM"] = d.groupby("month").M.transform(lambda x: bins(x, 5))
        d["qMom"] = d.groupby("month").r12_2.transform(lambda x: bins(x, 5))
        d["qM2"] = d.groupby("month").M_sin_mom.transform(lambda x: bins(x, 5))
        d["qIV"] = d.groupby("month").IdioVol.transform(lambda x: bins(x, 5))
        ew = d.groupby("month").ret.mean()
        legs = {
            "SYY M: Q5 sobrevaloradas": d.qM == 5,
            "SYY M sin momentum: Q5": d.qM2 == 5,
            "Momentum: Q1 perdedores": d.qMom == 1,
            "Perdedoras Y sobrevaloradas (Q1 mom & Q5 M)": (d.qMom == 1) & (d.qM == 5),
            "Perdedoras NO sobrevaloradas (Q1 mom & M<=Q3)": (d.qMom == 1) & (d.qM <= 3),
            "Sobrevaloradas Y alta IVOL (Q5 M & Q5 IVOL)": (d.qM == 5) & (d.qIV == 5),
            "Sobrevaloradas Y baja IVOL (Q5 M & Q1 IVOL)": (d.qM == 5) & (d.qIV == 1),
        }
        long_m = d.qM == 1
        r_long = d[long_m].groupby("month").ret.mean()
        for name, mask in legs.items():
            rs = d[mask].groupby("month").ret.mean().reindex(ew.index)
            to = turnover(d, mask)
            for kind, s in (("corto solo (−R, exceso s/ T-bill)", -rs),
                            ("corto cubierto con mercado EW", ew - rs),
                            ("L/S: Q1 M largo − corto", r_long - rs)):
                st = summarize(s, ff)
                st.update(universo=sz, estrategia=name, pierna=kind, n_medio=mask.groupby(d.month).sum().mean(),
                          rotacion_mensual=to,
                          sharpe_neto_aprox=(s.mean() - COST * 2 * to * (2 if kind.startswith("L/S") else 1))
                          / s.std() * np.sqrt(12))
                res.append(st)
                series[f"{sz}|{name}|{kind}"] = s
    res = pd.DataFrame(res)
    first = ["universo", "estrategia", "pierna"]
    res[first + [c for c in res if c not in first]].to_csv(OUT / "cortos.csv", index=False, float_format="%.4f")
    ser = pd.DataFrame(series)
    ser.index = ser.index.to_timestamp()
    ser.to_parquet(OUT / "series.parquet")

    # 3. 5x5 independent sort M x IVOL (SYY 2015, Table II): FF3 alpha, %/month
    for sz, cut in SIZES.items():
        d = size_filter(p, cut)
        d["qM"] = d.groupby("month").M.transform(lambda x: bins(x, 5))
        d["qIV"] = d.groupby("month").IdioVol.transform(lambda x: bins(x, 5))
        r = d.groupby(["month", "qM", "qIV"]).ret.mean().unstack(["qM", "qIV"])
        tab_a = pd.DataFrame(index=range(1, 6), columns=range(1, 6), dtype=float)
        tab_t = tab_a.copy()
        for (m, v) in r.columns:
            a, t = alpha(r[(m, v)], ff, ["Mkt-RF", "SMB", "HML"])
            tab_a.loc[m, v], tab_t.loc[m, v] = 100 * a, t
        for m in range(1, 6):
            a, t = alpha(r[(m, 5.0)] - r[(m, 1.0)], ff, ["Mkt-RF", "SMB", "HML"])
            tab_a.loc[m, "IVOL5-IVOL1"], tab_t.loc[m, "IVOL5-IVOL1"] = 100 * a, t
        tab_a.index = [f"M Q{m}" for m in range(1, 6)]
        tab_t.index = tab_a.index
        tab_a.to_csv(OUT / f"ivol_x_M_alpha_{sz.split()[0]}.csv", float_format="%.3f")
        tab_t.to_csv(OUT / f"ivol_x_M_t_{sz.split()[0]}.csv", float_format="%.2f")

    # 4. sentiment (Baker-Wurgler, orthogonalised SENT^): high/low = above/below median
    #    of the PREVIOUS month's level; SYY 2012 Tables 2-3
    bw = pd.read_csv(data.DATA / "bw_sentiment.csv")
    bw["month"] = pd.PeriodIndex(bw.yearmo.astype(str), freq="M")
    sent = bw.set_index("month")["SENT_orth"].shift(1)  # known before the return month
    srows = []
    for sz in SIZES:
        for name in ["SYY M: Q5 sobrevaloradas", "Momentum: Q1 perdedores",
                     "Perdedoras Y sobrevaloradas (Q1 mom & Q5 M)",
                     "Sobrevaloradas Y alta IVOL (Q5 M & Q5 IVOL)"]:
            for kind in ("corto solo (−R, exceso s/ T-bill)", "corto cubierto con mercado EW",
                         "L/S: Q1 M largo − corto"):
                s = series[f"{sz}|{name}|{kind}"]
                st_ = sent.reindex(s.index)
                hi = st_ > st_.median()
                x = pd.concat([s, hi.rename("hi")], axis=1).dropna()
                d_ = x.iloc[:, 0][x.hi.astype(bool)].mean() - x.iloc[:, 0][~x.hi.astype(bool)].mean()
                X = sm.add_constant(x.hi.astype(float))
                t = sm.OLS(x.iloc[:, 0], X).fit(cov_type="HAC", cov_kwds={"maxlags": 3}).tvalues["hi"]
                a_hi = alpha(x.iloc[:, 0][x.hi.astype(bool)], ff, ["Mkt-RF", "SMB", "HML"])
                a_lo = alpha(x.iloc[:, 0][~x.hi.astype(bool)], ff, ["Mkt-RF", "SMB", "HML"])
                srows.append({"universo": sz, "estrategia": name, "pierna": kind,
                              "media_alto_%mes": 100 * x.iloc[:, 0][x.hi.astype(bool)].mean(),
                              "media_bajo_%mes": 100 * x.iloc[:, 0][~x.hi.astype(bool)].mean(),
                              "dif_%mes": 100 * d_, "t_dif": t,
                              "alfaFF3_alto_%mes": 100 * a_hi[0], "alfaFF3_bajo_%mes": 100 * a_lo[0],
                              "meses": len(x)})
    pd.DataFrame(srows).to_csv(OUT / "sentimiento.csv", index=False, float_format="%.4f")

    # 5. subperiods (SYY 2015 sample ends Jan-2011) and momentum-crash months
    sub = []
    crash = ff["MOM"].reindex(pd.PeriodIndex(ser.index, freq="M")).nsmallest(10).index.to_timestamp()
    for col in ser:
        sz, name, kind = col.split("|")
        if kind != "corto cubierto con mercado EW":
            continue
        s = ser[col]
        for per, sl in (("1967-1989", slice("1967", "1989")), ("1990-2010", slice("1990", "2010")),
                        ("2011-2016 (post SYY)", slice("2011", "2016"))):
            x = s.loc[sl].dropna()
            sub.append({"universo": sz, "estrategia": name, "periodo": per, "media_%mes": 100 * x.mean(),
                        "t": tstat(x), "sharpe": x.mean() / x.std() * np.sqrt(12)})
        sub.append({"universo": sz, "estrategia": name, "periodo": "10 peores meses MOM",
                    "media_%mes": 100 * s.reindex(crash).mean(), "t": np.nan, "sharpe": np.nan})
    pd.DataFrame(sub).to_csv(OUT / "subperiodos.csv", index=False, float_format="%.4f")
    print("ok", file=sys.stderr)


if __name__ == "__main__":
    main()
