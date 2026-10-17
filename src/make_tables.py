"""Markdown tables for REPORT.md -> results/tables.md."""
import pandas as pd

import data

OUT = data.ROOT / "results"
g = pd.read_csv(OUT / "grid_stats.csv")
CORE = ["MOM (quintil perdedor)", "FIP (perdedor continuo, ID bajo)", "DISC (perdedor brusco, ID alto)",
        "JUMP (perdedor con mayor caida de 1 dia)", "CRASH (decil mayor caida ultimo periodo)"]
SECTOR = ["FIP (perdedor continuo, ID bajo)", "FIP + sector perdedor (misma ventana)",
          "FIP + sector perdedor (1 mes)", "FIP + sector FIP (sector cae gradual)",
          "DISC + sector perdedor (misma ventana)", "SECTOR mom 1 mes", "SECTOR mom misma ventana",
          "SECTOR FIP (caida gradual)"]
RESID = ["MOM (quintil perdedor)", "RMOM (perdedor residual)", "FIP (perdedor continuo, ID bajo)",
         "RFIP (perdedor residual continuo)"]
DIFF = ["Rezagados (todos)", "Rezagados con lideres debiles", "FIP no-lider con lideres debiles",
        "Proveedores (todos)", "Proveedores con clientes debiles"]
HEDGE = {"mkt": "mercado", "sector": "sector EW", "pair": "par (largo fuertes sector)",
         "sectores": "L/S sectores"}


def table(ds, w, strats, hedges=("mkt",), leg="ls"):
    x = g[(g.dataset == ds) & (g.window == w) & g.strategy.isin(strats) & g.hedge.isin(hedges)
          & (g.leg == leg)].copy()
    x["strategy"] = pd.Categorical(x.strategy, strats)
    x["hedge"] = pd.Categorical(x.hedge.map(HEDGE), [HEDGE[h] for h in hedges])
    x = x.sort_values(["strategy", "hedge"])
    pct = ["ret_anual", "vol_anual", "alfa_FF6_anual", "max_dd", "ret_en_crashes_MOM"]
    x[pct] = (x[pct] * 100).round(1)
    x[["sharpe", "t_NW", "t_alfa", "beta_MOM"]] = x[["sharpe", "t_NW", "t_alfa", "beta_MOM"]].round(2)
    x["n_medio"] = x.n_medio.round(0)
    x = x[["strategy", "hedge", "ret_anual", "vol_anual", "sharpe", "t_NW", "alfa_FF6_anual", "t_alfa",
           "beta_MOM", "max_dd", "ret_en_crashes_MOM", "n_medio"]]
    x.columns = ["Estrategia", "Cobertura", "Ret %/a", "Vol %/a", "Sharpe", "t NW", "Alfa FF6 %/a",
                 "t alfa", "β MOM", "MaxDD %", "Crashes MOM %", "Nº cortos"]
    return x.to_markdown(index=False)


def main():
    out = []
    for ds, w in [("yahoo", "12-1m"), ("yahoo", "1-0m"), ("yahoo", "13-1w"), ("algoseek", "12-1m"),
                  ("algoseek", "1-0m"), ("algoseek", "13-1w")]:
        out.append(f"### Núcleo FIP vs brusco — {ds} {w} (neto, cubierto con mercado)\n\n" + table(ds, w, CORE))
    for ds, w in [("yahoo", "12-1m"), ("yahoo", "1-0m"), ("algoseek", "1-0m")]:
        out.append(f"### Filtro sectorial — {ds} {w}\n\n" + table(ds, w, SECTOR, ("mkt", "sectores")))
    for ds, w in [("yahoo", "12-1m"), ("yahoo", "6-1m"), ("algoseek", "12-1m")]:
        out.append(f"### Residual vs bruto — {ds} {w}\n\n" + table(ds, w, RESID, ("mkt", "sector", "pair")))
    for ds, w in [("yahoo", "1-0m"), ("yahoo", "4-1w"), ("algoseek", "1-0m")]:
        out.append(f"### Difusión lenta — {ds} {w}\n\n" + table(ds, w, DIFF))
    s = pd.read_csv(OUT / "spread_tests.csv")
    s = s[s.leg == "ls_bruto"]
    out.append("### Test directo FIP − rival (bruto), t de Newey-West\n\n" + s.pivot_table(
        index=["dataset", "comparacion"], columns="window", values="t_NW").round(2).to_markdown())
    out.append("### Diferencia FIP − rival (bruto), % anual\n\n" + (s.pivot_table(
        index=["dataset", "comparacion"], columns="window", values="dif_anual") * 100).round(1).to_markdown())
    v = pd.read_csv(OUT / "survivorship_2017_2021.csv")
    out.append("### Sesgo de supervivencia 2017-2021 (bruto)\n\n" + v.pivot_table(
        index=["window", "strategy"], columns="dataset",
        values=["ret_perdedores_anual", "sharpe_bruto"]).round(2).to_markdown())
    d = pd.read_csv(OUT / "diffusion_tests.csv")
    out.append("### Fama-MacBeth difusión lenta\n\n" + d.round(3).to_markdown(index=False))
    c = pd.read_csv(OUT / "combo_stats.csv")
    for ds in ("yahoo", "algoseek"):
        x = c[c.dataset == ds].pivot_table(index="strategy", columns="window", values="sharpe", sort=False)
        out.append(f"### Dilema: sleeves vs meta-modelo — Sharpe neto fuera de muestra ({ds})\n\n"
                   + x.round(2).to_markdown())
    (OUT / "tables.md").write_text("\n\n".join(out) + "\n")


if __name__ == "__main__":
    main()
