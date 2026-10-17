"""The sector dilemma: (1) two risk-budgeted sleeves and (2) one book with sector
momentum as a meta-model feature (walk-forward, no look-ahead)."""
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

import backtest as bt
import data

OUT = data.ROOT / "results"
BASE_FEATS = ["pret", "id", "minret", "last", "vol", "rpret", "rid", "cust", "is_leader",
              "is_laggard"]
SECTOR_FEATS = ["sec_pret", "sec_id", "sec_1m", "lead"]


def vol_target(r, ppy, target, lookback):
    """Scale returns to an ex-ante vol target using trailing realised vol (lagged)."""
    sd = r.rolling(lookback, min_periods=lookback // 2).std().shift(1) * np.sqrt(ppy)
    return (r * (target / sd).clip(upper=3.0)).dropna()


def sleeves(rets, ppy, w_resid=0.75, target=0.10):
    """Residual short sleeve + small sector-momentum sleeve, each vol-targeted and
    combined with a fixed risk budget."""
    lb = 12 if ppy == 12 else 52
    sec = rets["SECTOR mom 1 mes|sectores|ls"]
    out = {"Sleeve sectorial (mom 1m L/S)": vol_target(sec, ppy, target, lb)}
    vb = vol_target(sec, ppy, target * (1 - w_resid), lb)
    for hedge, tag in (("sector", "neutral sector"), ("pair", "par Darwinex")):
        a = rets[f"RFIP (perdedor residual continuo)|{hedge}|ls"]
        out[f"Sleeve residual RFIP {tag}"] = vol_target(a, ppy, target, lb)
        va = vol_target(a, ppy, target * w_resid, lb)
        combo = pd.concat([va, vb], axis=1, sort=True).dropna().sum(axis=1)
        out[f"Dos sleeves 75/25 ({tag})"] = combo
    return out


def add_features(df):
    df = df.copy()
    df["is_leader"] = (df.role == "leader").astype(float)
    df["is_laggard"] = (df.role == "laggard").astype(float)
    g = df.groupby("date")
    for c in BASE_FEATS + SECTOR_FEATS:
        df["f_" + c] = g[c].rank(pct=True).fillna(0.5) - 0.5
    df["y"] = g.fwd.rank(pct=True) - 0.5
    return df


def walk_forward(df, feats, model, ppy):
    dates = np.sort(df.date.unique())
    first = 36 if ppy == 12 else 156
    step = 12 if ppy == 12 else 52
    cols = ["f_" + c for c in feats]
    preds = []
    for k in range(first, len(dates), step):
        tr = df[df.date < dates[k]]
        te = df[(df.date >= dates[k]) & (df.date < dates[min(k + step, len(dates) - 1)])]
        if k + step >= len(dates):
            te = df[df.date >= dates[k]]
        if model == "ridge":
            m = Ridge(alpha=1.0).fit(tr[cols], tr.y)
        else:
            m = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=15,
                                  min_child_samples=200, subsample=0.8, subsample_freq=1,
                                  colsample_bytree=0.8, verbose=-1, random_state=0)
            m.fit(tr[cols], tr.y)
        preds.append(pd.Series(m.predict(te[cols]), index=te.index))
    out = df.loc[pd.concat(preds).index].copy()
    out["pred"] = pd.concat(preds)
    out["q_pred"] = out.groupby("date").pred.transform(lambda x: bt._q(x, 5))
    return out


def main(ds, freq, win):
    ppy = 12 if freq == "M" else 52
    df = pd.read_parquet(OUT / "panels" / f"{ds}_{freq}_{win}.parquet")
    rets = pd.read_parquet(OUT / "returns" / f"{ds}_{freq}_{win}.parquet")
    ff = bt.factor_periods(data.load_ff_daily(), pd.DatetimeIndex(sorted(df.date.unique())))
    crash = bt.mom_crash_dates(ff.dropna(), k=10)
    rows, series = [], {}

    def record(name, r):
        st = bt.stats(r, ppy, ff, crash)
        st.update(dataset=ds, freq=freq, window=win, strategy=name)
        rows.append(st)
        series[name] = r

    for name, r in sleeves(rets, ppy).items():
        record(name, r)
    df = add_features(df.dropna(subset=["rpret"]))
    for model in ("ridge", "lgbm"):
        for tag, feats in (("con sector", BASE_FEATS + SECTOR_FEATS), ("sin sector", BASE_FEATS)):
            p = walk_forward(df, feats, model, ppy)
            short = lambda d: d.q_pred == 1
            for hedge in ("mkt", "pair"):
                r = bt.run_strategy(p, short, hedge=hedge, pair_col="pred", ppy=ppy)
                record(f"Meta-modelo {model} {tag} | {hedge}", r.ls)
    # hard-filter benchmarks over the same out-of-sample span
    start = min(s.index.min() for k, s in series.items() if k.startswith("Meta"))
    for k in ["FIP (perdedor continuo, ID bajo)|mkt|ls", "FIP + sector perdedor (1 mes)|mkt|ls",
              "RFIP (perdedor residual continuo)|sector|ls"]:
        record("Filtro duro: " + k, rets[k][rets.index >= start])
    pd.DataFrame(series).to_parquet(OUT / "returns" / f"combo_{ds}_{freq}_{win}.parquet")
    print("done", ds, freq, win, file=sys.stderr, flush=True)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    jobs = [("yahoo", "M", "12-1m"), ("yahoo", "M", "1-0m"), ("yahoo", "M", "6-1m"),
            ("yahoo", "W", "13-1w"), ("yahoo", "W", "4-1w"), ("yahoo", "W", "52-1w"),
            ("algoseek", "W", "13-1w"), ("algoseek", "W", "4-1w")]
    res = pd.concat([main(*j) for j in jobs], ignore_index=True)
    first = ["dataset", "freq", "window", "strategy"]
    res = res[first + [c for c in res.columns if c not in first]]
    res.to_csv(OUT / "combo_stats.csv", index=False, float_format="%.5f")
    print(res.shape)
