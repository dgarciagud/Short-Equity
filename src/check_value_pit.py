"""Point-in-time audit of the value inputs used by sector_value.py.

For every (company, month-end t) row of the 13-theme panel (sec2_panel.parquet) it looks up, in the
raw SEC companyfacts cache, the filings that reported the exact value used and checks that the
EARLIEST of them was filed on or before t. Reports violations, same-day uses, the publication lag
(t - filing date) and the age of the data (t - period end), plus a few worked examples.
"""
import json
import os

import numpy as np
import pandas as pd

import data
from live_syy import SEC
from repo_xbrl import universe

PANEL = os.environ.get("KELLY_PANEL", "/home/user/Short-Equity-13-familias-kelly/results/kelly/sec2_panel.parquet")
FIELDS = {"BE": ("equity", None), "ni": ("net_income", (350, 380)), "cfo": ("cfo", (350, 380)),
          "rev": ("revenue", (350, 380)), "op": ("op_income", (350, 380))}


def raw_facts():
    hist = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    uni = universe().drop_duplicates("cik")
    cik_of = {**hist, **dict(zip(uni.symbol, uni.cik))}
    parts, seen = [], set()
    for t, c in sorted(cik_of.items()):
        f = SEC / "facts" / f"{t}.parquet"
        if c in seen or not f.exists():
            continue
        seen.add(c)
        parts.append(pd.read_parquet(f).assign(cik=c))
    x = pd.concat(parts)
    x["val"] = pd.to_numeric(x.val, errors="coerce")
    for c in ("end", "start", "filed"):
        x[c] = pd.to_datetime(x[c])
    x["days"] = (x.end - x.start).dt.days
    return x


def main():
    p = pd.read_parquet(PANEL, columns=["cik", "date"] + list(FIELDS))
    x = raw_facts()
    rows = []
    for col, (key, span) in FIELDS.items():
        r = x[x.key == key]
        r = r[r.start.isna()] if span is None else r[(r.days >= span[0]) & (r.days <= span[1])]
        r = r.dropna(subset=["val"])
        r["vkey"] = r.val.round(0)
        first = r.groupby(["cik", "vkey"]).agg(filed=("filed", "min"), end=("end", "max")).reset_index()
        q = p[["cik", "date", col]].dropna().assign(vkey=lambda d: d[col].round(0))
        m = q.merge(first, on=["cik", "vkey"], how="left")
        m["lag_dias"] = (m.date - m.filed).dt.days
        m["edad_dias"] = (m.date - m.end).dt.days
        rows.append({"campo": col, "filas": len(m), "sin_fuente_encontrada_%": 100 * m.filed.isna().mean(),
                     "publicado_DESPUES_de_t": int((m.lag_dias < 0).sum()),
                     "publicado_el_mismo_dia_%": 100 * (m.lag_dias == 0).mean(),
                     "lag_mediana_dias": m.lag_dias.median(), "lag_p10_dias": m.lag_dias.quantile(0.1),
                     "edad_mediana_dias": m.edad_dias.median(), "edad_p90_dias": m.edad_dias.quantile(0.9)})
        if col in ("BE", "ni"):
            for cik, name in ((320193, "Apple"), (34088, "Exxon"), (19617, "JPMorgan")):
                e = m[(m.cik == cik) & (m.date.between("2023-12-31", "2024-05-31"))]
                for _, z in e.iterrows():
                    print(f"{name:8s} {col:3s} t={z.date.date()} valor={z[col] / 1e6:,.0f} M  periodo={z.end.date()}"
                          f"  presentado={z.filed.date()}  ({int(z.lag_dias)} días antes de t)")
    pd.set_option("display.width", 220)
    print(pd.DataFrame(rows).round(1).to_string(index=False))


if __name__ == "__main__":
    main()
