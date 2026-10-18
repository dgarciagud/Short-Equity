"""Darwinex Classic (stock CFDs) cost model applied to the SYY/CPZ short strategies.

Contract terms supplied by the user (AAPL, ACHC example rows):
  margin 20 %, min size 1 share, commission 0.02 USD per share per order,
  daily swap long -0.02 %, daily swap short +0.01 % (applied every calendar day;
  the triple rollover covers weekends), so per 30.4-day month:
  long  -0.608 %, short +0.304 % of notional.

Universe: top 500 stocks by market cap each month (CPZ panel, 1967-2016).
Concentrated books: each month take the N most overpriced names (highest M)
inside the candidate set; hedge either with the EW top-500 market (proxy for an
index CFD or basket) or with the N most underpriced names (lowest M).
Returns in CPZ are excess of the T-bill, so CFD financing enters relative to it:
a dollar-neutral book's financing is (short credit - long charge) and the T-bill
terms cancel; a short-only book earns -excess + (short credit - T-bill).
"""
import numpy as np
import pandas as pd

import data
from cpz_mispricing import bins, factors, load, size_filter, tstat

OUT = data.ROOT / "results" / "cpz"
DAYS_PER_MONTH = 365.25 / 12
SWAP_LONG = -0.0002 * DAYS_PER_MONTH    # -0.61 %/month
SWAP_SHORT = 0.0001 * DAYS_PER_MONTH    # +0.30 %/month
SPREAD = 0.0005                         # 5 bp half-spread per side (assumption)
COMM = 0.0001                           # 0.02 USD/share on a ~200 USD share
DIV_WHT = 0.15 * 0.025 / 12             # 15 % withholding on a ~2.5 % dividend yield, long leg only


def book(d, short_mask, long_mode, n):
    """Monthly gross return of a concentrated long/short (or short-only) book."""
    rows = []
    prev_s, prev_l = set(), set()
    for m, g in d.groupby("month"):
        cand = g[short_mask.loc[g.index]]
        if len(cand) < n:
            continue
        s = cand.nlargest(n, "M")
        r_short = s.ret.mean()
        if long_mode == "mercado":
            r_long, l_ids = g.ret.mean(), set()
        elif long_mode == "infravaloradas":
            l = g.nsmallest(n, "M")
            r_long, l_ids = l.ret.mean(), set(l.firm)
        else:
            r_long, l_ids = np.nan, set()
        to_s = 1 - len(prev_s & set(s.firm)) / n
        to_l = (1 - len(prev_l & l_ids) / n) if l_ids else (0.0 if long_mode == "mercado" else 0.0)
        rows.append((m, r_short, r_long, to_s, to_l))
        prev_s, prev_l = set(s.firm), l_ids
    return pd.DataFrame(rows, columns=["month", "r_short", "r_long", "to_s", "to_l"]).set_index("month")


def main():
    p = load()
    d = size_filter(p, 500)
    d["qM"] = d.groupby("month").M.transform(lambda x: bins(x, 5))
    d["qMom"] = d.groupby("month").r12_2.transform(lambda x: bins(x, 5))
    d["qIV"] = d.groupby("month").IdioVol.transform(lambda x: bins(x, 5))
    ff = factors()
    rf = ff["RF"]
    cands = {
        "SYY M: más sobrevaloradas": d.qM >= 4,
        "Perdedoras Y sobrevaloradas": (d.qMom == 1) & (d.qM >= 4),
        "Sobrevaloradas Y alta IVOL": (d.qIV == 5) & (d.qM >= 4),
    }
    cost_trade = SPREAD + COMM
    rows = []
    for name, mask in cands.items():
        for n in (5, 10, 15, 20):
            for hedge in ("mercado", "infravaloradas", "sin cobertura"):
                b = book(d, mask, hedge, n)
                if hedge == "sin cobertura":
                    gross = -b.r_short
                    fin = SWAP_SHORT - rf.reindex(b.index).fillna(0)
                    trade = 2 * cost_trade * b.to_s
                else:
                    gross = b.r_long - b.r_short
                    fin = pd.Series(SWAP_SHORT + SWAP_LONG - DIV_WHT, index=b.index)
                    trade = 2 * cost_trade * (b.to_s + b.to_l)
                net = gross + fin - trade
                for lab, s in (("bruto", gross), ("neto Darwinex", net)):
                    rows.append({"candidatas": name, "N por lado": n, "cobertura": hedge, "medida": lab,
                                 "media_%mes": 100 * s.mean(), "t": tstat(s),
                                 "vol_anual_%": 100 * s.std() * np.sqrt(12),
                                 "sharpe": s.mean() / s.std() * np.sqrt(12),
                                 "peor_mes_%": 100 * s.min(),
                                 "max_dd_%": 100 * ((1 + s).cumprod() / (1 + s).cumprod().cummax() - 1).min(),
                                 "post2000_%mes": 100 * s.loc["2000":].mean(),
                                 "rotacion_corto": b.to_s.mean(), "meses": len(s)})
    res = pd.DataFrame(rows)
    res.to_csv(OUT / "darwinex_classic.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 250)
    for v in ("media_%mes", "t", "sharpe", "vol_anual_%", "max_dd_%", "peor_mes_%", "post2000_%mes"):
        for lab in ("bruto", "neto Darwinex"):
            print("==", v, lab)
            print(res[res.medida == lab].pivot_table(index=["candidatas", "cobertura"], columns="N por lado",
                                                      values=v).round(2).to_string())


if __name__ == "__main__":
    main()
