"""The 13 factor themes of Jensen, Kelly and Pedersen (2023) combined into one portfolio,
CRSP / Chen-Pelger-Zhu panel 1967-2016, top 500 stocks by market cap (≈ S&P 500 ≈ Darwinex CFDs).

CPZ characteristics are cross-sectional ranks in [-0.5, 0.5] known at the start of the return
month. Each theme is the average of its signed characteristics (+ = expected to outperform);
three themes have no CPZ characteristic and use a proxy built from the panel itself:
  seasonality    average return in the same calendar month over the previous 5 years (min 3)
  profit growth  12-month change in the ROE rank
  debt issuance  minus the 12-month change in the leverage rank
Portfolios (equal weight, rebalanced monthly, inside the top 500):
  theme L/S      top minus bottom quintile of each theme score
  combinado EW   mean of the 13 theme L/S returns (gross; a factor-level benchmark)
  combinado IV   inverse-volatility weights, past 60 months, known at t
  libro N/N      composite score = mean of the 13 theme percentiles; long the N best, short the
                 N worst; net of Darwinex Zero costs (8 bp half spread + commission per trade,
                 15 % withholding on the long leg's dividends; no swaps)
"""
import numpy as np
import pandas as pd

import data
from cpz_mispricing import factors, tstat
from darwinex_sim import COMM, DIV_WHT, SPREAD

OUT = data.ROOT / "results" / "kelly"
THEMES = {
    "Accruals": {"AC": -1, "OA": -1},
    "Debt Issuance": {"dLev": -1},
    "Investment": {"Investment": -1, "DPI2A": -1, "NOA": -1, "NI": -1},
    "Low Leverage": {"Lev": -1},
    "Low Risk": {"Beta": -1, "IdioVol": -1, "Variance": -1, "Resid_Var": -1},
    "Momentum": {"r12_2": 1, "r12_7": 1},
    "Profit Growth": {"dROE": 1},
    "Profitability": {"PROF": 1, "OP": 1, "ROE": 1},
    "Quality": {"ROA": 1, "ATO": 1, "PCM": 1},
    "Seasonality": {"SEAS": 1},
    "Short-Term Reversal": {"ST_REV": -1},
    "Size": {"LME": -1},
    "Value": {"BEME": 1, "E2P": 1, "CF2P": 1, "S2P": 1},
}


def panel(top=500):
    chars = sorted({c for t in THEMES.values() for c in t} - {"SEAS", "dROE", "dLev"})
    p = pd.read_parquet(data.DATA / "cpz_panel.parquet", columns=["date", "firm", "ret"] + chars)
    p["month"] = p.date.dt.to_period("M")
    # proxies from the firm's own history (pivot over ALL firms, then keep the top 500)
    piv = lambda c: p.pivot_table(index="month", columns="firm", values=c)
    ret = piv("ret")
    full = pd.period_range(ret.index.min(), ret.index.max(), freq="M")
    ret = ret.reindex(full)
    seas = pd.concat([ret.shift(12 * k) for k in range(1, 6)]).groupby(level=0)
    seas = (seas.sum(min_count=3) / seas.count().replace(0, np.nan)).where(seas.count() >= 3)
    extra = {"SEAS": seas}
    for name, col in (("dROE", "ROE"), ("dLev", "Lev")):
        x = piv(col).reindex(full)
        extra[name] = x - x.shift(12)
    for name, x in extra.items():
        s = x.stack().rename(name)
        s.index.names = ["month", "firm"]
        p = p.join(s, on=["month", "firm"])
    p = p[p.groupby("month").LME.rank(ascending=False, method="first") <= top].copy()
    for t, members in THEMES.items():
        sc = sum(p[c].fillna(np.nan) * s for c, s in members.items()) / len(members) \
            if all(c in p for c in members) else np.nan
        # average the available members only
        sc = pd.concat([p[c] * s for c, s in members.items()], axis=1).mean(axis=1)
        p["T_" + t] = sc.groupby(p.month).rank(pct=True)
    tcols = ["T_" + t for t in THEMES]
    p["n_temas"] = p[tcols].notna().sum(axis=1)
    p["S"] = p[tcols].mean(axis=1).where(p.n_temas >= 9)
    return p


