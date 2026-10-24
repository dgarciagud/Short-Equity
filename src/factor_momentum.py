"""Factor momentum (Gupta and Kelly, 2019, "Factor Momentum Everywhere") on JKP factors.

Input: the 153 official JKP factors inside the mega-cap and large-cap groups, signed in their
expected direction (jkp_download.py, cluster_labels.csv). Monthly, information known at t-1.
Weights over factors (Sum |w| = 1 each month, so returns are per unit of gross factor exposure):
  estatico        1/sigma_i                         (static, risk-balanced combination)
  TSFM 12m        sign(r_i, t-12..t-1) / sigma_i    (time-series factor momentum, GK main spec)
  TSFM 1m         sign(r_i, t-1) / sigma_i
  solo ganadores  1{r_i, t-12..t-1 > 0} / sigma_i   (drop the losers, never short a factor)
  XSFM 12m        +1/sigma_i above the cross-factor median past return, -1/sigma_i below
sigma_i = std of the factor's past 36 months (min 24). Also at the theme level (13 themes).
"""
import numpy as np
import pandas as pd

import data
from kelly_jkp import JKP, NAMES

RES = data.ROOT / "results" / "kelly"
PERIODS = {"1967-1989": ("1967", "1989"), "1990-2006": ("1990", "2006"), "2007-2016": ("2007", "2016"),
           "2017-2025": ("2017", "2025"), "2012-2025": ("2012", "2025"), "1967-2025": ("1967", "2025")}


def schemes(R):
    """R: months x factors. Returns {name: monthly return series}."""
    sig = R.shift(1).rolling(36, min_periods=24).std()
    p12 = R.shift(1).rolling(12, min_periods=12).sum()
    p1 = R.shift(1)
    raw = {"estatico": 1 / sig,
           "TSFM 12m": np.sign(p12) / sig,
           "TSFM 1m": np.sign(p1) / sig,
           "solo ganadores 12m": (p12 > 0) / sig,
           "XSFM 12m": np.sign(p12.sub(p12.median(axis=1), axis=0)) / sig}
    out = {}
    for k, w in raw.items():
        w = w.where(sig.notna() & p12.notna())
        w = w.div(w.abs().sum(axis=1), axis=0)
        out[k] = (w * R).sum(axis=1, min_count=1)
    return pd.DataFrame(out)


def stats(s):
    s = s.dropna()
    return s.mean() / s.std() * np.sqrt(12), 100 * s.mean()


def main():
    f = pd.read_parquet(JKP / "factors_usa_size.parquet")
    lab = pd.read_csv(JKP / "cluster_labels.csv").set_index("characteristic")
    f["ret"] = f.ret * f.name.map(lab.direction)
    f["theme"] = f.name.map(lab.cluster)
    f["m"] = pd.to_datetime(f.date).dt.to_period("M")
    rows, series = [], {}
    for g in ("mega", "large"):
        x = f[f.size_grp == g]
        R = x.pivot_table(index="m", columns="name", values="ret").loc["1963":]
        T = x.groupby(["m", "theme"]).ret.mean().unstack().loc["1963":]
        for level, M in (("153 factores", R), ("13 temas", T)):
            sc = schemes(M)
            series[(g, level)] = sc
            for k in sc:
                for per, (a, b) in PERIODS.items():
                    sh, mu = stats(sc[k].loc[a:b])
                    rows.append({"grupo": g, "nivel": level, "esquema": k, "periodo": per, "sharpe": sh, "%/mes": mu})
    res = pd.DataFrame(rows)
    res.to_csv(RES / "fm_jkp_resumen.csv", index=False, float_format="%.4f")
    pd.concat({f"{g}|{lvl}": s for (g, lvl), s in series.items()}, axis=1).to_csv(RES / "fm_jkp_retornos.csv",
                                                                               float_format="%.6f")
    pd.set_option("display.width", 250)
    piv = res.pivot_table(index=["grupo", "nivel", "esquema"], columns="periodo", values="sharpe", sort=False)
    print(piv[list(PERIODS)].round(2).to_string())
    mu = res.pivot_table(index=["grupo", "nivel", "esquema"], columns="periodo", values="%/mes", sort=False)
    print(mu[list(PERIODS)].round(3).to_string())


if __name__ == "__main__":
    main()
