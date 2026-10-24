"""The 13 Jensen-Kelly-Pedersen themes on the point-in-time S&P 500, 2012-2026 (SEC + ml4t-data).

Same universe, data and costs as the short strategy's pit_backtest.py: index members at each
month-end, SEC companyfacts as filed, Yahoo + AlgoSeek prices joined by CIK, Darwinex Zero costs
(measured half spread or 8 bp, commission, 15 % withholding on long dividends, no swaps).
Market value ME = last 10-K public float carried forward with the total return (pit_backtest).

Theme characteristics (+ = expected to outperform):
  Accruals        AC -
  Debt Issuance   1-year change in debt / assets -
  Investment      AG -, NOA -, DPI2A -, net share issuance -
  Low Leverage    liabilities / assets -
  Low Risk        beta (252 d) -, idiosyncratic vol -, total vol -
  Momentum        r12_2 +, r12_7 +
  Profit Growth   1-year change in quarterly ROA +
  Profitability   gross profit / assets +, net income / book equity +
  Quality         ROA +, asset turnover +, gross margin +
  Seasonality     same-calendar-month return over the previous years (min 3) +
  ST Reversal     last month return -
  Size            ME -
  Value           B/M +, E/P +, CF/P +, S/P +
"""
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

import data
import pit_backtest as pb
import recent_backtest as rb
from cpz_mispricing import factors
from darwinex_sim import COMM, DIV_WHT
from live_syy import SEC
from repo_xbrl import universe

OUT = data.ROOT / "results" / "kelly"
THEMES = {
    "Accruals": {"AC": -1}, "Debt Issuance": {"dDEBT": -1},
    "Investment": {"AG": -1, "NOA": -1, "DPI2A": -1, "NI": -1}, "Low Leverage": {"LEV": -1},
    "Low Risk": {"BETA": -1, "IVOL": -1, "VOL": -1}, "Momentum": {"r12_2": 1, "r12_7": 1},
    "Profit Growth": {"dROA": 1}, "Profitability": {"PROF": 1, "ROE": 1},
    "Quality": {"ROA": 1, "ATO": 1, "GM": 1}, "Seasonality": {"SEAS": 1},
    "Short-Term Reversal": {"STREV": -1}, "Size": {"ME": -1},
    "Value": {"BM": 1, "EP": 1, "CFP": 1, "SP": 1},
}


def tables_and_market():
    hist = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    uni = universe().drop_duplicates("cik")
    cik_of = {**hist, **dict(zip(uni.symbol, uni.cik))}
    files = []
    for cik in set(cik_of.values()):
        tic = next((t for t, c in sorted(cik_of.items()) if c == cik and (SEC / "facts" / f"{t}.parquet").exists()), None)
        if tic:
            files.append((tic, cik))
    rb.CF_UNIVERSE = files
    rb.EXTRA = True
    tab = rb.feature_tables("companyfacts")
    ret, spy = pb.monthly_returns(cik_of)
    mkt = pb.market_inputs(ret, spy, cik_of)
    fl = pb.float_table(mkt["lntr"])

    ins = tab["ins"][0].copy()
    ins = rb.lagged(ins, ["debt"], 4, "_1")
    ins["dDEBT"] = (ins.debt - ins.debt_1) / ins.A_1
    ins["LEV"] = ins.L / ins.A
    qn = rb.lagged(tab["qn"][0].copy(), ["ROA"], 4, "_1")
    qn["dROA"] = qn.ROA - qn.ROA_1
    an = tab["an"][0].copy()
    an["ATO"] = an.rev / an.A
    an["GM"] = an.gp / an.rev
    an = an.merge(tab["bal"][0][["cik", "q", "BE"]], on=["cik", "q"], how="left")
    an["ROE"] = an.ni / an.BE.where(an.BE > 0)
    tables = {"ins": (ins, ["AG", "NOA", "DPI2A", "dDEBT", "LEV", "BE"]), "qn": (qn, ["ROA", "dROA"]),
              "sh": tab["sh"], "an": (an, ["AC", "PROF", "ATO", "GM", "ROE", "ni", "cfo", "rev"]),
              "fl": (fl, ["lnN"])}

    d = pb.daily_returns(cik_of)
    px = pd.read_parquet(data.DATA / "prices_sp500_pit.parquet")
    m = px["SPY"].pct_change(fill_method=None).reindex(d.index)
    vm = m.rolling(252, min_periods=126).var()
    beta = d.rolling(252, min_periods=126).cov(m).div(vm, axis=0)
    var = d.rolling(252, min_periods=126).var()
    ivol = np.sqrt((var - beta.pow(2).mul(vm, axis=0)).clip(lower=0))
    me_ = lambda x: x.resample("ME").last().reindex(ret.index)
    lr = np.log1p(ret)
    seas = pd.concat([ret.shift(12 * k) for k in range(1, 6)]).groupby(level=0)
    market = {"BETA": me_(beta), "IVOL": me_(ivol), "VOL": me_(np.sqrt(var)),
              "r12_2": np.expm1(lr.shift(1).rolling(11, min_periods=11).sum()),
              "r12_7": np.expm1(lr.shift(6).rolling(6, min_periods=6).sum()),
              "STREV": ret, "SEAS": (seas.sum(min_count=3) / seas.count().replace(0, np.nan)).where(seas.count() >= 3),
              "lntr": mkt["lntr"]}
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()
    return cik_of, tables, ret, spy, market, spr


