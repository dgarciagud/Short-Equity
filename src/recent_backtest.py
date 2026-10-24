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

SOURCE = sys.argv[1] if len(sys.argv) > 1 else "frames"          # frames | companyfacts
OUT = data.ROOT / "results" / "recent" / SOURCE
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


CF_COLS = {"assets": "assets", "liabilities": "liabilities",
           "liab_equity": "liabilitiesandstockholdersequity", "equity": "stockholdersequity",
           "cash": "cashandcashequivalentsatcarryingvalue", "st_invest": "shortterminvestments",
           "lt_debt": "longtermdebtnoncurrent", "st_debt": "debtcurrent",
           "ppe": "propertyplantandequipmentnet", "inventory": "inventorynet",
           "net_income": "netincomeloss", "cfo": "netcashprovidedbyusedinoperatingactivities",
           "gross_profit": "grossprofit", "revenue": "revenues", "cogs": "costofrevenue",
           "shares": "weightedaveragenumberofdilutedsharesoutstanding",
           "cur_assets": "assetscurrent", "cur_liab": "liabilitiescurrent", "public_float": "public_float"}
CF_PANELS = {"instant": (None, ["assets", "liabilities", "liab_equity", "equity", "cash", "st_invest",
                                "lt_debt", "st_debt", "ppe", "inventory", "cur_assets", "cur_liab"]),
             "float": (None, ["public_float"]),
             "quarterly": ((80, 100), ["net_income"]), "shares": ((80, 100), ["shares"]),
             "annual": ((350, 380), ["net_income", "cfo", "gross_profit", "revenue", "cogs"])}
_CF = {}
SPLIT_SAFE_NI = True   # NI from same-filing comparatives (False reproduces the split-contaminated version)
EXTRA = False          # also build O-score / CHS inputs (pit_backtest.py)
CF_UNIVERSE = None   # [(ticker of the cached facts file, cik)]; default: today's Darwinex universe


def load_cf(name):
    """Same schema as the Frames panels, from SEC companyfacts keeping each period's ORIGINAL
    as-filed value dated by its own filing (live_syy.download cache, data/sec/facts)."""
    if "facts" not in _CF:
        from live_syy import SEC
        if CF_UNIVERSE is None:
            uni = universe()
            files = zip(uni.symbol, uni.cik)
        else:
            files = CF_UNIVERSE
        parts = []
        for tic, cik in files:
            f = SEC / "facts" / f"{tic}.parquet"
            if f.exists():
                parts.append(pd.read_parquet(f).assign(cik=cik))
        x = pd.concat(parts)
        x["val"] = pd.to_numeric(x.val, errors="coerce").astype(float)
        x["end"] = pd.to_datetime(x.end)
        x["start"] = pd.to_datetime(x.start)
        x["filed"] = pd.to_datetime(x.filed)
        x["days"] = (x.end - x.start).dt.days
        _CF["raw"] = x
        x = x.sort_values(["filed", "prio"]).drop_duplicates(["cik", "key", "start", "end"], keep="first")
        _CF["facts"] = x
    x = _CF["facts"]
    span, keys = CF_PANELS[name]
    x = x[x.key.isin(keys)]
    x = x[x.start.isna()] if span is None else x[(x.days >= span[0]) & (x.days <= span[1])]
    x = x.sort_values(["prio", "filed"]).drop_duplicates(["cik", "key", "end"], keep="first")
    wide = x.pivot_table(index=["cik", "end"], columns="key", values="val", aggfunc="first")
    ann = x.groupby(["cik", "end"]).filed.max()
    wide = wide.rename(columns=CF_COLS).join(ann.rename("announcement_date")).reset_index()
    return wide.rename(columns={"end": "fiscal_quarter_end"})


