"""Year-by-year Sharpe ratio of the SYY short strategy, 2006-2026 (figure 13).

Two backtests, both net of Darwinex Zero costs (spread + commission, 15 % dividend withholding):
  CRSP/CPZ 1967-2016   top 500 by market cap, 10 most overpriced (M), hedged with the EW top 500
                       (darwinex_sim.book; no sector cap: CPZ has no GICS sectors)
  SEC PIT 2012-2026    point-in-time S&P 500, 10 most overpriced with max 3 per sector, hedged with
                       SPY (pit_backtest.py, the live rule)
Both are dated by the HOLDING month. Sharpe = mean / std of the monthly returns of each calendar
year x sqrt(12) (12 observations: a noisy number, read it together with the yearly return).
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import data
import darwinex_sim as dsim
from cpz_mispricing import bins, load, size_filter
from pit_figures import C, FIG, GRID, INK, MUTED

OUT = data.ROOT / "results" / "recent"


def cpz_series():
    d = size_filter(load(), 500)
    d["qM"] = d.groupby("month").M.transform(lambda x: bins(x, 5))
    b = dsim.book(d, d.qM >= 4, "mercado", 10)
    trade = 2 * (dsim.SPREAD + dsim.COMM) * b.to_s
    return b.r_long - b.r_short - dsim.DIV_WHT - trade


def pit_series():
    s = pd.read_csv(OUT / "pit" / "strategy_returns.csv", index_col=0, parse_dates=True)
    s = s["Top10 límite sectorial / SPY, neto Zero"]
    s.index = s.index + pd.offsets.MonthEnd(1)              # formation t -> holding month t+1
    return s


def yearly(s):
    g = s.groupby(s.index.year)
    return pd.DataFrame({"retorno_%": 100 * (g.apply(lambda x: (1 + x).prod()) - 1),
                         "vol_%": 100 * g.std() * np.sqrt(12),
                         "sharpe": g.mean() / g.std() * np.sqrt(12), "meses": g.size()})


def main():
    a = cpz_series()
    a.index = a.index.to_timestamp(how="end").normalize()     # CPZ month = holding month
    b = pit_series()
    ya, yb = yearly(a.loc["2006":]), yearly(b)
    tab = pd.concat({"CRSP_CPZ": ya, "SEC_PIT": yb}, axis=1).loc[2006:]
    tab.round(3).to_csv(OUT / "sharpe_anual.csv")

    def agg(s):
        return pd.Series({"media_%mes": 100 * s.mean(), "sharpe": s.mean() / s.std() * np.sqrt(12),
                          "vol_%": 100 * s.std() * np.sqrt(12), "meses": len(s)})
    joined = pd.concat([a.loc["2006":"2011"], b])                # CPZ until 2011, SEC from 2012
    per = pd.DataFrame({"CRSP 2006-2016": agg(a.loc["2006":"2016"]), "SEC 2012-2026": agg(b),
                        "Empalme 2006-2026": agg(joined),
                        "CRSP 2012-2016": agg(a.loc["2012":"2016"]), "SEC 2012-2016": agg(b.loc[:"2016"])}).T
    per.round(3).to_csv(OUT / "sharpe_periodos.csv")
    pos = (pd.concat([ya.sharpe.loc[:2011], yb.sharpe]) > 0)
    print(tab.round(2).to_string())
    print(per.round(2).to_string())
    print(f"Años con Sharpe positivo 2006-2026 (empalme): {pos.sum()} de {len(pos)}")
    print("Correlación mensual CRSP vs SEC 2012-2016:",
          round(a.loc["2012":"2016"].reset_index(drop=True).corr(b.loc[:"2016"].reset_index(drop=True)), 2))

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, height_ratios=[1.3, 1])
    years = np.arange(2006, 2027)
    w = 0.4
    for i, (col, lab, y) in enumerate((("CRSP_CPZ", "CRSP / Chen-Pelger-Zhu (top 500, cobertura mercado EW)", ya),
                                       ("SEC_PIT", "SEC point-in-time (S&P 500, límite sectorial, cobertura SPY)", yb))):
        y = y.reindex(years)
        ax.bar(years + (i - 0.5) * w, y.sharpe, w, color=C[i], label=lab)
        ax2.bar(years + (i - 0.5) * w, y["retorno_%"], w, color=C[i])
    for a_ in (ax, ax2):
        a_.axhline(0, color=MUTED, lw=0.8)
    ax.set_ylabel("Sharpe del año")
    ax2.set_ylabel("retorno del año, %")
    fig.suptitle("Short SYY, 10 cortos cubiertos, neto Darwinex Zero: Sharpe y retorno por año",
                 x=0.01, ha="left", fontsize=10.5, color=INK)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=8)
    ax2.set_xticks(years, [str(y) if y < 2026 else "2026*" for y in years], rotation=0, fontsize=8)
    ax2.text(1.0, -0.22, "* 2026: enero-octubre", transform=ax2.transAxes, ha="right", fontsize=7.5, color=MUTED)
    fig.tight_layout()
    fig.savefig(FIG / "fig13_sharpe_anual.png")


if __name__ == "__main__":
    main()
