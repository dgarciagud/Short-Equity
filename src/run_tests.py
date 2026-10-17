"""Head-to-head tests and survivorship-bias check.

1. Spread tests: (short FIP) - (short abrupt) per window, with Newey-West t.
2. Survivorship: same strategies on Yahoo (today's members) vs AlgoSeek
   (point-in-time members) over the common 2017-2021 window."""
import numpy as np
import pandas as pd

import backtest as bt
import data
from signals import MONTHLY_WINDOWS, WEEKLY_WINDOWS

OUT = data.ROOT / "results"
FIP = "FIP (perdedor continuo, ID bajo)"
RIVALS = {"MOM": "MOM (quintil perdedor)", "DISC": "DISC (perdedor brusco, ID alto)",
          "JUMP": "JUMP (perdedor con mayor caida de 1 dia)",
          "CRASH": "CRASH (decil mayor caida ultimo periodo)"}


def spread_tests():
    rows = []
    for ds in ("algoseek", "yahoo"):
        for freq, wins in (("M", MONTHLY_WINDOWS), ("W", WEEKLY_WINDOWS)):
            ppy = 12 if freq == "M" else 52
            for win in wins:
                r = pd.read_parquet(OUT / "returns" / f"{ds}_{freq}_{win}.parquet")
                for leg in ("ls", "ls_bruto"):
                    for tag, k in RIVALS.items():
                        a, b = f"{FIP}|mkt|{leg}", f"{k}|mkt|{leg}"
                        if a not in r or b not in r:
                            continue
                        d = (r[a] - r[b]).dropna()
                        rows.append(dict(dataset=ds, freq=freq, window=win, leg=leg,
                                         comparacion=f"FIP - {tag}",
                                         dif_anual=d.mean() * ppy,
                                         t_NW=bt.nw_t(d, 3 if ppy == 12 else 4),
                                         pct_periodos_FIP_mejor=(d > 0).mean(),
                                         n=len(d)))
    return pd.DataFrame(rows)


def survivorship():
    rows = []
    for freq, win in (("M", "12-1m"), ("M", "1-0m"), ("W", "13-1w"), ("W", "4-1w")):
        ppy = 12 if freq == "M" else 52
        for ds in ("algoseek", "yahoo"):
            df = pd.read_parquet(OUT / "panels" / f"{ds}_{freq}_{win}.parquet")
            df = df[(df.date >= "2017-12-01") & (df.date <= "2021-11-30")]
            for name in ["MOM (quintil perdedor)", FIP, "DISC (perdedor brusco, ID alto)",
                         "CRASH (decil mayor caida ultimo periodo)"]:
                r = bt.run_strategy(df, bt.SEL[name], hedge="mkt", ppy=ppy, cost_bps=0, borrow=0)
                rows.append(dict(window=win, dataset=ds, strategy=name,
                                 ret_anual_bruto=r.ls.mean() * ppy,
                                 sharpe_bruto=r.ls.mean() / r.ls.std() * np.sqrt(ppy),
                                 ret_perdedores_anual=-r.short.mean() * ppy))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    s = spread_tests()
    s.to_csv(OUT / "spread_tests.csv", index=False, float_format="%.4f")
    v = survivorship()
    v.to_csv(OUT / "survivorship_2017_2021.csv", index=False, float_format="%.4f")
    pd.set_option("display.width", 200)
    print(s[s.leg == "ls_bruto"].pivot_table(index=["dataset", "comparacion"], columns="window",
                                              values="t_NW").round(2))
    print(s[s.leg == "ls_bruto"].pivot_table(index=["dataset", "comparacion"], columns="window",
                                              values="dif_anual").round(3))
    print(v.pivot_table(index=["window", "strategy"], columns="dataset",
                        values=["sharpe_bruto", "ret_perdedores_anual"]).round(2))