def build_panel(cik_of, tables, ret, market):
    mem = pb.membership()
    fwd = ret.shift(-1)
    rows = []
    for t in ret.index[(ret.index >= "2012-01-31") & (ret.index <= ret.index[-2])]:
        lst = mem[mem.index <= t].iloc[-1]
        members = {cik_of[x] for x in lst if x in cik_of}
        f = rb.asof(tables, t).replace([np.inf, -np.inf], np.nan)
        f = f[f.index.isin(members)]
        for k in ("BETA", "IVOL", "VOL", "r12_2", "r12_7", "STREV", "SEAS"):
            f[k] = market[k].loc[t].reindex(f.index)
        f["ME"] = np.exp(f.lnN + market["lntr"].loc[t].reindex(f.index))
        f["BM"] = f.BE / f.ME
        f["EP"] = f.ni / f.ME
        f["CFP"] = f.cfo / f.ME
        f["SP"] = f.rev / f.ME
        f["fwd"] = fwd.loc[t].reindex(f.index)
        rows.append(f.dropna(subset=["fwd"]).assign(date=t))
    p = pd.concat(rows).rename_axis("cik").reset_index()
    for th, members in THEMES.items():
        z = pd.concat([p.groupby("date")[c].rank(pct=True) * s for c, s in members.items()], axis=1).mean(axis=1)
        p["T_" + th] = z.groupby(p.date).rank(pct=True)
    tc = ["T_" + t for t in THEMES]
    p["n_temas"] = p[tc].notna().sum(axis=1)
    p["S"] = p[tc].mean(axis=1).where(p.n_temas >= 9)
    return p


def quint_ls(p, col):
    q = np.ceil(p.groupby("date")[col].rank(pct=True, method="first") * 5)
    g = p.assign(q=q).groupby(["date", "q"]).fwd.mean().unstack()
    return g[5.0] - g[1.0]


def book(p, n, spr):
    prev, rows = pd.Series(dtype=float), []
    for t, g in p.dropna(subset=["S"]).groupby("date"):
        r = g.S.rank(method="first")
        L, S = g[r > len(g) - n], g[r <= n]
        w = pd.concat([pd.Series(1 / n, index=L.cik.values), pd.Series(-1 / n, index=S.cik.values)])
        turn = w.sub(prev, fill_value=0).abs()
        cost = sum(turn[c] * (spr.get(c, 0.0008) + COMM) for c in turn.index)
        gross = L.fwd.mean() - S.fwd.mean()
        rows.append((t, gross, gross - cost - DIV_WHT, turn.sum() / 4))
        prev = w
    return pd.DataFrame(rows, columns=["date", "bruto", "neto", "rotacion"]).set_index("date")


def stats(s, ff):
    s = s.dropna()
    eq = (1 + s).cumprod()
    out = {"media_%mes": 100 * s.mean(), "t": rb.stats(s)["t"], "sharpe": s.mean() / s.std() * np.sqrt(12),
           "vol_%": 100 * s.std() * np.sqrt(12), "max_dd_%": 100 * (eq / eq.cummax() - 1).min(),
           "2012-2016": 100 * s.loc["2012":"2016"].mean(), "2017-2021": 100 * s.loc["2017":"2021"].mean(),
           "2022-2026": 100 * s.loc["2022":].mean(), "meses": len(s)}
    x = s.copy()
    x.index = x.index.to_period("M") + 1
    f = ff.reindex(x.index)[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]].dropna()
    o = sm.OLS(x.reindex(f.index), sm.add_constant(f)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    out.update(alfa_FF6_mes=100 * o.params["const"], t_alfa=o.tvalues["const"], beta_mkt=o.params["Mkt-RF"])
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cik_of, tables, ret, spy, market, spr = tables_and_market()
    p = build_panel(cik_of, tables, ret, market)
    p.to_parquet(OUT / "sec_panel.parquet")
    ff = factors()
    ls = pd.DataFrame({t: quint_ls(p, "T_" + t) for t in THEMES})
    combo = {"Combinado EW (13 temas, bruto)": ls.mean(axis=1)}
    books = {n: book(p, n, spr) for n in (10, 25, 50)}
    rows = [{"cartera": t, **stats(ls[t], ff)} for t in THEMES]
    rows += [{"cartera": k, **stats(v, ff)} for k, v in combo.items()]
    for n, b in books.items():
        rows += [{"cartera": f"Libro {n}/{n}, bruto", **stats(b.bruto, ff)},
                 {"cartera": f"Libro {n}/{n}, neto Zero", **stats(b.neto, ff), "rotacion_%mes": 100 * b.rotacion.iloc[1:].mean()}]
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "sec_resumen.csv", index=False, float_format="%.4f")
    ls.corr().to_csv(OUT / "sec_correlaciones.csv", float_format="%.3f")
    allr = ls.join(pd.DataFrame(combo))
    for n, b in books.items():
        allr[f"libro{n}_bruto"], allr[f"libro{n}_neto"] = b.bruto, b.neto
    allr.to_csv(OUT / "sec_retornos.csv", float_format="%.5f")
    pd.set_option("display.width", 250)
    print(res.round(2).to_string(index=False))
    print("acciones/mes:", round(p.groupby("date").S.count().mean()), " cobertura de temas:",
          {t: round(p["T_" + t].notna().mean(), 2) for t in THEMES})


if __name__ == "__main__":
    main()
