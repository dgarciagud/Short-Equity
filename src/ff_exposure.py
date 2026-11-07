"""Fama-French 5 factors + momentum exposures of the live book and of the backtest.

Factors: Kenneth French daily/monthly files (ml4t-data cache in data/ff, refreshed from the
Tuck site when newer files are passed as arguments: python ff_exposure.py <ff5_daily.csv> <mom_daily.csv>).
Live book (data/live/holdings.csv, latest closes): each position's daily excess return is regressed
on Mkt-RF, SMB, HML, RMW, CMA, MOM over the last 252 sessions with factor data; the book's
exposure is the value-weighted sum (shorts negative), per unit of short value and in USD per 1 %
factor move. Backtest: monthly regression of the SPY-hedged 10-short book (pit_backtest.py rule).
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yfinance as yf

import data

FAC = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "MOM"]


def french_csv(path):
    rows = []
    for line in open(path):
        p = [x.strip() for x in line.split(",")]
        if len(p) > 1 and p[0].isdigit() and len(p[0]) == 8:
            rows.append(p)
    return rows


def daily_factors():
    if len(sys.argv) > 2:
        f5 = pd.DataFrame(french_csv(sys.argv[1]), columns=["d", "Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"])
        mo = pd.DataFrame(french_csv(sys.argv[2]), columns=["d", "MOM"])
        f = f5.merge(mo, on="d")
        f.index = pd.to_datetime(f.pop("d"))
        return f.astype(float) / 100
    f5 = pd.read_parquet(data.DATA / "ff" / "ff5_daily.parquet").set_index("timestamp")
    mo = pd.read_parquet(data.DATA / "ff" / "mom_daily.parquet").set_index("timestamp")
    return f5.join(mo, how="inner")


def main():
    F = daily_factors()
    h = pd.read_csv(data.DATA / "live" / "holdings.csv")
    book = h.groupby("ticker").shares.sum()
    px = yf.download(list(book.index), start=(F.index[-1] - pd.Timedelta(days=400)).strftime("%Y-%m-%d"),
                     auto_adjust=True, progress=False)["Close"]
    last = px.ffill().iloc[-1]
    r = px.pct_change(fill_method=None).reindex(F.index).iloc[-252:]
    Fw = F.loc[r.index]
    betas = {}
    for t in book.index:
        y = (r[t] - Fw.RF).dropna()
        o = sm.OLS(y, sm.add_constant(Fw.loc[y.index, FAC])).fit()
        betas[t] = o.params[FAC].to_dict() | {"R2": o.rsquared}
    B = pd.DataFrame(betas).T
    val = pd.Series({t: book[t] * last[t] * (1 if t == "SPY" else -1) for t in book.index})
    short = -val[val < 0].sum()
    expo = (B[FAC].mul(val, axis=0)).sum()
    out = pd.DataFrame({"beta_por_unidad_de_corto": expo / short, "USD_por_1%_del_factor": expo / 100})
    shorts_only = (B[FAC].mul(val.where(val < 0, 0), axis=0)).sum() / short

    # backtest (monthly)
    s = pd.read_csv(data.ROOT / "results" / "recent" / "pit" / "strategy_returns.csv", index_col=0, parse_dates=True)
    s = s["Top10 límite sectorial / SPY, neto Zero"]
    s.index = s.index.to_period("M") + 1
    from cpz_mispricing import factors
    ff = factors().reindex(s.index)[FAC].dropna()
    o = sm.OLS(s.reindex(ff.index), sm.add_constant(ff)).fit(cov_type="HAC", cov_kwds={"maxlags": 3})

    pd.set_option("display.width", 200)
    print(f"Datos de factores hasta {F.index[-1].date()}; precios hasta {px.index[-1].date()}")
    print("\n== Betas por valor (último año, diario)\n", B.round(2).to_string())
    print("\n== Solo los 10 cortos (por unidad de corto)\n", shorts_only.round(2).to_string())
    print("\n== Cartera completa (cortos + SPY)\n", out.round(3).to_string())
    print("\n== Backtest 2012-2026, mensual: cargas FF5+MOM (t)\n",
          pd.DataFrame({"carga": o.params, "t": o.tvalues}).round(2).to_string(), "\nR2", round(o.rsquared, 2))


if __name__ == "__main__":
    main()