def quint_ls(p, col):
    q = np.ceil(p.groupby("month")[col].rank(pct=True, method="first") * 5)
    g = p.assign(q=q).groupby(["month", "q"]).ret.mean().unstack()
    return g[5.0] - g[1.0]


def book(p, n):
    prev_l, prev_s, rows = set(), set(), []
    for m, g in p.dropna(subset=["S"]).groupby("month"):
        r = g.S.rank(method="first")
        L = g[r > len(g) - n]
        S = g[r <= n]
        tl = 1 - len(prev_l & set(L.firm)) / n
        ts = 1 - len(prev_s & set(S.firm)) / n
        gross = L.ret.mean() - S.ret.mean()
        net = gross - 2 * (SPREAD + COMM) * (tl + ts) - DIV_WHT
        rows.append((m, gross, net, (tl + ts) / 2))
        prev_l, prev_s = set(L.firm), set(S.firm)
    return pd.DataFrame(rows, columns=["month", "bruto", "neto", "rotacion"]).set_index("month")


def stats(s):
    s = s.dropna()
    eq = (1 + s).cumprod()
    return {"media_%mes": 100 * s.mean(), "t": tstat(s), "sharpe": s.mean() / s.std() * np.sqrt(12),
            "vol_%": 100 * s.std() * np.sqrt(12), "max_dd_%": 100 * (eq / eq.cummax() - 1).min(),
            "1967-1989": 100 * s.loc[:"1989"].mean(), "1990-2006": 100 * s.loc["1990":"2006"].mean(),
            "2007-2016": 100 * s.loc["2007":].mean(), "meses": len(s)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = panel()
    ls = pd.DataFrame({t: quint_ls(p, "T_" + t) for t in THEMES})
    sig = ls.shift(1).rolling(60, min_periods=36).std()
    w = (1 / sig).div((1 / sig).sum(axis=1), axis=0)
    combo = {"Combinado EW (13 temas, bruto)": ls.mean(axis=1),
             "Combinado inversa vol. (bruto)": (ls * w).sum(axis=1, min_count=1).where(w.notna().any(axis=1))}
    books = {n: book(p, n) for n in (10, 25, 50)}
    rows = [{"cartera": t, **stats(ls[t])} for t in THEMES]
    rows += [{"cartera": k, **stats(v)} for k, v in combo.items()]
    for n, b in books.items():
        rows += [{"cartera": f"Libro {n} largos / {n} cortos, bruto", **stats(b.bruto)},
                 {"cartera": f"Libro {n} largos / {n} cortos, neto Zero", **stats(b.neto),
                  "rotacion_%mes": 100 * b.rotacion.iloc[1:].mean()}]
    res = pd.DataFrame(rows)
    ff = factors()
    for i, r in res.iterrows():
        s = (ls[r.cartera] if r.cartera in ls else combo.get(r.cartera))
        if s is None:
            n = int(r.cartera.split()[1])
            s = books[n]["neto" if "neto" in r.cartera else "bruto"]
        x = ff.reindex(s.index)[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]].dropna()
        import statsmodels.api as sm
        o = sm.OLS(s.reindex(x.index), sm.add_constant(x), missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        res.loc[i, "alfa_FF6_%mes"] = 100 * o.params["const"]
        res.loc[i, "t_alfa"] = o.tvalues["const"]
        res.loc[i, "beta_mkt"] = o.params["Mkt-RF"]
    res.to_csv(OUT / "cpz_resumen.csv", index=False, float_format="%.4f")
    ls.corr().to_csv(OUT / "cpz_correlaciones.csv", float_format="%.3f")
    out = ls.join(pd.DataFrame(combo)).join(pd.concat({f"libro{n}": b[["bruto", "neto"]] for n, b in books.items()},
                                                     axis=1).pipe(lambda d: d.set_axis(["_".join(c) for c in d.columns], axis=1)))
    out.index = out.index.astype(str)
    out.to_csv(OUT / "cpz_retornos.csv", float_format="%.5f")
    pd.set_option("display.width", 250)
    print(res.round(2).to_string(index=False))
    print(ls.corr().round(2).to_string())
    print("cobertura temas:", p.groupby("month").n_temas.mean().describe().round(1).to_dict())


if __name__ == "__main__":
    main()
