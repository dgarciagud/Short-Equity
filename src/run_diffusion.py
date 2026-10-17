"""Fama-MacBeth tests of slow information diffusion.

Leader -> laggard (Hou 2007): sector-level cross-sections; next-period return of
the laggard (small) portfolio on the leaders' and laggards' own last-period return.
Customer -> supplier (Cohen-Frazzini 2008): supplier next-period return on its
customers' last-month return, controlling for own last return and sector return."""
import numpy as np
import pandas as pd

import backtest as bt
import data

OUT = data.ROOT / "results"


def fama_macbeth(df, y, xs, lags):
    coefs = []
    for d, g in df.dropna(subset=[y] + xs).groupby("date"):
        if len(g) < len(xs) + 3:
            continue
        X = np.column_stack([np.ones(len(g))] + [g[x].values for x in xs])
        b, *_ = np.linalg.lstsq(X, g[y].values, rcond=None)
        coefs.append(pd.Series(b, index=["const"] + xs, name=d))
    c = pd.DataFrame(coefs)
    return {x: (c[x].mean(), bt.nw_t(c[x], lags), len(c)) for x in xs}


def main():
    rows = []
    for ds, freq, win in [("yahoo", "M", "1-0m"), ("yahoo", "W", "4-1w"),
                          ("algoseek", "M", "1-0m"), ("algoseek", "W", "4-1w")]:
        lags = 3 if freq == "M" else 4
        df = pd.read_parquet(OUT / "panels" / f"{ds}_{freq}_{win}.parquet")
        lag = df[df.role == "laggard"].groupby(["date", "sector"]).agg(
            fwd=("fwd", "mean"), own=("last", "mean"), lead=("lead", "first")).reset_index()
        for x, (b, t, n) in fama_macbeth(lag, "fwd", ["lead", "own"], lags).items():
            rows.append(dict(dataset=ds, freq=freq, test="lider->rezagado (sector)",
                             variable=x, coef=b, t_NW=t, n_periodos=n))
        df["sec_last"] = df.groupby(["date", "sector"])["last"].transform("mean")
        sup = df[df.cust.notna()]
        for x, (b, t, n) in fama_macbeth(sup, "fwd", ["cust", "last", "sec_last"], lags).items():
            rows.append(dict(dataset=ds, freq=freq, test="cliente->proveedor (accion)",
                             variable=x, coef=b, t_NW=t, n_periodos=n))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "diffusion_tests.csv", index=False, float_format="%.4f")
    print(out.round(3).to_string())


if __name__ == "__main__":
    main()
