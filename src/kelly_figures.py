"""Figure K1: the 13 JKP themes in large US stocks, CRSP 1967-2016 and SEC point-in-time 2012-2026."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import data
from pit_figures import C, GRID, INK, MUTED

RES = data.ROOT / "results" / "kelly"
FIG = data.ROOT / "figures"


def sharpe(x):
    x = x.dropna()
    return x.mean() / x.std() * np.sqrt(12)


def main():
    c = pd.read_csv(RES / "cpz_retornos.csv", index_col=0)
    c.index = pd.PeriodIndex(c.index, freq="M").to_timestamp(how="end")
    s = pd.read_csv(RES / "sec_retornos.csv", index_col=0, parse_dates=True)
    s.index = s.index + pd.offsets.MonthEnd(1)                       # holding month
    th = [x for x in s.columns if not x.startswith(("Combinado", "libro"))]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6), width_ratios=[1.15, 1])
    for col, lab, i in (("Combinado EW (13 temas, bruto)", "13 temas, igual peso (bruto)", 0),
                        ("libro25_neto", "Libro 25 largos / 25 cortos, neto Zero", 1)):
        a1.plot((1 + c[col]).cumprod(), color=C[i], label=f"{lab}, CRSP")
        a1.plot((1 + s[col]).cumprod() * (1 + c[col]).cumprod().loc[:"2011"].iloc[-1], color=C[i], ls="--",
                label=f"{lab}, SEC 2012-2026")
    a1.set_yscale("log")
    a1.set_title("Crecimiento de 1 $ (escala log.)", loc="left", fontsize=9.5, color=INK)
    a1.legend(fontsize=7.5, loc="lower right")
    per = {"CRSP 1967-1989": c.loc[:"1989"], "CRSP 1990-2006": c.loc["1990":"2006"],
           "CRSP 2007-2016": c.loc["2007":], "SEC 2012-2026": s}
    y = np.arange(len(th))
    h = 0.2
    for i, (lab, d) in enumerate(per.items()):
        a2.barh(y + (i - 1.5) * h, [sharpe(d[t]) for t in th], h, color=C[i] if i < 4 else MUTED, label=lab)
    a2.set_yticks(y, th, fontsize=8)
    a2.invert_yaxis()
    a2.axvline(0, color=MUTED, lw=0.8)
    a2.set_title("Sharpe de cada tema (quintil alto − bajo, bruto)", loc="left", fontsize=9.5, color=INK)
    a2.legend(fontsize=7.5, loc="lower right")
    fig.suptitle("Las 13 familias de Jensen-Kelly-Pedersen en las 500 mayores de EE. UU.", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(FIG / "kelly1_temas.png")


if __name__ == "__main__":
    main()
