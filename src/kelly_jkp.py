"""Our 13-theme reconstruction vs the official Jensen-Kelly-Pedersen factors (jkpfactors.com).

Official series (jkp_download.py):
  JKP todas      13 US themes, all stocks, capped value weights (the headline JKP series)
  JKP mega       themes rebuilt from the 153 factors inside the mega-cap group (> NYSE 80th pct.)
  JKP large      same inside the large-cap group (NYSE 50th-80th pct.)
Ours: CRSP/CPZ top 500 (kelly_cpz.py, 1967-2016) and SEC point-in-time S&P 500 (kelly_sec.py,
2012-2026), equal-weighted quintile spreads. All gross of costs.
"""
import numpy as np
import pandas as pd

import data
from pit_figures import C, INK, MUTED

RES = data.ROOT / "results" / "kelly"
JKP = data.DATA / "jkp"
NAMES = {"accruals": "Accruals", "debt_issuance": "Debt Issuance", "investment": "Investment",
         "low_leverage": "Low Leverage", "low_risk": "Low Risk", "momentum": "Momentum",
         "profit_growth": "Profit Growth", "profitability": "Profitability", "quality": "Quality",
         "seasonality": "Seasonality", "short_term_reversal": "Short-Term Reversal", "size": "Size",
         "value": "Value"}
PERIODS = {"1967-1989": ("1967", "1989"), "1990-2006": ("1990", "2006"), "2007-2016": ("2007", "2016"),
           "2017-2025": ("2017", "2025"), "2012-2025": ("2012", "2025")}


def jkp_series():
    t = pd.read_parquet(JKP / "themes_usa_vw_cap.parquet")
    t["m"] = pd.to_datetime(t.date).dt.to_period("M")
    allst = t.pivot(index="m", columns="name", values="ret").rename(columns=NAMES)
    f = pd.read_parquet(JKP / "factors_usa_size.parquet")
    lab = pd.read_csv(JKP / "cluster_labels.csv").set_index("characteristic")
    f["theme"] = f.name.map(lab.cluster)
    f["ret"] = f.ret * f.name.map(lab.direction)        # size-group files are raw high-minus-low
    f["m"] = pd.to_datetime(f.date).dt.to_period("M")
    size = {g: f[f.size_grp == g].groupby(["m", "theme"]).ret.mean().unstack() for g in ("mega", "large")}
    return {"JKP todas (vw cap.)": allst, "JKP mega": size["mega"], "JKP large": size["large"]}


def sharpe(x):
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(12) if len(x) > 12 else np.nan


def main():
    js = jkp_series()
    c = pd.read_csv(RES / "cpz_retornos.csv", index_col=0)
    c.index = pd.PeriodIndex(c.index, freq="M")
    s = pd.read_csv(RES / "sec_retornos.csv", index_col=0, parse_dates=True)
    s.index = s.index.to_period("M") + 1                                  # holding month
    th = list(NAMES.values())
    ours = {"Nuestro CRSP top 500": c[th], "Nuestro SEC S&P 500": s[th]}
    allser = {**js, **ours}

    # 1. Sharpe by period, each theme and the equal-weight combination
    rows = []
    for name, df in allser.items():
        df = df.reindex(columns=th)
        comb = df.mean(axis=1).where(df.notna().sum(axis=1) >= 10)
        for per, (a, b) in PERIODS.items():
            x = df.loc[a:b]
            if x.dropna(how="all").shape[0] < 24:
                continue
            rows.append({"serie": name, "periodo": per, "Combinado 13": sharpe(comb.loc[a:b]),
                         "Combinado %/mes": 100 * comb.loc[a:b].mean(), **{t: sharpe(x[t]) for t in th}})
    sh = pd.DataFrame(rows)
    sh.to_csv(RES / "jkp_sharpe_periodos.csv", index=False, float_format="%.3f")

    # 2. monthly correlation of our themes with the official ones
    cor = []
    for ours_name, o in ours.items():
        for jn in ("JKP todas (vw cap.)", "JKP mega", "JKP large"):
            j = js[jn].reindex(columns=th)
            idx = o.dropna(how="all").index.intersection(j.dropna(how="all").index)
            cor.append({"nuestro": ours_name, "oficial": jn, "meses": len(idx),
                        **{t: o.loc[idx, t].corr(j.loc[idx, t]) for t in th},
                        "Combinado 13": o.loc[idx].mean(axis=1).corr(j.loc[idx].mean(axis=1))})
    # CPZ firm ids restart at its train/valid/test boundaries (1987, ~2000): the 12-month and 5-year
    # history proxies (Debt Issuance, Profit Growth, Seasonality) are missing right after them.
    cor = pd.DataFrame(cor)
    cor.to_csv(RES / "jkp_correlaciones.csv", index=False, float_format="%.3f")

    pd.set_option("display.width", 260)
    print(sh[["serie", "periodo", "Combinado 13", "Combinado %/mes"]].round(2).to_string(index=False))
    print(sh.drop(columns=["Combinado %/mes"]).set_index(["serie", "periodo"]).round(2).T.to_string())
    print(cor.set_index(["nuestro", "oficial"]).round(2).T.to_string())

    # figure: rolling 5-year Sharpe of the 13-theme combination
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.4), width_ratios=[1.25, 1])
    cols = {"JKP todas (vw cap.)": MUTED, "JKP mega": C[0], "JKP large": C[2],
            "Nuestro CRSP top 500": C[1], "Nuestro SEC S&P 500": C[3]}
    for name, df in allser.items():
        df = df.reindex(columns=th)
        comb = df.mean(axis=1).where(df.notna().sum(axis=1) >= 10).loc["1963":]
        r = comb.rolling(60, min_periods=48)
        rs = (r.mean() / r.std() * np.sqrt(12)).dropna()
        a1.plot(rs.index.to_timestamp(), rs, color=cols[name], label=name, lw=1.4 if "Nuestro" in name else 1.8)
    a1.axhline(0, color=MUTED, lw=0.8)
    a1.set_title("Sharpe móvil a 5 años de la combinación de los 13 temas (bruto)", loc="left", fontsize=9.5, color=INK)
    a1.legend(fontsize=7.5, loc="upper right")
    m = sh[sh.serie == "JKP mega"].set_index("periodo")[th]
    y = np.arange(len(th))
    for i, per in enumerate(["1967-1989", "1990-2006", "2007-2016", "2017-2025"]):
        a2.barh(y + (i - 1.5) * 0.2, m.loc[per], 0.2, color=[C[0], C[1], C[2], C[3]][i], label=per)
    a2.set_yticks(y, th, fontsize=8)
    a2.invert_yaxis()
    a2.axvline(0, color=MUTED, lw=0.8)
    a2.set_title("JKP oficial, mega caps: Sharpe de cada tema", loc="left", fontsize=9.5, color=INK)
    a2.legend(fontsize=7.5, loc="lower right")
    fig.suptitle("Factores oficiales de Jensen-Kelly-Pedersen frente a nuestra reconstrucción", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(data.ROOT / "figures" / "kelly2_oficial_vs_nuestro.png")


if __name__ == "__main__":
    main()
