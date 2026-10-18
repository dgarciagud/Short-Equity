"""Hysteresis (buffer) rules for the concentrated SYY short book, CPZ top 500, 1967-2016.

Each month every stock is ranked by the mispricing score M (1 = most overpriced).
A name enters the short book when it ranks inside the top N; a held name is only
dropped when its rank falls below `exit_rank` (or it leaves the data). `cap` limits
the number of names replaced per month (a proxy for spreading entries over the
weeks). The long leg is either the EW top-500 market (SPY proxy) or the mirror
book of the most underpriced names with the same rule.
Costs: Darwinex measured spread (8 bp per side) + 0.02 USD/share commission;
account 'zero' (no swaps) or 'classic' (long -5.5 %, short +2.1 % per year).
"""
import numpy as np
import pandas as pd

import data
from cpz_mispricing import load, size_filter, tstat
from darwinex_sim import COMM, DAYS_PER_MONTH

OUT = data.ROOT / "results" / "cpz"
SPREAD = 0.0008
DIV_WHT = 0.15 * 0.025 / 12
FIN = {"zero": 0.0, "classic": (-0.055 + 0.021) / 360 * DAYS_PER_MONTH}


def run_book(d, n, exit_rank, cap, ascending):
    """Monthly returns and turnover of a buffered book of n names."""
    held, rows = [], []
    for m, g in d.groupby("month"):
        rk = g.set_index("firm").M.rank(ascending=ascending, method="first")
        present = [h for h in held if h in rk.index]
        out = [h for h in present if rk[h] > exit_rank]
        out.sort(key=lambda h: -rk[h])                     # worst first
        if cap is not None and len(out) > cap:
            out = out[:cap]
        keep = [h for h in present if h not in out]
        missing = len(held) - len(present)
        new = [f for f in rk.sort_values().index if f not in keep][: n - len(keep)]
        book = keep + new
        traded = len(new) if held else n
        rows.append((m, g.set_index("firm").ret.reindex(book).mean(), traded / n, missing))
        held = book
    return pd.DataFrame(rows, columns=["month", "ret", "turnover", "missing"]).set_index("month")


def main():
    p = load()
    d = size_filter(p, 500)
    mkt = d.groupby("month").ret.mean()
    res, n = [], 10
    cost_side = SPREAD + COMM
    for exit_rank in (10, 15, 20, 25, 30, 40):
        for cap in (None, 4, 2):
            s = run_book(d, n, exit_rank, cap, ascending=False)     # most overpriced
            l = run_book(d, n, exit_rank, cap, ascending=True)      # most underpriced
            for hedge in ("SPY (mercado)", "infravaloradas"):
                if hedge.startswith("SPY"):
                    gross = mkt.reindex(s.index) - s.ret
                    trade = 2 * cost_side * s.turnover
                else:
                    gross = l.ret - s.ret
                    trade = 2 * cost_side * (s.turnover + l.turnover)
                for acc, fin in FIN.items():
                    net = gross + fin - DIV_WHT - trade
                    eq = (1 + net).cumprod()
                    res.append({"cuenta": acc, "cobertura": hedge, "salida_rank": exit_rank,
                                "cap_mes": "sin límite" if cap is None else cap,
                                "media_%mes": 100 * net.mean(), "t": tstat(net),
                                "sharpe": net.mean() / net.std() * np.sqrt(12),
                                "vol_%": 100 * net.std() * np.sqrt(12),
                                "max_dd_%": 100 * (eq / eq.cummax() - 1).min(),
                                "peor_mes_%": 100 * net.min(),
                                "post2000_%mes": 100 * net.loc["2000":].mean(),
                                "rotacion_corto_%mes": 100 * s.turnover.iloc[1:].mean(),
                                "nombres_cambiados_mes": n * s.turnover.iloc[1:].mean(),
                                "coste_trading_%mes": 100 * trade.iloc[1:].mean(),
                                "permanencia_media_meses": 1 / max(s.turnover.iloc[1:].mean(), 1e-9)})
    out = pd.DataFrame(res)
    out.to_csv(OUT / "buffer_rules.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    for acc in FIN:
        for hedge in ("SPY (mercado)", "infravaloradas"):
            x = out[(out.cuenta == acc) & (out.cobertura == hedge)]
            print(f"=== {acc} | {hedge}")
            print(x.drop(columns=["cuenta", "cobertura"]).round(2).to_string(index=False))


if __name__ == "__main__":
    main()
