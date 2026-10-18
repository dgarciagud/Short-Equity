"""SYY mispricing short strategy, 2012-2026, on the POINT-IN-TIME S&P 500 (no survivorship bias).

Same signal, portfolios and costs as recent_backtest.py (companyfacts as-filed fundamentals),
but at every month-end t the universe is the index membership AT t, not today's members.

  membership   fja05680/sp500 "S&P 500 Historical Components & Changes", sampled at month-ends
               into data/sp500_membership_monthly.csv
  ticker->CIK  data/sp500_hist_cik.json (SEC tickers + name match + manual fixes for renames)
  prices       ml4t-data Yahoo provider (pit_prices.py) for every historical member;
               AlgoSeek PIT daily bars (ML4T repo) fill 2017-2021 names Yahoo no longer has.
               Returns are combined per CIK, so renames (FB->META, BK->BNY) keep one history.
  delistings   the holding-month return runs to the last traded price (takeover premium or
               collapse included when the source has it).
Two universes run through the identical pipeline:
  pit        index members at t
  survivor   today's Darwinex S&P 500 CFDs at every t (the biased universe of section 12)
Members with no price history are reported as coverage gaps (mostly 2012-2016 acquisitions).
"""
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

import data
import recent_backtest as rb
from cpz_mispricing import factors
from live_syy import SEC
from repo_xbrl import universe

OUT = data.ROOT / "results" / "recent"
HIST = data.DATA / "sp500_membership_monthly.csv"   # month-end lists from fja05680/sp500 (2010-12..2026-10)
RECYCLED = {"Q", "S", "SE", "STI", "MI", "POM", "EP", "CPWR", "BEAM", "MMI", "SUN"}   # Yahoo = new issuer


def sic_sector(sic):
    """Coarse GICS sector from an SEC SIC code (only for names missing from the GICS lists)."""
    try:
        s = int(sic)
    except (TypeError, ValueError):
        return "Unknown"
    rules = [((6324, 6325), "Health Care"), ((6500, 6600), "Real Estate"), ((6798, 6799), "Real Estate"),
             ((6000, 6800), "Financials"), ((4900, 5000), "Utilities"), ((1300, 1400), "Energy"),
             ((2900, 3000), "Energy"), ((2830, 2840), "Health Care"), ((3840, 3860), "Health Care"),
             ((8000, 8100), "Health Care"), ((3570, 3580), "Information Technology"),
             ((3600, 3700), "Information Technology"), ((7370, 7380), "Information Technology"),
             ((3820, 3830), "Information Technology"), ((4800, 4900), "Communication Services"),
             ((2710, 2790), "Communication Services"), ((7810, 7820), "Communication Services"),
             ((2000, 2200), "Consumer Staples"), ((5400, 5500), "Consumer Staples"),
             ((2840, 2845), "Consumer Staples"), ((5140, 5150), "Consumer Staples"),
             ((5000, 6000), "Consumer Discretionary"), ((2300, 2400), "Consumer Discretionary"),
             ((3700, 3720), "Consumer Discretionary"), ((7000, 7100), "Consumer Discretionary"),
             ((1000, 1500), "Materials"), ((2600, 2700), "Materials"), ((2800, 2900), "Materials"),
             ((3200, 3400), "Materials")]
    for (lo, hi), name in rules:
        if lo <= s < hi:
            return name
    return "Industrials"


def membership():
    h = pd.read_csv(HIST)
    h["date"] = pd.to_datetime(h.date)
    return h.sort_values("date").set_index("date").tickers.str.split(",")


def monthly_returns(cik_of):
    """Monthly total returns per CIK: Yahoo first, AlgoSeek where Yahoo has nothing."""
    px = pd.read_parquet(data.DATA / "prices_sp500_pit.parquet")
    me = px.resample("ME").last()
    yret = me.pct_change(fill_method=None)
    spy = yret.pop("SPY")
    a = pd.read_parquet(data.ALGOSEEK, columns=["date", "symbol", "close", "adj_factor"])
    a["date"] = pd.to_datetime(a.date)
    a["tr"] = a.close * a.adj_factor
    ame = a.pivot(index="date", columns="symbol", values="tr").resample("ME").last()
    aret = ame.pct_change(fill_method=None).reindex(yret.index)
    out = {}
    for src, ret in (("yahoo", yret), ("algoseek", aret)):
        cols = [c for c in ret if c in cik_of and not (src == "yahoo" and c in RECYCLED)]
        cols.sort(key=lambda c: -ret[c].notna().sum())        # longest history first
        for c in cols:
            k = cik_of[c]
            out[k] = ret[c] if k not in out else out[k].fillna(ret[c])
    return pd.DataFrame(out), spy