def share_growth_cf():
    """Diluted-share growth vs the same quarter a year earlier, both taken from the SAME filing
    (the prior-year comparative is restated for splits, so a split is not read as issuance)."""
    load_cf("shares")
    x = _CF["raw"]
    x = x[(x.key == "shares") & (x.days >= 80) & (x.days <= 100)]
    cur = x.sort_values(["filed", "prio"]).drop_duplicates(["cik", "end"], keep="first")
    m = cur.merge(x[["cik", "filed", "end", "val"]], on=["cik", "filed"], suffixes=("", "_1"))
    gap = (m.end - m.end_1).dt.days
    m = m[(gap >= 355) & (gap <= 375)].drop_duplicates(["cik", "end"])
    m["NI"] = np.log(m.val / m.val_1).where((m.val > 0) & (m.val_1 > 0))
    m["ann"] = m.filed
    m["q"] = (m.end - pd.Timedelta(days=45)).dt.to_period("Q")
    return m.sort_values("end").drop_duplicates(["cik", "q"], keep="last")[["cik", "q", "ann", "NI"]]


def load(name, base=FRAMES):
    df = load_cf(name) if base == "companyfacts" else pd.read_parquet(base / f"{name}.parquet")
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
    ins["BE"] = eq
    ins["CA"] = first(ins, ["assetscurrent"])
    ins["CL"] = first(ins, ["liabilitiescurrent"])
    bs = ins[["cik", "q", "ann", "A", "L", "cash", "debt", "ppe", "inv", "BE", "CA", "CL"]]
    t_ins = lagged(bs, ["A", "ppe", "inv"], 4, "_1")
    t_ins["AG"] = t_ins.A / t_ins.A_1 - 1
    t_ins["NOA"] = ((t_ins.A - t_ins.cash) - (t_ins.L - t_ins.debt)) / t_ins.A_1
    t_ins["DPI2A"] = ((t_ins.ppe - t_ins.ppe_1) + (t_ins.inv - t_ins.inv_1).fillna(0)) / t_ins.A_1
    assets = bs[["cik", "q", "A"]]

    qn = load("quarterly", base)
    qn["ni"] = first(qn, ["netincomeloss", "profitloss"])
    qn = qn[["cik", "q", "ann", "ni"]].merge(assets.assign(q=assets.q + 1), on=["cik", "q"], how="left")
    qn["ROA"] = qn.ni / qn.A

    if base == "companyfacts" and SPLIT_SAFE_NI:
        sh = share_growth_cf()
    else:
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
    an["rev"] = rev
    an = an[["cik", "q", "ann", "ni", "cfo", "gp", "rev"]].merge(assets, on=["cik", "q"], how="left")
    an = an.merge(assets.assign(q=assets.q + 4).rename(columns={"A": "A_1"}), on=["cik", "q"], how="left")
    an["AC"] = (an.ni - an.cfo) / an[["A", "A_1"]].mean(axis=1)
    an["PROF"] = an.gp / an.A
    tables = {"ins": (t_ins, ["AG", "NOA", "DPI2A"]), "qn": (qn, ["ROA"]), "sh": (sh, ["NI"]),
              "an": (an, ["AC", "PROF"])}
    if EXTRA:
        tables.update(distress_inputs(bs, qn, an))
    return tables


