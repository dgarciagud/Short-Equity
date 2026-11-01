"""P&L attribution of the live Darwinex book: by sector and by factor (ETF proxies).

Positions: data/live/holdings.csv (real MT5 entries). Daily P&L of a position on day t =
shares x (P_t - P_{t-1}) with P_{entry day - 1} = entry price, so the totals match MT5.
Factors (daily returns of US ETFs, yfinance):
  mercado SPY; sector = sector SPDR net of its SPY beta; tamaño IWM - SPY; value IWD - IWF;
  momentum MTUM - SPY; calidad QUAL - SPY; baja vol. USMV - SPY.
Betas, 252 sessions before entry, in sequence (the style ETFs are collinear):
  1. market beta: OLS of the stock on SPY;
  2. sector: OLS of that residual on the sector ETF's own residual vs SPY;
  3. styles: ridge regression (RidgeCV) of the remaining residual on the five style spreads.
Contribution of factor k on day t = sum_i value_i,t-1 x beta_i,k x f_k,t (value < 0 for shorts);
the rest of each stock's P&L is its specific (idiosyncratic) part.
Usage: python attribution.py [end YYYY-MM-DD] [orders file with the trades about to be made]
"""
import sys

import numpy as np
import pandas as pd
import yfinance as yf

import data

LIVE = data.DATA / "live"
OUT = data.ROOT / "results" / "live"
SECTOR_ETF = {"Utilities": "XLU", "Consumer Staples": "XLP", "Health Care": "XLV", "Industrials": "XLI",
              "Materials": "XLB", "Financials": "XLF", "Consumer Discretionary": "XLY",
              "Information Technology": "XLK", "Energy": "XLE", "Real Estate": "XLRE",
              "Communication Services": "XLC"}
STYLE = {"tamaño": ("IWM", "SPY"), "value": ("IWD", "IWF"), "momentum": ("MTUM", "SPY"),
         "calidad": ("QUAL", "SPY"), "baja vol.": ("USMV", "SPY")}


def main(end=None):
    h = pd.read_csv(LIVE / "holdings.csv")
    h["fecha_entrada"] = pd.to_datetime(h.fecha_entrada)
    sectors = pd.read_csv(data.DATA / "sp500_current.csv").set_index("symbol").sector
    names = sorted(set(h.ticker) - {"SPY"})
    extra = sys.argv[2].split(",") if len(sys.argv) > 2 else []
    etfs = sorted({SECTOR_ETF[sectors[n]] for n in names + extra} | {"SPY", "IWM", "IWD", "IWF", "MTUM", "QUAL", "USMV"})
    px = yf.download(names + extra + etfs, start="2025-09-01", end=end, auto_adjust=False, progress=False)["Close"]
    r = px.pct_change(fill_method=None)
    F = pd.DataFrame({"mercado": r.SPY, **{k: r[a] - r[b] for k, (a, b) in STYLE.items()}})

    from sklearn.linear_model import RidgeCV
    styles = list(STYLE)
    sec_beta = {}

    def ols(y, x):
        x1 = np.column_stack([np.ones(len(x)), x])
        return np.linalg.lstsq(x1, y, rcond=None)[0][1:]

    def betas(n, until):
        sec = SECTOR_ETF[sectors[n]]
        W = pd.concat([r[[n, sec]], F], axis=1).loc[:until].iloc[-253:-1].dropna()
        bs = ols(W[sec].values, W[["mercado"]].values)[0]
        sec_beta[(sec, until)] = bs
        bm = ols(W[n].values, W[["mercado"]].values)[0]
        e1 = W[n] - bm * W.mercado
        srs = W[sec] - bs * W.mercado
        g = ols(e1.values, srs.values[:, None])[0]
        e2 = e1 - g * srs
        rg = RidgeCV(alphas=np.logspace(-6, -1, 30)).fit(W[styles].values, e2.values)
        return pd.Series({"mercado": bm, "sector": g, **dict(zip(styles, rg.coef_))}), sec

    rows, daily = [], []
    for _, p in h.iterrows():
        q = p.shares * (1 if p.ticker == "SPY" else -1)
        days = px.index[px.index >= p.fecha_entrada]
        prev = p.precio_entrada
        if p.ticker == "SPY":
            b, sec = pd.Series({"mercado": 1.0}), None
        else:
            b, sec = betas(p.ticker, p.fecha_entrada)
        for t in days:
            P = px.at[t, p.ticker]
            pnl = q * (P - prev)
            ret = P / prev - 1
            f = F.loc[t].copy()
            f["sector"] = r.at[t, sec] - sec_beta[(sec, p.fecha_entrada)] * r.at[t, "SPY"] if sec else 0.0
            contrib = {k: q * prev * b.get(k, 0.0) * f[k] for k in ["mercado", "sector", *STYLE]}
            sec_move = q * prev * (r.at[t, sec] if sec else r.at[t, "SPY"])
            daily.append({"fecha": t, "ticker": p.ticker, "sector_gics": sectors.get(p.ticker, "Cobertura (SPY)"),
                          "pnl": pnl, "mov_ETF_sector": sec_move, **contrib})
            prev = P
        rows.append((p.ticker, b))
    D = pd.DataFrame(daily)
    D["especifico_vs_sector"] = D.pnl - D.mov_ETF_sector
    fac = ["mercado", "sector", *STYLE]
    D["especifico_factores"] = D.pnl - D[fac].sum(axis=1)

    by_sector = D.groupby("sector_gics")[["pnl", "mov_ETF_sector", "especifico_vs_sector"]].sum().sort_values("pnl")
    by_factor = D[fac + ["especifico_factores"]].sum()
    by_stock = D.groupby("ticker")[["pnl"] + fac + ["especifico_factores"]].sum().sort_values("pnl")
    B = pd.DataFrame({t: b for t, b in rows if t != "SPY"}).T.reindex(columns=fac).round(2)

    # exposures of the book after the planned trades (latest close), in USD per 1 % factor move
    book = h.groupby("ticker").shares.sum()
    if len(sys.argv) > 2:
        o = pd.read_csv(OUT / f"holdings_tras_ordenes_{sys.argv[3]}.csv") if len(sys.argv) > 3 else None
        if o is not None:
            book = o.groupby("ticker").shares.sum()
    last = px.ffill().iloc[-1]
    expo = {}
    for n, sh in book.items():
        val = sh * last[n] * (1 if n == "SPY" else -1)
        b = pd.Series({"mercado": 1.0}) if n == "SPY" else betas(n, px.index[-1])[0]
        for k in fac:
            expo[k] = expo.get(k, 0.0) + val * b.get(k, 0.0) / 100
    sec_expo = {}
    for n, sh in book.items():
        if n != "SPY":
            sec_expo[sectors[n]] = sec_expo.get(sectors[n], 0.0) - sh * last[n]

    OUT.mkdir(parents=True, exist_ok=True)
    D.to_csv(OUT / "atribucion_diaria.csv", index=False, float_format="%.2f")
    pd.set_option("display.width", 220)
    print("== P&L por sector (USD)\n", by_sector.round(0).to_string())
    print("\n== P&L por factor (USD)\n", by_factor.round(0).to_string(), "\n total", round(D.pnl.sum()))
    print("\n== Por valor (USD)\n", by_stock.round(0).to_string())
    print("\n== Betas estimadas (año previo a la entrada)\n", B.to_string())
    print("\n== Exposición de la cartera tras las órdenes: USD por cada +1 % del factor\n",
          pd.Series(expo).round(0).to_string())
    print("\n== Exposición sectorial bruta en corto (USD)\n", pd.Series(sec_expo).round(0).sort_values().to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
