"""The SYY short strategy (pit_backtest.py, 8 anomalies, split-safe NI) with value weights.

Scores M and sectors from results/recent/pit/panel.parquet; market value ME from the richer
panel of kelly_sec2.py (restated shares x split-adjusted close). Portfolios formed at t, held t+1:
  Q5 vs mercado   most overpriced quintile minus the whole universe, both weighted the same way
  Top10 / SPY     10 most overpriced with max 3 per sector, net of Darwinex Zero costs
Weights: igual (as in REPORT 12.b), capitalización con tope (80th pct., JKP) and capitalización pura.
"""
import numpy as np
import pandas as pd

import data
import recent_backtest as rb
from darwinex_sim import COMM
from repo_xbrl import universe

OUT = data.ROOT / "results" / "kelly"


def main():
    pit = pd.read_parquet(data.ROOT / "results" / "recent" / "pit" / "panel.parquet")
    pit = pit.rename_axis("cik").reset_index()[["cik", "date", "M", "sector", "fwd"]]
    me = pd.read_parquet(OUT / "sec2_panel.parquet", columns=["cik", "date", "ME"])
    p = pit.merge(me, on=["cik", "date"], how="left")
    p = p[p.ME > 0].copy()
    spy = pd.read_csv(data.ROOT / "results" / "recent" / "pit" / "monthly.csv", index_col=0, parse_dates=True).spy
    uni = universe().drop_duplicates("cik")
    spr = (uni.set_index("cik").avg_spread_bps / 2 / 1e4).to_dict()
    schemes = {"igual": lambda g: pd.Series(1.0, index=g.index),
               "capitalización con tope": lambda g: g.ME.clip(upper=g.ME.quantile(0.8)),
               "capitalización pura": lambda g: g.ME}
    rows, series = [], {}
    for name, wf in schemes.items():
        q5, top, prev = {}, {}, pd.Series(dtype=float)
        for t, g in p.groupby("date"):
            w = wf(g)
            q = g.M.rank(pct=True) > 0.8
            mkt = (w * g.fwd).sum() / w.sum()
            q5[t] = mkt - (w[q] * g.fwd[q]).sum() / w[q].sum()
            picked, cnt = [], {}
            for i in g.M.sort_values(ascending=False).index:
                s = g.at[i, "sector"]
                if cnt.get(s, 0) < 3:
                    picked.append(i)
                    cnt[s] = cnt.get(s, 0) + 1
                if len(picked) == 10:
                    break
            ww = w[picked] / w[picked].sum()
            ww.index = g.loc[picked, "cik"].values
            turn = ww.sub(prev, fill_value=0).abs()
            cost = sum(turn[c] * (spr.get(c, 0.0008) + COMM) for c in turn.index)
            top[t] = (spy.loc[t] - (ww.values * g.loc[picked, "fwd"].values).sum() - cost - rb.DIV_WHT_SPY,
                      ww.max())
            prev = ww
        a = pd.Series(q5)
        b = pd.Series({k: v[0] for k, v in top.items()})
        mx = pd.Series({k: v[1] for k, v in top.items()})
        series[f"Q5|{name}"], series[f"Top10|{name}"] = a, b
        for lab, s in (("Quintil sobrevalorado vs mercado, bruto", a), ("10 cortos (máx. 3/sector) / SPY, neto Zero", b)):
            st = rb.stats(s)
            rows.append({"estrategia": lab, "ponderacion": name, "%/mes": st["media_%mes"], "t": st["t"],
                         "sharpe": st["sharpe"], "max_dd_%": st["max_dd_%"],
                         "2012-2016": 100 * s.loc[:"2016"].mean(), "2017-2021": 100 * s.loc["2017":"2021"].mean(),
                         "2022-2026": 100 * s.loc["2022":].mean(),
                         "peso_max_medio_%": 100 * mx.mean() if "10" in lab else np.nan})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "syy_vw_resumen.csv", index=False, float_format="%.4f")
    pd.DataFrame(series).to_csv(OUT / "syy_vw_retornos.csv", float_format="%.5f")
    pd.set_option("display.width", 220)
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
