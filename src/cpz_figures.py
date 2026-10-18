"""Figures for the SYY mispricing score on Chen-Pelger-Zhu (results/cpz -> figures/)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import data
from make_figures import C, FIG, GRID, INK, MUTED  # shared style

OUT = data.ROOT / "results" / "cpz"
HEDGED = "corto cubierto con mercado EW"
UNIV = ["Todas", "Grandes (top 30% LME)", "Top 500 (≈S&P 500)", "Mega (top 10% LME)"]
STRATS = {
    "Momentum: Q1 perdedores": "Perdedores momentum",
    "Perdedoras NO sobrevaloradas (Q1 mom & M<=Q3)": "Perdedores NO sobrevalorados",
    "Perdedoras Y sobrevaloradas (Q1 mom & Q5 M)": "Perdedores Y sobrevalorados",
    "SYY M: Q5 sobrevaloradas": "SYY M: Q5 sobrevaloradas",
    "Sobrevaloradas Y alta IVOL (Q5 M & Q5 IVOL)": "Sobrevaloradas + alta IVOL",
}


def fig_shorts():
    c = pd.read_csv(OUT / "cortos.csv")
    c = c[c.pierna == HEDGED]
    fig, ax = plt.subplots(figsize=(10, 5))
    y = np.arange(len(STRATS))
    h = 0.2
    for i, u in enumerate(UNIV):
        g = c[c.universo == u].set_index("estrategia").reindex(list(STRATS))
        ax.barh(y + (i - 1.5) * h, g["alfa_FF3_%mes"], h * 0.9, color=C[i], label=u)
        for yi, v, t in zip(y, g["alfa_FF3_%mes"], g["t_FF3"]):
            ax.text(v, yi + (i - 1.5) * h, f" {v:.2f} (t {t:.1f})", va="center", fontsize=6.5, color=INK)
    ax.set_yticks(y, list(STRATS.values()))
    ax.invert_yaxis()
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlim(right=ax.get_xlim()[1] + 0.35)
    ax.set_xlabel("Alfa FF3 del corto cubierto con mercado, % al mes (1967-2016)")
    ax.set_title("Chen-Pelger-Zhu (sin sesgo de supervivencia): qué perdedores conviene cortar",
                 loc="left", color=INK)
    ax.legend(fontsize=8, loc="lower right")
    fig.savefig(FIG / "fig7_cpz_cortos_syy.png")


def fig_heatmap():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.0))
    fig.subplots_adjust(wspace=0.35, top=0.84)
    for ax, u in zip(axes, ["Todas", "Top"]):
        a = pd.read_csv(OUT / f"ivol_x_M_alpha_{u}.csv", index_col=0)
        t = pd.read_csv(OUT / f"ivol_x_M_t_{u}.csv", index_col=0)
        v = a.iloc[:, :5].values
        lim = np.nanmax(np.abs(v))
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list("div", ["#c2410c", "#f4f3ee", "#2a78d6"])
        ax.imshow(v, cmap=cmap, vmin=-lim, vmax=lim, aspect="auto")
        for i in range(5):
            for j in range(5):
                ax.text(j, i, f"{v[i, j]:.2f}\n({t.iloc[i, j]:.1f})", ha="center", va="center",
                        fontsize=7, color=INK)
        ax.set_xticks(range(5), ["IVOL baja", "2", "3", "4", "IVOL alta"])
        ax.set_yticks(range(5), ["M Q1 infraval.", "Q2", "Q3", "Q4", "M Q5 sobreval."])
        ax.grid(False)
        ax.set_title(f"{'Todas las acciones' if u == 'Todas' else 'Top 500 por capitalización (≈S&P 500)'}",
                     loc="left", color=INK)
    fig.suptitle("Alfa FF3 mensual (%) por mispricing SYY × volatilidad idiosincrática (t entre paréntesis)",
                 x=0.01, ha="left", color=INK, fontsize=11)
    fig.savefig(FIG / "fig8_cpz_mispricing_x_ivol.png")


def fig_sentiment():
    s = pd.read_csv(OUT / "sentimiento.csv")
    s = s[(s.pierna == HEDGED)]
    names = ["Momentum: Q1 perdedores", "SYY M: Q5 sobrevaloradas",
             "Perdedoras Y sobrevaloradas (Q1 mom & Q5 M)", "Sobrevaloradas Y alta IVOL (Q5 M & Q5 IVOL)"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    fig.subplots_adjust(top=0.80)
    short = {n: STRATS[n].replace(" ", "\n", 1) for n in names}
    for ax, u in zip(axes, ["Todas", "Top 500 (≈S&P 500)"]):
        g = s[s.universo == u].set_index("estrategia").reindex(names)
        x = np.arange(len(names))
        ax.bar(x - 0.2, g["media_alto_%mes"], 0.38, color=C[1], label="Tras sentimiento ALTO")
        ax.bar(x + 0.2, g["media_bajo_%mes"], 0.38, color=C[0], label="Tras sentimiento BAJO")
        for xi, d, t in zip(x, g["dif_%mes"], g["t_dif"]):
            ax.text(xi, 1.42, f"Δ {d:.2f} (t {t:.1f})", ha="center", fontsize=7, color=INK)
        ax.set_ylim(top=1.55)
        ax.set_xticks(x, [short[n] for n in names], fontsize=7)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.set_title(u, loc="left", color=INK)
    axes[0].set_ylabel("Corto cubierto con mercado, % al mes")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Sentimiento Baker-Wurgler: los cortos rinden en los meses tras sentimiento alto",
                 x=0.01, ha="left", color=INK, fontsize=11)
    fig.savefig(FIG / "fig9_cpz_sentimiento.png")


def fig_cum():
    ser = pd.read_parquet(OUT / "series.parquet")
    u = "Top 500 (≈S&P 500)"
    names = ["Momentum: Q1 perdedores", "Perdedoras NO sobrevaloradas (Q1 mom & M<=Q3)",
             "Perdedoras Y sobrevaloradas (Q1 mom & Q5 M)", "SYY M: Q5 sobrevaloradas"]
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, n in enumerate(names):
        s = (1 + ser[f"{u}|{n}|{HEDGED}"].fillna(0)).cumprod()
        ax.plot(s.index, s.values, color=C[i], label=STRATS[n])
        ax.annotate(STRATS[n].split(":")[0], (s.index[-1], s.values[-1]), xytext=(4, 0),
                    textcoords="offset points", fontsize=7, color=INK, va="center")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.1f"))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.5, 1, 2, 4, 8, 16, 32]))
    ax.axhline(1, color=MUTED, lw=0.8)
    ax.set_ylabel("Crecimiento de 1 (log), bruto")
    ax.set_title("Corto cubierto con mercado, top 500 por capitalización (≈S&P 500), 1967-2016",
                 loc="left", color=INK)
    ax.legend(fontsize=8, loc="upper left")
    fig.savefig(FIG / "fig10_cpz_acumulado_grandes.png")


if __name__ == "__main__":
    fig_shorts()
    fig_heatmap()
    fig_sentiment()
    fig_cum()
