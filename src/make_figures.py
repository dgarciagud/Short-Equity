"""Figures for REPORT.md (static PNG, light theme)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import data

OUT = data.ROOT / "results"
FIG = data.ROOT / "figures"
FIG.mkdir(exist_ok=True)
# categorical slots in fixed order (validated default palette)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK, MUTED, GRID = "#2b2b29", "#6b6a63", "#e4e3dc"
plt.rcParams.update({
    "font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
    "figure.dpi": 130, "savefig.bbox": "tight", "lines.linewidth": 1.6,
})

grid = pd.read_csv(OUT / "grid_stats.csv")
combo = pd.read_csv(OUT / "combo_stats.csv")
WIN_ORDER = ["12-1m", "6-1m", "3-0m", "1-0m", "52-1w", "26-1w", "13-1w", "4-1w"]
CORE = {"MOM (quintil perdedor)": "MOM", "FIP (perdedor continuo, ID bajo)": "FIP (ID bajo)",
        "DISC (perdedor brusco, ID alto)": "DISC (ID alto, brusco)",
        "CRASH (decil mayor caida ultimo periodo)": "CRASH (mayor caida reciente)"}


def sel(ds, strat, hedge="mkt", leg="ls"):
    g = grid[(grid.dataset == ds) & (grid.strategy == strat) & (grid.hedge == hedge) & (grid.leg == leg)]
    return g.set_index("window").reindex(WIN_ORDER)


def fig_core_sharpe():
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    x = np.arange(len(WIN_ORDER))
    w = 0.2
    for ax, ds, title in zip(axes, ["yahoo", "algoseek"],
                             ["S&P 500 actual 2004-2026 (Yahoo)", "S&P 500 point-in-time 2017-2021 (AlgoSeek)"]):
        for i, (k, lab) in enumerate(CORE.items()):
            v = sel(ds, k).sharpe.values
            ax.bar(x + (i - 1.5) * w, v, w * 0.9, color=C[i], label=lab)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.axvline(3.5, color=GRID, lw=1)
        ax.set_xticks(x, WIN_ORDER)
        ax.set_title(title, color=INK, fontsize=10, loc="left")
        ax.set_xlabel("mensual  |  semanal", color=MUTED)
    axes[0].set_ylabel("Sharpe neto (corto - mercado EW)")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, fontsize=8, bbox_to_anchor=(0.5, -0.11))
    fig.suptitle("Corto en perdedores: FIP (caida continua) vs caidas bruscas, cubierto con mercado",
                 x=0.01, ha="left", color=INK, fontsize=11)
    fig.savefig(FIG / "fig1_sharpe_fip_vs_brusco.png")


def cum(r):
    return (1 + r.fillna(0)).cumprod()


def fig_cum(ds="yahoo", freq="M", win="12-1m"):
    r = pd.read_parquet(OUT / "returns" / f"{ds}_{freq}_{win}.parquet")
    fig, ax = plt.subplots(figsize=(9, 4))
    for i, (k, lab) in enumerate(CORE.items()):
        s = cum(r[f"{k}|mkt|ls"])
        ax.plot(s.index, s.values, color=C[i], label=lab)
        ax.annotate(lab.split(" ")[0], (s.index[-1], s.values[-1]), xytext=(4, 0),
                    textcoords="offset points", color=INK, fontsize=8, va="center")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.1f"))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.yaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.1, 0.2, 0.3, 0.5, 0.7, 1, 1.5, 2]))
    ax.axhline(1, color=MUTED, lw=0.8)
    ax.set_ylabel("Crecimiento de 1 (log), neto de costes")
    ax.set_title(f"Corto perdedores cubierto con mercado - {ds} {win}", loc="left", color=INK)
    ax.legend(loc="lower left", fontsize=8)
    fig.savefig(FIG / f"fig2_acumulado_{ds}_{win}.png")


def fig_sector(ds="yahoo"):
    strats = {"FIP (perdedor continuo, ID bajo)": "FIP solo",
              "FIP + sector perdedor (misma ventana)": "FIP + sector perdedor (ventana)",
              "FIP + sector perdedor (1 mes)": "FIP + sector perdedor (1 mes)",
              "FIP + sector FIP (sector cae gradual)": "FIP + sector 'rana' (ID sector)"}
    wins = ["12-1m", "1-0m", "13-1w", "4-1w"]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    x = np.arange(len(wins))
    for i, (k, lab) in enumerate(strats.items()):
        v = sel(ds, k).reindex(wins).sharpe.values
        ax.bar(x + (i - 1.5) * 0.2, v, 0.18, color=C[i], label=lab)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.set_xticks(x, wins)
    ax.set_ylabel("Sharpe neto (cubierto con mercado)")
    ax.set_title(f"Momentum sectorial como filtro del corto FIP - {ds}", loc="left", color=INK)
    ax.legend(fontsize=8, ncol=2, loc="lower left")
    fig.savefig(FIG / f"fig3_filtro_sectorial_{ds}.png")


def fig_residual(ds="yahoo", freq="M", win="12-1m"):
    r = pd.read_parquet(OUT / "returns" / f"{ds}_{freq}_{win}.parquet")
    ser = {"FIP cubierto con mercado": r["FIP (perdedor continuo, ID bajo)|mkt|ls"],
           "RFIP cubierto con mercado": r["RFIP (perdedor residual continuo)|mkt|ls"],
           "RFIP par sectorial (largo fuertes del sector)": r["RFIP (perdedor residual continuo)|pair|ls"]}
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for i, (lab, s) in enumerate(ser.items()):
        axes[0].plot(s.index, cum(s).values, color=C[i], label=lab)
        vol = s.rolling(12).std() * np.sqrt(12)
        axes[1].plot(vol.index, vol.values, color=C[i], label=lab)
    axes[0].set_yscale("log")
    axes[0].yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.1f"))
    axes[0].yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axes[0].yaxis.set_major_locator(matplotlib.ticker.FixedLocator([0.1, 0.2, 0.3, 0.5, 0.7, 1, 1.5, 2]))
    axes[0].set_title("Crecimiento de 1 (log), neto", loc="left", color=INK)
    axes[1].set_title("Volatilidad anualizada rodante 12m", loc="left", color=INK)
    axes[1].yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, fontsize=8, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle(f"Momentum residual (sin beta ni sector) - {ds} {win}", x=0.01, ha="left",
                 color=INK, fontsize=11)
    fig.savefig(FIG / f"fig4_residual_{ds}_{win}.png")
    # crash months
    ff = pd.read_parquet(data.DATA / "ff" / "mom_monthly.parquet").set_index("timestamp").MOM
    ff.index = pd.to_datetime(ff.index).to_period("M")
    s0 = pd.DataFrame(ser)
    s0.index = s0.index.to_period("M") + 1  # holding month
    worst = ff.reindex(s0.index).nsmallest(10).index
    t = s0.loc[worst]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    x = np.arange(len(worst))
    for i, c in enumerate(t.columns):
        ax.bar(x + (i - 1) * 0.27, t[c].values, 0.25, color=C[i], label=c)
    ax.set_xticks(x, [f"{p}\nMOM {ff[p]:.0%}" for p in worst], fontsize=7)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.set_title("Retorno del corto en los 10 peores meses del factor momentum (crashes)",
                 loc="left", color=INK)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    fig.savefig(FIG / f"fig5_crashes_{ds}_{win}.png")
    return t


def fig_combo():
    d = combo[(combo.dataset == "yahoo")]
    wins = ["12-1m", "1-0m", "13-1w"]
    keep = ["Filtro duro: FIP (perdedor continuo, ID bajo)|mkt|ls",
            "Filtro duro: FIP + sector perdedor (1 mes)|mkt|ls",
            "Filtro duro: RFIP (perdedor residual continuo)|sector|ls",
            "Dos sleeves 75/25 (neutral sector)",
            "Meta-modelo lgbm sin sector | pair", "Meta-modelo lgbm con sector | pair",
            "Meta-modelo ridge sin sector | pair", "Meta-modelo ridge con sector | pair"]
    fig, axes = plt.subplots(1, len(wins), figsize=(12, 3.8), sharey=True)
    for ax, w in zip(axes, wins):
        g = d[d.window == w].set_index("strategy").reindex(keep)
        y = np.arange(len(keep))
        ax.barh(y, g.sharpe.values, color=C[0], height=0.6)
        for yi, v in zip(y, g.sharpe.values):
            if np.isfinite(v):
                ax.text(v, yi, f" {v:.2f} " , va="center", ha="left" if v >= 0 else "right",
                        fontsize=7, color=INK)
        ax.axvline(0, color=MUTED, lw=0.8)
        lo, hi = ax.get_xlim()
        ax.set_xlim(lo - 0.25, max(hi, 0) + 0.15)
        ax.set_title(w, loc="left", color=INK)
        ax.set_yticks(y, [k.replace("Filtro duro: ", "Duro: ").replace("|mkt|ls", " (mkt)")
                          .replace("|sector|ls", " (sector)") for k in keep], fontsize=7)
        ax.invert_yaxis()
    axes[0].set_xlabel("Sharpe neto (periodo fuera de muestra)")
    fig.suptitle("El dilema sectorial: dos sleeves vs un libro con meta-modelo (Yahoo)",
                 x=0.01, ha="left", color=INK, fontsize=11)
    fig.savefig(FIG / "fig6_dilema_sleeves_metamodelo.png")


if __name__ == "__main__":
    fig_core_sharpe()
    for w, f in [("12-1m", "M"), ("1-0m", "M"), ("13-1w", "W")]:
        fig_cum("yahoo", f, w)
    fig_cum("algoseek", "M", "12-1m")
    fig_sector("yahoo")
    fig_sector("algoseek")
    print(fig_residual("yahoo", "M", "12-1m"))
    fig_combo()