def distress_inputs(bs, qn, an):
    """Ohlson (1980) O-score and the accounting inputs of the Campbell-Hilscher-Szilagyi (2008)
    failure probability (its market inputs are added in pit_backtest.py)."""
    o = an[["cik", "q", "ann", "ni", "cfo"]].merge(bs[["cik", "q", "ann", "A", "L", "CA", "CL"]],
                                                   on=["cik", "q"], how="left", suffixes=("", "_bs"))
    o["ann"] = o[["ann", "ann_bs"]].max(axis=1)
    o = lagged(o, ["ni"], 4, "_1")
    A = o.A.where(o.A > 0)
    chin = (o.ni - o.ni_1) / (o.ni.abs() + o.ni_1.abs())
    o["OSC"] = (-0.407 * np.log(A) + 6.03 * o.L / A - 1.43 * (o.CA - o.CL) / A + 0.0757 * o.CL / o.CA
                - 2.37 * o.ni / A - 1.83 * o.cfo / o.L.where(o.L > 0)
                + 0.285 * ((o.ni < 0) & (o.ni_1 < 0)) - 1.72 * (o.L > o.A) - 0.521 * chin)
    # quarterly NI with the fiscal Q4 (rarely tagged as a 3-month fact) = annual - Q1..Q3
    q = qn[["cik", "q", "ann", "ni"]].copy()
    yr = an[["cik", "q", "ann", "ni"]].rename(columns={"ni": "ni_y", "ann": "ann_y"})
    prior = q[["cik", "q", "ni"]]
    tri = yr.copy()
    for k in (1, 2, 3):
        tri = tri.merge(prior.assign(q=prior.q + k).rename(columns={"ni": f"p{k}"}), on=["cik", "q"], how="left")
    tri["ni"] = tri.ni_y - tri[["p1", "p2", "p3"]].sum(axis=1, min_count=3)
    q4 = tri.dropna(subset=["ni"])[["cik", "q", "ann_y", "ni"]].rename(columns={"ann_y": "ann"})
    q = pd.concat([q, q4[~q4.set_index(["cik", "q"]).index.isin(q.set_index(["cik", "q"]).index)]])
    q = q.sort_values("q").drop_duplicates(["cik", "q"], keep="last")
    q = lagged(lagged(lagged(q, ["ni"], 1, "_1"), ["ni"], 2, "_2"), ["ni"], 3, "_3")
    # CHS weights: quarter lags decay by phi^3 = 1/2
    q["NIW"] = (1 - 0.5) / (1 - 0.5 ** 4) * (q.ni + 0.5 * q.ni_1 + 0.25 * q.ni_2 + 0.125 * q.ni_3)
    b = bs[["cik", "q", "ann", "L", "cash", "BE"]]
    return {"osc": (o, ["OSC"]), "niw": (q, ["NIW"]), "bal": (b, ["L", "cash", "BE"])}


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
    OUT.mkdir(parents=True, exist_ok=True)
    uni = universe().drop_duplicates("cik").set_index("cik")
    sym = uni.symbol
    half_spread = (uni.set_index("symbol").avg_spread_bps / 2 / 1e4)
    sector = uni.set_index("symbol").sector
    px = pd.read_parquet(data.DATA / "prices_darwinex_universe.parquet")
    me = px.resample("ME").last()
    fwd = me.shift(-1) / me - 1
    mom = me.shift(1) / me.shift(12) - 1
    spy = fwd.pop("SPY")
    tables = feature_tables(FRAMES if SOURCE == "frames" else "companyfacts")

    months = me.index[(me.index >= "2012-01-31") & (me.index <= me.index[-2])]
    rows, books, panel = [], {}, []
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
        panel.append(f.assign(date=t))
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
    pan = pd.concat(panel)
    pan.to_parquet(OUT / "panel.parquet")
    ics = []
    for k, sgn in list(SIGN.items()) + [("M", 1)]:
        ic = pan.groupby("date").apply(lambda g: (g[k] * (sgn if k != "M" else 1)).rank().corr(g.fwd.rank()))
        q = pan.groupby("date").apply(lambda g: g.fwd[(g[k] * (sgn if k != "M" else 1)).rank(pct=True) > 0.8].mean()
                                      - g.fwd.mean())
        ics.append({"anomalia": k, "IC_medio": ic.mean(), "t_IC": ic.mean() / ic.std() * np.sqrt(ic.count()),
                    "Q5_menos_EW_%mes": 100 * q.mean(), "t_Q5": q.mean() / q.std() * np.sqrt(q.count()),
                    "Q5_2022_2026_%mes": 100 * q.loc["2022":].mean(), "cobertura": pan[k].notna().mean()})
    ics = pd.DataFrame(ics)
    ics.to_csv(OUT / "anomalias.csv", index=False, float_format="%.4f")
    print(ics.round(3).to_string(index=False))

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
