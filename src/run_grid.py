"""Run every short strategy x hedge x formation window x frequency x dataset.

Writes results/grid_stats.csv and the per-period returns to results/returns/."""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import backtest as bt
import data
from signals import MONTHLY_WINDOWS, WEEKLY_WINDOWS

OUT = data.ROOT / "results"
(OUT / "returns").mkdir(parents=True, exist_ok=True)
(OUT / "panels").mkdir(parents=True, exist_ok=True)
(OUT / "stats").mkdir(parents=True, exist_ok=True)
DATASETS = {"algoseek": data.load_algoseek, "yahoo": data.load_yahoo}


def one(job):
    ds, freq, win = job
    done = OUT / "stats" / f"{ds}_{freq}_{win}.csv"
    if done.exists():
        return pd.read_csv(done)
    L, skip = (MONTHLY_WINDOWS if freq == "M" else WEEKLY_WINDOWS)[win]
    ppy = 12 if freq == "M" else 52
    panel = OUT / "panels" / f"{ds}_{freq}_{win}.parquet"
    if panel.exists():
        df = pd.read_parquet(panel)
        rebal = pd.DatetimeIndex(sorted(df.date.unique()))
    else:
        df, rebal = bt.build_panel(DATASETS[ds](), freq, L, skip)
        df.to_parquet(panel)
    ff = bt.factor_periods(data.load_ff_daily(), rebal)
    crash = bt.mom_crash_dates(ff.reindex(sorted(df.date.unique())).dropna(), k=10)
    rows, rets = [], {}
    for name, fn in bt.SEL.items():
        pair_col = "rpret" if name in bt.RESIDUAL else "pret"
        for hedge in ("mkt", "sector", "pair"):
            r = bt.run_strategy(df, fn, hedge=hedge, pair_col=pair_col, ppy=ppy)
            g = bt.run_strategy(df, fn, hedge=hedge, pair_col=pair_col, ppy=ppy,
                                cost_bps=0.0, borrow=0.0)
            legs = [("ls", r.ls), ("ls_bruto", g.ls)]
            if hedge == "mkt":
                legs += [("short", r.short), ("short_bruto", g.short)]
            for leg, series in legs:
                st = bt.stats(series, ppy, ff, crash)
                st.update(dataset=ds, freq=freq, window=win, strategy=name, hedge=hedge,
                          leg=leg, n_medio=r.n[r.n > 0].mean(), turnover=r.turnover.mean())
                rows.append(st)
                rets[f"{name}|{hedge}|{leg}"] = series
    # sector-level momentum on EW sector baskets
    df["sec_fipsig"] = np.where(df.sec_pret < 0, df.sec_id, 1 + df.sec_pret)
    for col, label in [("sec_1m", "SECTOR mom 1 mes"), ("sec_pret", "SECTOR mom misma ventana"),
                       ("sec_fipsig", "SECTOR FIP (caida gradual)")]:
        r = bt.sector_strategy(df, col, ppy)
        for leg in ("ls", "short"):
            st = bt.stats(r[leg], ppy, ff, crash)
            st.update(dataset=ds, freq=freq, window=win, strategy=label, hedge="sectores",
                      leg=leg, n_medio=3, turnover=np.nan)
            rows.append(st)
            rets[f"{label}|sectores|{leg}"] = r[leg]
    pd.DataFrame(rets).to_parquet(OUT / "returns" / f"{ds}_{freq}_{win}.parquet")
    print("done", job, file=sys.stderr, flush=True)
    rows = pd.DataFrame(rows)
    rows.to_csv(done, index=False)
    return rows


if __name__ == "__main__":
    jobs = [(ds, f, w) for ds in DATASETS
            for f, ws in (("M", MONTHLY_WINDOWS), ("W", WEEKLY_WINDOWS)) for w in ws]
    with ProcessPoolExecutor(max_workers=4) as ex:
        res = list(ex.map(one, jobs))
    grid = pd.concat(res, ignore_index=True)
    first = ["dataset", "freq", "window", "strategy", "hedge", "leg"]
    grid = grid[first + [c for c in grid.columns if c not in first]]
    grid.to_csv(OUT / "grid_stats.csv", index=False, float_format="%.5f")
    print(grid.shape)
