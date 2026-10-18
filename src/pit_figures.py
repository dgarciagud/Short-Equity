"""Figure 12: SYY short strategy 2012-2026, point-in-time S&P 500 vs today's survivors."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import data

REC = data.ROOT / "results" / "recent"
FIG = data.ROOT / "figures"
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, MUTED, GRID = "#2b2b29", "#6b6a63", "#e4e3dc"
plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.dpi": 130, "savefig.bbox": "tight", "lines.linewidth": 1.6,
})
UNIS = {"pit": ("S&P 500 histórico (point-in-time)", C[0]),
        "survivor_mismo_pipeline": ("Miembros actuales (sesgo de supervivencia)", C[1])}
STRATS = ["Top10 corto / SPY, neto Zero", "Q5 vs mercado EW, bruto"]


def main():
    ret = {u: pd.read_csv(REC / u / "strategy_returns.csv", index_col=0, parse_dates=True) for u in UNIS}
    summ = pd.read_csv(REC / "pit_vs_survivor.csv")
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9))
    for ax, s in zip(axes[:2], STRATS):
        for u, (lab, col) in UNIS.items():
            x = ret[u][s]
            x.index = x.index + pd.offsets.MonthEnd(1)          # plot at the holding month
            ax.plot((1 + x).cumprod(), color=col, label=lab)
        ax.axvspan(pd.Timestamp("2012-01-01"), pd.Timestamp("2016-12-31"), color=GRID, alpha=0.5, lw=0)
        ax.text(pd.Timestamp("2012-03-01"), 0.98, "cobertura de precios ~75%", transform=ax.get_xaxis_transform(),
                va="top", fontsize=7.5, color=MUTED)
        ax.axhline(1, color=MUTED, lw=0.8)
        ax.set_title(s, fontsize=9.5, color=INK, loc="left")
        ax.set_ylabel("crecimiento de 1 €")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=8.5, bbox_to_anchor=(0.5, -0.04))
    ax = axes[2]
    pers = ["2012-2016", "2017-2021", "2022-2026", "2012-2026"]
    w = 0.38
    for i, (u, (lab, col)) in enumerate(UNIS.items()):
        g = summ[(summ.universo == u) & (summ.estrategia == STRATS[0])].set_index("periodo").reindex(pers)
        b = ax.bar(np.arange(4) + (i - 0.5) * w, g["media_%mes"], w, color=col, label=lab)
        for rect, t in zip(b, g.t):
            ax.annotate(f"t {t:.1f}", (rect.get_x() + rect.get_width() / 2, rect.get_height()),
                        xytext=(0, 3 if rect.get_height() >= 0 else -10), textcoords="offset points",
                        ha="center", fontsize=7, color=MUTED)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_ylim(min(ax.get_ylim()[0], -0.55), None)
    ax.set_xticks(range(4), pers)
    ax.set_ylabel("% al mes (neto Zero)")
    ax.set_title("Top10 corto / SPY por subperiodo", fontsize=9.5, color=INK, loc="left")
    fig.suptitle("Short SYY 2012–2026: S&P 500 histórico vs miembros actuales (mismo pipeline)",
                 x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "fig12_pit_vs_supervivientes.png")


if __name__ == "__main__":
    main()
