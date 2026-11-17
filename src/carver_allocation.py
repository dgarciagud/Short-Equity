"""Carver-style allocation of the account between the three sleeves, under Darwinex Zero's margin.

Sleeves (monthly net returns, dated by the holding month, common window 2013-2026):
  SYY      10 overpriced shorts hedged with SPY   (per unit of short value; gross = 2 per unit)
  value    3 cheapest per sector, hedged with ETF (per unit of long value;  gross = 2 per unit)
  beta     RSP, EWMAC trend + vol target, long    (per unit of sleeve capital; gross <= 1 per unit)
Carver (Systematic Trading, ch. 4-11):
  1. risk weights w by handcrafting on the correlation matrix (3 sleeves, similar correlations ->
     close to equal; tilted only when a pair is clearly more correlated);
  2. strategy diversification multiplier SDM = 1 / sqrt(w' rho w), capped at 2.5;
  3. risk budget of a sleeve = tau x w_s x SDM; its size N_s = budget / sigma_s (per unit of equity);
  4. margin: sum_s N_s x gross_s <= 90 % of equity (Zero: 100 % margin, no leverage). tau is the
     largest target the margin allows, unless a lower one is asked for.
Output: weights, sizes in USD for the account, the combined backtest and the current SYY cut.
"""
import sys

import numpy as np
import pandas as pd

import data

REC = data.ROOT / "results" / "recent"
CAPITAL = float(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
MARGIN_MAX = 0.90
GROSS = {"SYY": 2.0, "value": 2.0, "beta": 1.0}


def sleeves():
    s = pd.read_csv(REC / "pit" / "strategy_returns.csv", index_col=0, parse_dates=True)["Top10 límite sectorial / SPY, neto Zero"]
    s.index = (s.index + pd.offsets.MonthEnd(1)).to_period("M")
    v = pd.read_csv(REC / "value_sectorial" / "retornos.csv", index_col=0, parse_dates=True)["largo 3 por sector / ETF"]
    v.index = (v.index + pd.offsets.MonthEnd(1)).to_period("M")
    b = pd.read_csv(REC / "beta_ewmac" / "retornos_diarios.csv", index_col=0, parse_dates=True)
    b = b["Tendencia + vol. objetivo, solo largo (máx. 1)"]
    b = ((1 + b).groupby(b.index.to_period("M")).prod() - 1)
    return pd.DataFrame({"SYY": s, "value": v, "beta": b}).dropna()


def handcraft(rho):
    """Carver's handcrafting for three assets: equal weights, shifted away from the most
    correlated pair when its correlation stands out (table in Systematic Trading, ch. 4)."""
    names = list(rho.columns)
    w = pd.Series(1 / 3, index=names)
    pairs = {(a, b): rho.loc[a, b] for i, a in enumerate(names) for b in names[i + 1:]}
    (a, b), top = max(pairs.items(), key=lambda kv: kv[1])
    others = [c for c in pairs.values() if c != top]
    if top - np.mean(others) > 0.3:
        c = next(x for x in names if x not in (a, b))
        w[[a, b]], w[c] = 0.30, 0.40
    return w


def main():
    R = sleeves()
    sig = R.std() * np.sqrt(12)
    rho = R.corr()
    w = handcraft(rho)
    sdm = min(2.5, 1 / np.sqrt(w.values @ rho.values @ w.values))
    gross_per_tau = sum(w[s] * sdm / sig[s] * GROSS[s] for s in R)          # margin used per unit of tau
    tau = MARGIN_MAX / gross_per_tau
    N = pd.Series({s: tau * w[s] * sdm / sig[s] for s in R})                # units per unit of equity
    port = (R * N).sum(axis=1)
    eq = (1 + port).cumprod()

    pd.set_option("display.width", 200)
    print(f"Ventana {R.index[0]} - {R.index[-1]} ({len(R)} meses)\n")
    print("Volatilidad anual por unidad y Sharpe de cada estrategia:")
    print(pd.DataFrame({"vol_%": 100 * sig, "sharpe": R.mean() / R.std() * np.sqrt(12),
                        "%/mes": 100 * R.mean()}).round(2).to_string())
    print("\nCorrelaciones mensuales:\n", rho.round(2).to_string())
    print(f"\nPesos de riesgo (handcrafting): {w.round(3).to_dict()}   SDM = {sdm:.2f}")
    print(f"Volatilidad objetivo máxima que permite el margen (≤{MARGIN_MAX:.0%}): {100 * tau:.1f} % anual")
    tab = pd.DataFrame({"unidades_por_capital": N, "USD": N * CAPITAL,
                        "margen_USD": N * CAPITAL * pd.Series(GROSS),
                        "riesgo_aportado_%": 100 * tau * w * sdm})
    print("\nTamaños (unidades: SYY y value = dinero por pata; beta = capital asignado a RSP):\n",
          tab.round(3).to_string())
    print(f"\nCartera combinada: {100 * port.mean():.2f} %/mes, vol {100 * port.std() * np.sqrt(12):.1f} %, "
          f"Sharpe {port.mean() / port.std() * np.sqrt(12):.2f}, DD máx {100 * (eq / eq.cummax() - 1).min():.1f} %")
    cur = R.SYY * 0.45
    ce = (1 + cur).cumprod()
    print(f"SYY actual (0,45 por pata): {100 * cur.mean():.2f} %/mes, vol {100 * cur.std() * np.sqrt(12):.1f} %, "
          f"Sharpe {cur.mean() / cur.std() * np.sqrt(12):.2f}, DD máx {100 * (ce / ce.cummax() - 1).min():.1f} %")
    for k in (2012, 2017, 2022):
        x = port.loc[str(k):str(k + 4)]
        print(f"  {k}-{k + 4}: combinada {100 * x.mean():.2f} %/mes, Sharpe {x.mean() / x.std() * np.sqrt(12):.2f}")
    out = pd.concat({"pesos": w, "vol": sig, "unidades": N}, axis=1)
    out.attrs = {}
    out.to_csv(REC / "asignacion_carver.csv", float_format="%.4f")


if __name__ == "__main__":
    main()
