"""Recent out-of-sample backtest (2012-2026) of the SYY mispricing short strategy.

Data, all through the ML4T repository's libraries:
  fundamentals  SEC XBRL Frames panels built by repo_xbrl.py (repo downloader; each row
                dated by the filing of its last fact, so no look-ahead)
  prices        ml4t-data Yahoo provider (adjusted closes), repo_prices.py
Universe: today's S&P 500 members that Darwinex offers as CFDs (420 stocks). This is
SURVIVORSHIP-BIASED: firms that dropped out of the index are missing. The bias raises the
returns of the weakest stocks, so it works AGAINST the short side (conservative for shorts).

At each month-end t, for every stock, the latest fundamentals announced <= t are used:
  instant panel  -> AG, NOA, DPI2A (vs the same quarter a year earlier)
  quarterly NI   -> ROA (NI of the quarter / assets of the previous quarter)
  shares         -> NI  (log growth of diluted shares vs a year earlier)
  annual         -> AC  ((NI - CFO) / average assets), PROF (gross profit / assets)
  prices         -> r12_2 momentum
M = mean percentile (>= 5 of 8 anomalies). Portfolios are formed at t and held in t+1.
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

import data
from cpz_mispricing import factors
from repo_xbrl import OUT as FRAMES, universe

OUT = data.ROOT / "results" / "recent"
OUT.mkdir(parents=True, exist_ok=True)
SIGN = {"NI": 1, "AC": 1, "NOA": 1, "r12_2": -1, "PROF": -1, "AG": 1, "ROA": -1, "DPI2A": 1}
COMM = 0.000127
SPY_SIDE = 0.000025
DIV_WHT_SPY = 0.15 * 0.013 / 12
FIN_CLASSIC = (-0.055 + 0.021) / 360 * 365.25 / 12


def first(df, cols):
    out = pd.Series(np.nan, index=df.index)
    for c in cols:
        if c in df:
            out = out.fillna(df[c])
    return out


def load(name, base=FRAMES):
    df = pd.read_parquet(base / f"{name}.parquet")
    df["end"] = pd.to_datetime(df.fiscal_quarter_end)
    df["ann"] = pd.to_datetime(df.announcement_date)
    df["q"] = (df.end - pd.Timedelta(days=45)).dt.to_period("Q")
    return df.dropna(subset=["ann"]).sort_values("end").drop_duplicates(["cik", "q"], keep="last")


def lagged(df, cols, k, suffix):
    lag = df[["cik", "q"] + cols].copy()
    lag["q"] = lag.q + k
    return df.merge(lag.rename(columns={c: c + suffix for c in cols}), on=["cik", "q"], how="left")


def feature_tables(base=FRAMES):
    ins = load("instant", base)
    ins["A"] = ins.get("assets")
    eq = first(ins, ["stockholdersequityincludingportionattributabletononcontrollinginterest",
                     "stockholdersequity"])
    ins["L"] = first(ins, ["liabilities"]).fillna(ins.get("liabilitiesandstockholdersequity") - eq)
    ins["cash"] = first(ins, ["cashandcashequivalentsatcarryingvalue",
                              "cashcashequivalentsrestrictedcashandrestrictedcashequivalents"]).fillna(0) \
        + first(ins, ["shortterminvestments", "marketablesecuritiescurrent"]).fillna(0)
    ins["debt"] = first(ins, ["longtermdebtnoncurrent", "longtermdebt"]).fillna(0) \
        + first(ins, ["debtcurrent", "longtermdebtcurrent", "shorttermborrowings"]).fillna(0)
    ins["ppe"] = first(ins, ["propertyplantandequipmentnet"])
    ins["inv"] = first(ins, ["inventorynet"])
    base = ins[["cik", "q", "ann", "A", "L", "cash", "debt", "ppe", "inv"]]
    t_ins = lagged(base, ["A", "ppe", "inv"], 4, "_1")
    t_ins["AG"] = t_ins.A / t_ins.A_1 - 1
    t_ins["NOA"] = ((t_ins.A - t_ins.cash) - (t_ins.L - t_ins.debt)) / t_ins.A_1
    t_ins["DPI2A"] = ((t_ins.ppe - t_ins.ppe_1) + (t_ins.inv - t_ins.inv_1).fillna(0)) / t_ins.A_1
    assets = base[["cik", "q", "A"]]

    qn = load("quarterly", base)
    qn["ni"] = first(qn, ["netincomeloss", "profitloss"])
    qn = qn[["cik", "q", "ann", "ni"]].merge(assets.assign(q=assets.q + 1), on=["cik", "q"], how="left")
    qn["ROA"] = qn.ni / qn.A

    sh = load("shares", base)
    sh["sh"] = sh["weightedaveragenumberofdilutedsharesoutstanding"]
    sh = lagged(sh[["cik", "q", "ann", "sh"]], ["sh"], 4, "_1")
    sh["NI"] = np.log(sh.sh / sh.sh_1).where((sh.sh > 0) & (sh.sh_1 > 0))

    an = load("annual", base)
    an["ni"] = first(an, ["netincomeloss", "profitloss"])
    an["cfo"] = first(an, ["netcashprovidedbyusedinoperatingactivities"])
    rev = first(an, ["revenues", "revenuefromcontractwithcustomerexcludingassessedtax"])
    cost = first(an, ["costofrevenue", "costofgoodsandservicessold"])
    an["gp"] = first(an, ["grossprofit"]).fillna(rev - cost)
    an = an[["cik", "q", "ann", "ni", "cfo", "gp"]].merge(assets, on=["cik", "q"], how="left")
    an = an.merge(assets.assign(q=assets.q + 4).rename(columns={"A": "A_1"}), on=["cik", "q"], how="left")
    an["AC"] = (an.ni - an.cfo) / an[["A", "A_1"]].mean(axis=1)
    an["PROF"] = an.gp / an.A
    return {"ins": (t_ins, ["AG", "NOA", "DPI2A"]), "qn": (qn, ["ROA"]), "sh": (sh, ["NI"]),
            "an": (an, ["AC", "PROF"])}


def asof(tables, t, max_age_q=6):
    """Latest announced value of every feature for every cik, as known at t."""
    tq = pd.Period(t, "Q")
    parts = []
    for tab, feats in tables.values():
        av = tab[(tab.ann <= t) & (tab.q <= tq) & (tab.q > tq - max_age_q)]
        for f in feats:
            x = av.dropna(subset=[f]).sort_values("q").groupby("cik").tail(1)
            parts.append(x.set_index("cik")[f])
    return pd.concat(parts, axis=1)


def stats(r, ppy=12):
    r = r.dropna()
    t = sm.OLS(r.values, np.ones(len(r))).fit(cov_type="HAC", cov_kwds={"maxlags": 3}).tvalues[0]
    eq = (1 + r).cumprod()
    return {"media_%mes": 100 * r.mean(), "t": t, "sharpe": r.mean() / r.std() * np.sqrt(ppy),
            "vol_%": 100 * r.std() * np.sqrt(ppy), "max_dd_%": 100 * (eq / eq.cummax() - 1).min(),
            "peor_mes_%": 100 * r.min(), "meses": len(r)}


def main():
    uni = universe().set_index("cik")
    sym = uni.symbol
    half_spread = (uni.set_index("symbol").avg_spread_bps / 2 / 1e4)
    sector = uni.set_index("symbol").sector
    px = pd.read_parquet(data.DATA / "prices_darwinex_universe.parquet")
    me = px.resample("ME").last()
    fwd = me.shift(-1) / me - 1
    mom = me.shift(1) / me.shift(12) - 1
    spy = fwd.pop("SPY")
    tables = feature_tables()

    months = me.index[(me.index >= "2012-01-31") & (me.index <= me.index[-2])]
    rows, books = [], {}
    prev = {}
    for t in months:
        f = asof(tables, t)
        f.index = f.index.map(sym)
        f = f[f.index.notna()]
        f["r12_2"] = mom.loc[t].reindex(f.index)
        f["fwd"] = fwd.loc[t].reindex(f.index)
        f = f.dropna(subset=["fwd"])
        pct = pd.DataFrame({k: (f[k] * s).rank(pct=True) for k, s in SIGN.items()})
        f["M"] = pct.mean(axis=1).where(pct.notna().sum(axis=1) >= 5)
        f = f.dropna(subset=["M"])
        f["sector"] = sector.reindex(f.index)
        rk = f.M.rank(ascending=False, method="first")
        q = np.ceil(f.M.rank(pct=True) * 5)
        ic = f.M.rank().corr(f.fwd.rank())
        top10 = f.loc[rk.sort_values().index[:10]]
        capped, cnt = [], {}
        for s_, row in f.sort_values("M", ascending=False).iterrows():
            if cnt.get(row.sector, 0) < 3:
                capped.append(s_)
                cnt[row.sector] = cnt.get(row.sector, 0) + 1
            if len(capped) == 10:
                break
        bot10 = f.loc[f.M.rank(ascending=True, method="first").sort_values().index[:10]]
        sets = {"top10": list(top10.index), "top10_sector3": capped, "bot10": list(bot10.index)}
        to = {}
        for k, v in sets.items():
            old = prev.get(k, [])
            new = [x for x in v if x not in old]
            to[k] = (len(new) / len(v), np.mean([half_spread.get(x, 0.0008) for x in new]) if new else 0.0)
        prev = sets
        rows.append({
            "date": t, "n": len(f), "ic": ic, "ew": f.fwd.mean(), "spy": spy.loc[t],
            "q5": f.fwd[q == 5].mean(), "q1": f.fwd[q == 1].mean(),
            "top10": f.fwd[sets["top10"]].mean(), "top10_sector3": f.fwd[capped].mean(),
            "bot10": f.fwd[sets["bot10"]].mean(),
            "mom_losers10": f.fwd[f.r12_2.rank(method="first") <= 10].mean(),
            **{f"to_{k}": v[0] for k, v in to.items()}, **{f"spr_{k}": v[1] for k, v in to.items()},
            "n_utilities_top10": (top10.sector == "Utilities").sum(),
        })
        books[t] = sets
    r = pd.DataFrame(rows).set_index("date")
    r.to_csv(OUT / "monthly.csv", float_format="%.5f")

    def cost(k):   # sell + buy of replaced names, both sides, at measured spreads + commission
        return 2 * r[f"to_{k}"] * (r[f"spr_{k}"] + COMM)

    strat = {
        "Q5 (20% más sobrevaloradas) vs mercado EW, bruto": r.ew - r.q5,
        "Q1 − Q5 (largo infravaloradas, corto sobrevaloradas), bruto": r.q1 - r.q5,
        "Top10 corto / SPY, neto Zero": r.spy - r.top10 - cost("top10") - DIV_WHT_SPY,
        "Top10 límite sectorial / SPY, neto Zero": r.spy - r.top10_sector3 - cost("top10_sector3") - DIV_WHT_SPY,
        "Top10 corto / Bot10 largo, neto Zero": r.bot10 - r.top10 - cost("top10") - cost("bot10"),
        "Top10 límite sectorial / SPY, neto Classic": r.spy - r.top10_sector3 - cost("top10_sector3")
        - DIV_WHT_SPY + FIN_CLASSIC,
        "Referencia: 10 perdedores momentum / SPY, bruto": r.spy - r.mom_losers10,
    }
    ff = factors()
    out = []
    for name, s in strat.items():
        for per, sl in (("2012-2026", slice(None)), ("2012-2016", slice("2012", "2016")),
                        ("2017-2021", slice("2017", "2021")), ("2022-2026", slice("2022", "2026"))):
            x = s.loc[sl]
            st = stats(x)
            st.update(estrategia=name, periodo=per)
            if per == "2012-2026":
                xx = x.copy()
                xx.index = xx.index.to_period("M") + 1   # holding month
                fx = ff.reindex(xx.index)[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]].dropna()
                res = sm.OLS(xx.reindex(fx.index), sm.add_constant(fx)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
                st.update(alfa_FF6_mes=100 * res.params["const"], t_alfa=res.tvalues["const"],
                          beta_MOM=res.params["MOM"], beta_RMW=res.params["RMW"], beta_CMA=res.params["CMA"])
            out.append(st)
    out = pd.DataFrame(out)
    first_cols = ["estrategia", "periodo"]
    out = out[first_cols + [c for c in out if c not in first_cols]]
    out.to_csv(OUT / "summary.csv", index=False, float_format="%.4f")
    pd.DataFrame(strat).to_csv(OUT / "strategy_returns.csv", float_format="%.5f")
    pd.set_option("display.width", 250)
    print(out.round(2).to_string(index=False))
    print("\nIC medio (Spearman M vs retorno siguiente; negativo = funciona):",
          round(r.ic.mean(), 4), "t:", round(r.ic.mean() / r.ic.std() * np.sqrt(len(r)), 2))
    print("Rotación media top10:", round(r.to_top10.mean(), 2), " utilities en top10 (media):",
          round(r.n_utilities_top10.mean(), 1), " acciones/mes:", int(r.n.mean()))


if __name__ == "__main__":
    main()