def run(name, members_at, ret, spy, tables, half_spread, sector):
    fwd = ret.shift(-1)
    mom = np.expm1(np.log1p(ret).shift(1).rolling(11, min_periods=11).sum())
    months = ret.index[(ret.index >= "2012-01-31") & (ret.index <= ret.index[-2])]
    rows, panel, prev = [], [], {}
    for t in months:
        mem = members_at(t)
        f = rb.asof(tables, t).replace([np.inf, -np.inf], np.nan)
        f = f[f.index.isin(mem)]
        f["r12_2"] = mom.loc[t].reindex(f.index)
        f["fwd"] = fwd.loc[t].reindex(f.index)
        n_px = fwd.loc[t].reindex(list(mem)).notna().sum()
        f = f.dropna(subset=["fwd"])
        pct = pd.DataFrame({k: (f[k] * s).rank(pct=True) for k, s in rb.SIGN.items()})
        f["M"] = pct.mean(axis=1).where(pct.notna().sum(axis=1) >= 5)
        f = f.dropna(subset=["M"])
        f["sector"] = sector.reindex(f.index).fillna("Unknown")
        panel.append(f.assign(date=t))
        rk = f.M.rank(ascending=False, method="first")
        q = np.ceil(f.M.rank(pct=True) * 5)
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
            new = [x for x in v if x not in prev.get(k, [])]
            to[k] = (len(new) / len(v), np.mean([half_spread.get(x, 0.0008) for x in new]) if new else 0.0)
        prev = sets
        rows.append({
            "date": t, "miembros": len(mem), "con_precio": n_px, "n": len(f),
            "ic": f.M.rank().corr(f.fwd.rank()), "ew": f.fwd.mean(), "spy": spy.loc[t + pd.offsets.MonthEnd(1)],
            "q5": f.fwd[q == 5].mean(), "q1": f.fwd[q == 1].mean(),
            "top10": f.fwd[sets["top10"]].mean(), "top10_sector3": f.fwd[capped].mean(),
            "bot10": f.fwd[sets["bot10"]].mean(),
            "mom_losers10": f.fwd[f.r12_2.rank(method="first") <= 10].mean(),
            "top10_ya_no_miembro_hoy": np.mean([x not in sur_ciks for x in sets["top10"]]),
            **{f"to_{k}": v[0] for k, v in to.items()}, **{f"spr_{k}": v[1] for k, v in to.items()},
        })
    r = pd.DataFrame(rows).set_index("date")
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    r.to_csv(out / "monthly.csv", float_format="%.5f")
    pan = pd.concat(panel)
    pan.to_parquet(out / "panel.parquet")

    ics = []
    for k, sgn in list(rb.SIGN.items()) + [("M", 1)]:
        ic = pan.groupby("date").apply(lambda g: (g[k] * sgn).rank().corr(g.fwd.rank()))
        q5 = pan.groupby("date").apply(lambda g: g.fwd[(g[k] * sgn).rank(pct=True) > 0.8].mean() - g.fwd.mean())
        ics.append({"anomalia": k, "IC_medio": ic.mean(), "t_IC": ic.mean() / ic.std() * np.sqrt(ic.count()),
                    "Q5_menos_EW_%mes": 100 * q5.mean(), "t_Q5": q5.mean() / q5.std() * np.sqrt(q5.count())})
    pd.DataFrame(ics).to_csv(out / "anomalias.csv", index=False, float_format="%.4f")

    def cost(k):
        return 2 * r[f"to_{k}"] * (r[f"spr_{k}"] + rb.COMM)

    strat = {
        "Q5 vs mercado EW, bruto": r.ew - r.q5,
        "Q1 − Q5, bruto": r.q1 - r.q5,
        "Top10 corto / SPY, neto Zero": r.spy - r.top10 - cost("top10") - rb.DIV_WHT_SPY,
        "Top10 límite sectorial / SPY, neto Zero": r.spy - r.top10_sector3 - cost("top10_sector3") - rb.DIV_WHT_SPY,
        "Top10 corto / Bot10 largo, neto Zero": r.bot10 - r.top10 - cost("top10") - cost("bot10"),
        "Top10 límite sectorial / SPY, neto Classic": r.spy - r.top10_sector3 - cost("top10_sector3")
        - rb.DIV_WHT_SPY + rb.FIN_CLASSIC,
        "Referencia: 10 perdedores momentum / SPY, bruto": r.spy - r.mom_losers10,
    }
    ff = factors()
    res = []
    for sname, s in strat.items():
        for per, sl in (("2012-2026", slice(None)), ("2012-2016", slice("2012", "2016")),
                        ("2017-2021", slice("2017", "2021")), ("2022-2026", slice("2022", "2026"))):
            x = s.loc[sl]
            st = rb.stats(x)
            st.update(universo=name, estrategia=sname, periodo=per)
            xx = x.copy()
            xx.index = xx.index.to_period("M") + 1
            fx = ff.reindex(xx.index)[["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]].dropna()
            if len(fx) > 24:
                o = sm.OLS(xx.reindex(fx.index), sm.add_constant(fx)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
                st.update(alfa_FF6_mes=100 * o.params["const"], t_alfa=o.tvalues["const"])
            res.append(st)
    res = pd.DataFrame(res)
    res.to_csv(out / "summary.csv", index=False, float_format="%.4f")
    pd.DataFrame(strat).to_csv(out / "strategy_returns.csv", float_format="%.5f")
    return r, res


def main():
    global sur_ciks
    hist = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    uni = universe().drop_duplicates("cik")
    cik_of = {**hist, **dict(zip(uni.symbol, uni.cik))}
    sur_ciks = set(uni.cik)

    files = []
    for cik in set(cik_of.values()):
        tic = next((t for t, c in sorted(cik_of.items()) if c == cik and (SEC / "facts" / f"{t}.parquet").exists()),
                   None)
        if tic:
            files.append((tic, cik))
    rb.CF_UNIVERSE = files
    tables = rb.feature_tables("companyfacts")
    print(f"companyfacts: {len(files)} CIKs")

    ret, spy = monthly_returns(cik_of)
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()
    sic = {int(k): v for k, v in json.loads((SEC / "sic.json").read_text()).items()}
    gics = data.sector_labels()
    sector = {}
    for t, c in cik_of.items():
        if t in gics.index and c not in sector:
            sector[c] = gics[t]
    for c in set(cik_of.values()) - set(sector):
        sector[c] = sic_sector(sic.get(c, [None])[0])
    sector = pd.Series(sector)

    mem = membership()

    def pit(t):
        lst = mem[mem.index <= t].iloc[-1]
        return {cik_of[x] for x in lst if x in cik_of}

    out = {}
    for name, fn in (("pit", pit), ("survivor_mismo_pipeline", lambda t: sur_ciks)):
        r, res = run(name, fn, ret, spy, tables, spr, sector)
        out[name] = (r, res)
        print(f"\n== {name}: miembros {r.miembros.mean():.0f}, con precio {r.con_precio.mean():.0f}, "
              f"con M {r.n.mean():.0f}; top10 hoy fuera del índice {100 * r.top10_ya_no_miembro_hoy.mean():.0f}%")
    both = pd.concat([v[1] for v in out.values()])
    both.to_csv(OUT / "pit_vs_survivor.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    cols = ["universo", "estrategia", "periodo", "media_%mes", "t", "sharpe", "max_dd_%", "alfa_FF6_mes", "t_alfa"]
    print(both[cols].round(2).to_string(index=False))
    cov = out["pit"][0][["miembros", "con_precio", "n"]].resample("YE").mean().round(0)
    cov.to_csv(OUT / "pit" / "cobertura.csv")
    print(cov.to_string())


if __name__ == "__main__":
    main()
