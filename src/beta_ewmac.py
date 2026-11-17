"""Market-beta sleeve on the S&P 500 EQUAL-WEIGHT ETF (RSP) with Carver's EWMAC trend rule.

Carver (Systematic Trading / Advanced Futures Trading Strategies):
  raw_k = (EMA_fast - EMA_slow) / sigma_price, for the pairs 8/32, 16/64, 32/128, 64/256
          (sigma_price = daily price-change volatility, EWM span 35)
  forecast_k = raw_k x scalar_k (5.3, 3.75, 2.65, 1.87), capped at +-20; the rule variations are
  averaged and multiplied by a forecast diversification multiplier (estimated: 1 / sqrt(w' rho w)),
  capped again at +-20. An average |forecast| of 10 means a normal-size position.
Positions (fraction of the sleeve's capital, decided at the close of day t, held over t+1):
  fijo           buy and hold RSP (and SPY for reference)
  tendencia      forecast / 10, long only (0..2) or long/short (-2..2)
  tendencia+vol  forecast / 10 x (target vol / RSP vol), vol target 16 % = RSP's long-run vol
Positions are capped at 1.0 in the "sin apalancamiento" variants (Darwinex Zero) and traded only
when they move more than 10 % of a normal position (Carver's buffer).
Costs: 3 bp per unit traded (half spread + commission on a CFD around 200 USD); no interest on cash.
"""
import numpy as np
import pandas as pd
import yfinance as yf

import data

OUT = data.ROOT / "results" / "recent" / "beta_ewmac"
PAIRS = [(8, 32, 5.3), (16, 64, 3.75), (32, 128, 2.65), (64, 256, 1.87)]
COST = 0.0003
VOL_TARGET = 0.16


def forecast(px):
    sig = px.diff().ewm(span=35, min_periods=20).std()
    f = pd.DataFrame({f"{a}/{b}": ((px.ewm(span=a).mean() - px.ewm(span=b).mean()) / sig * s).clip(-20, 20)
                      for a, b, s in PAIRS})
    rho = f.dropna().corr().values
    w = np.full(len(PAIRS), 1 / len(PAIRS))
    fdm = 1 / np.sqrt(w @ rho @ w)
    return (f.mean(axis=1) * fdm).clip(-20, 20), fdm, f.abs().mean()


def run(px, pos, buffer=0.10):
    r = px.pct_change(fill_method=None)
    held, out, last = [], 0.0, None
    for p in pos.values:
        if np.isnan(p):
            p = 0.0
        if last is None or abs(p - last) > buffer:
            last = p
        held.append(last)
    held = pd.Series(held, index=pos.index)
    ret = held.shift(1) * r - held.diff().abs().fillna(held.abs()) * COST
    return ret.fillna(0), held


def stats(d):
    m = (1 + d).resample("ME").prod() - 1
    eq = (1 + d).cumprod()
    yr = (1 + d).groupby(d.index.year).prod() - 1
    return {"%/año": 100 * ((1 + d).prod() ** (252 / len(d)) - 1), "vol_%": 100 * d.std() * np.sqrt(252),
            "sharpe": d.mean() / d.std() * np.sqrt(252), "max_dd_%": 100 * (eq / eq.cummax() - 1).min(),
            "2008_%": 100 * yr.get(2008, np.nan), "2020_%": 100 * yr.get(2020, np.nan),
            "2022_%": 100 * yr.get(2022, np.nan), "exposición_media": np.nan}, m


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    px = yf.download(["RSP", "SPY"], start="2003-05-01", auto_adjust=True, progress=False)["Close"].dropna()
    rsp = px.RSP
    fc, fdm, mean_abs = forecast(rsp)
    vol = rsp.pct_change().ewm(span=35).std() * np.sqrt(252)
    lev = (VOL_TARGET / vol).clip(upper=2)
    variants = {
        "RSP fijo": pd.Series(1.0, index=rsp.index),
        "Tendencia, solo largo (máx. 1)": (fc / 10).clip(0, 1),
        "Tendencia, largo/corto (±1)": (fc / 10).clip(-1, 1),
        "Tendencia + vol. objetivo, solo largo (máx. 1)": (fc / 10 * lev).clip(0, 1),
        "Tendencia + vol. objetivo, largo/corto (±1)": (fc / 10 * lev).clip(-1, 1),
        "Tendencia, solo largo, con apalancamiento (máx. 2)": (fc / 10).clip(0, 2),
    }
    start = rsp.index[300]                                   # warm-up for the 256-day EMA
    rows, daily, held = [], {}, {}
    spy = px.SPY.pct_change().loc[start:]
    st, _ = stats(spy)
    rows.append({"variante": "SPY fijo (referencia)", **st, "exposición_media": 1.0})
    for name, pos in variants.items():
        d, h = run(rsp, pos.loc[start:])
        st, _ = stats(d)
        st["exposición_media"] = h.mean()
        st["operaciones/año"] = (h.diff().abs() > 0).sum() / (len(h) / 252)
        rows.append({"variante": name, **st})
        daily[name], held[name] = d, h
    res = pd.DataFrame(rows)
    sub = []
    for name, d in daily.items():                               # 2012-2026, the window of SYY / value
        s, _ = stats(d.loc["2012":])
        sub.append({"variante": name, "sharpe_2012_26": s["sharpe"], "max_dd_2012_26_%": s["max_dd_%"]})
    res = res.merge(pd.DataFrame(sub), on="variante", how="left")

    # monthly correlation with SYY and within-sector value (both dated by the HOLDING month)
    m = pd.DataFrame({k: (1 + v).resample("ME").prod() - 1 for k, v in daily.items()})
    syy = pd.read_csv(data.ROOT / "results" / "recent" / "pit" / "strategy_returns.csv", index_col=0, parse_dates=True)
    syy = syy["Top10 límite sectorial / SPY, neto Zero"]
    syy.index = syy.index + pd.offsets.MonthEnd(1)
    val = pd.read_csv(data.ROOT / "results" / "recent" / "value_sectorial" / "retornos.csv", index_col=0,
                      parse_dates=True)["largo 3 por sector / ETF"]
    val.index = val.index + pd.offsets.MonthEnd(1)
    m.index = m.index.normalize()
    res["corr_SYY"] = [m[k].corr(syy) for k in res.variante.where(res.variante.isin(m.columns), "RSP fijo")]
    res["corr_value"] = [m[k].corr(val) for k in res.variante.where(res.variante.isin(m.columns), "RSP fijo")]
    res.loc[res.variante.str.startswith("SPY"), ["corr_SYY", "corr_value"]] = np.nan
    res.to_csv(OUT / "resumen.csv", index=False, float_format="%.4f")
    pd.DataFrame(daily).to_csv(OUT / "retornos_diarios.csv", float_format="%.6f")
    pd.DataFrame(held).to_csv(OUT / "posiciones.csv", float_format="%.3f")
    pd.set_option("display.width", 260)
    print(f"FDM {fdm:.2f}; |forecast| medio por regla: {mean_abs.round(1).to_dict()}; |forecast| combinado "
          f"{fc.abs().mean():.1f}; forecast actual {fc.iloc[-1]:.1f} ({fc.index[-1].date()})")
    print(res.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
