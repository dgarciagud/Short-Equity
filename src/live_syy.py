"""Live Stambaugh-Yu-Yuan mispricing score from SEC XBRL (companyfacts) + prices.

Universe: S&P 500 stocks available as CFDs on Darwinex (data/darwinex/spread_history.csv).
For each company only facts FILED on or before --asof are used (no look-ahead);
for a given period the most recently filed value is taken (restated / split-adjusted).

8 anomalies (high percentile = overpriced), as in the CPZ backtest:
  NI   net stock issues      log(diluted shares, latest period / same period a year earlier)
  AC   accruals              (net income TTM - operating cash flow TTM) / average assets
  NOA  net operating assets  ((assets - cash) - (liabilities - debt)) / assets a year earlier
  r12_2 momentum             return t-12 -> t-1 months (low = overpriced)
  PROF gross profitability   gross profit TTM / assets (low = overpriced)
  AG   asset growth          assets / assets a year earlier - 1
  ROA  return on assets      net income TTM / assets a year earlier (low = overpriced)
  DPI2A investment-to-assets (change in PP&E + change in inventory) / assets a year earlier
M = mean of the available percentiles (at least 5 of 8 required).

Usage:
  SEC_USER_AGENT="Your Name your@email" python src/live_syy.py [--asof YYYY-MM-DD]
       [--holdings data/live/holdings.csv]
"""
import argparse
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import data

SEC = data.DATA / "sec"
LIVE = data.ROOT / "results" / "live"
UA = os.environ.get("SEC_USER_AGENT", "ShortEquityResearch research@example.org")
N_SHORT, N_BACKUP = 10, 10

CONCEPTS = {
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "liab_equity": ["LiabilitiesAndStockholdersEquity"],
    "equity": ["StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
               "StockholdersEquity"],
    "cash": ["CashAndCashEquivalentsAtCarryingValue",
             "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents", "Cash"],
    "st_invest": ["ShortTermInvestments", "MarketableSecuritiesCurrent",
                  "AvailableForSaleSecuritiesDebtSecuritiesCurrent"],
    "lt_debt": ["LongTermDebtNoncurrent", "LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"],
    "st_debt": ["DebtCurrent", "LongTermDebtCurrent", "ShortTermBorrowings", "CommercialPaper"],
    "ppe": ["PropertyPlantAndEquipmentNet",
            "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization"],
    "inventory": ["InventoryNet", "InventoryGross"],
    "net_income": ["NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "gross_profit": ["GrossProfit"],
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
                "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"],
    "cogs": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
    "shares": ["WeightedAverageNumberOfDilutedSharesOutstanding"],
}
FLOW = {"net_income", "cfo", "gross_profit", "revenue", "cogs", "shares"}


# ---------------------------------------------------------------- download ----
def cik_map():
    f = SEC / "company_tickers.json"
    if not f.exists() or time.time() - f.stat().st_mtime > 7 * 86400:
        r = requests.get("https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": UA}, timeout=60)
        r.raise_for_status()
        f.write_text(r.text)
    d = json.loads(f.read_text())
    return {v["ticker"].upper().replace("-", "."): int(v["cik_str"]) for v in d.values()}


def extract(facts):
    """Keep only the concepts we need: rows (key, start, end, val, filed, form)."""
    rows = []
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for key, names in CONCEPTS.items():
        for prio, name in enumerate(names):
            node = gaap.get(name)
            if not node:
                continue
            unit = "shares" if key == "shares" else "USD"
            for f in node.get("units", {}).get(unit, []):
                if f.get("form", "").startswith(("10-K", "10-Q", "20-F", "40-F")):
                    rows.append((key, prio, f.get("start"), f["end"], f["val"], f["filed"], f["form"]))
    return pd.DataFrame(rows, columns=["key", "prio", "start", "end", "val", "filed", "form"])


def download(tickers, cmap, max_age_days=6):
    out = SEC / "facts"
    out.mkdir(parents=True, exist_ok=True)
    s = requests.Session()
    s.headers["User-Agent"] = UA
    missing = []
    for i, t in enumerate(tickers):
        cik = cmap.get(t)
        if cik is None:
            missing.append(t)
            continue
        f = out / f"{t}.parquet"
        old = pd.read_parquet(f) if f.exists() else None
        thin = old is None or (old.key == "assets").sum() < 8
        if not thin and time.time() - f.stat().st_mtime < max_age_days * 86400:
            continue
        for attempt in range(4):
            try:
                r = s.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", timeout=60)
                if r.status_code == 200:
                    new = extract(r.json())
                    # companyfacts responses are occasionally partial: never lose facts
                    if old is not None:
                        new = pd.concat([old, new]).drop_duplicates(
                            ["key", "prio", "start", "end", "val", "filed", "form"])
                    new.to_parquet(f, index=False)
                    break
                time.sleep(2 ** attempt)
            except requests.RequestException:
                time.sleep(2 ** attempt)
        time.sleep(0.12)  # SEC fair-access limit: 10 requests/second
        if i % 50 == 0:
            print(f"  SEC {i}/{len(tickers)}", file=sys.stderr)
    return missing


# ------------------------------------------------------------ fundamentals ----
def latest_by_period(df, asof):
    """Facts known at `asof`; per (key, start, end) keep the latest filing and best tag."""
    d = df[pd.to_datetime(df.filed) <= asof].copy()
    if d.empty:
        return d
    d["end"] = pd.to_datetime(d.end)
    d["start"] = pd.to_datetime(d.start)
    d["filed"] = pd.to_datetime(d.filed)
    d = d.sort_values(["key", "prio", "filed"])
    best = d.groupby("key").prio.transform("min")      # most preferred tag that exists
    d = d[d.prio == best]
    return d.drop_duplicates(["key", "start", "end"], keep="last")


def instant(d, key, when, tol=45):
    x = d[(d.key == key)]
    if x.empty:
        return np.nan
    x = x.assign(gap=(x.end - when).abs().dt.days)
    x = x[x.gap <= tol]
    return x.sort_values("gap").val.iloc[0] if len(x) else np.nan


def ttm(d, key, end):
    """Trailing-12-month value of a flow ending at `end` (uses annual + YTD logic)."""
    x = d[(d.key == key) & d.start.notna()].copy()
    if x.empty:
        return np.nan
    x["days"] = (x.end - x.start).dt.days
    cur = x[(x.end - end).abs().dt.days <= 10]
    if cur.empty:
        return np.nan
    ann = cur[(cur.days > 350) & (cur.days < 380)]
    if len(ann):
        return ann.val.iloc[-1]
    ytd = cur.sort_values("days").iloc[-1]
    prev = x[((x.end - (end - pd.Timedelta(days=365))).abs().dt.days <= 15)
             & ((x.days - ytd.days).abs() <= 15)]
    fy = x[(x.days > 350) & (x.days < 380) & ((x.end - (ytd.start - pd.Timedelta(days=1))).abs().dt.days <= 15)]
    if prev.empty or fy.empty:
        return np.nan
    return fy.val.iloc[-1] + ytd.val - prev.val.iloc[-1]


def shares_growth(d, end):
    x = d[(d.key == "shares") & d.start.notna()].copy()
    if x.empty:
        return np.nan
    x["days"] = (x.end - x.start).dt.days
    cur = x[(x.end - end).abs().dt.days <= 10].sort_values("days")
    if cur.empty:
        return np.nan
    c = cur.iloc[0]
    prev = x[((x.end - (end - pd.Timedelta(days=365))).abs().dt.days <= 15) & ((x.days - c.days).abs() <= 15)]
    if prev.empty or c.val <= 0 or prev.val.iloc[-1] <= 0:
        return np.nan
    return np.log(c.val / prev.val.iloc[-1])


def fundamentals(ticker, asof):
    f = SEC / "facts" / f"{ticker}.parquet"
    if not f.exists():
        return None
    d = latest_by_period(pd.read_parquet(f), asof)
    a = d[d.key == "assets"]
    if a.empty:
        return None
    end = a.end.max()                               # latest balance-sheet date known
    last_filed = d[d.end == end].filed.max()
    yago = end - pd.Timedelta(days=365)
    A, A1 = instant(d, "assets", end), instant(d, "assets", yago)
    L = instant(d, "liabilities", end)
    if np.isnan(L):
        L = instant(d, "liab_equity", end) - instant(d, "equity", end)
    cash = np.nansum([instant(d, "cash", end), instant(d, "st_invest", end)])
    debt = np.nansum([instant(d, "lt_debt", end), instant(d, "st_debt", end)])
    ni, cfo = ttm(d, "net_income", end), ttm(d, "cfo", end)
    gp = ttm(d, "gross_profit", end)
    if np.isnan(gp):
        gp = ttm(d, "revenue", end) - ttm(d, "cogs", end)
    ppe, ppe1 = instant(d, "ppe", end), instant(d, "ppe", yago)
    inv, inv1 = instant(d, "inventory", end), instant(d, "inventory", yago)
    dinv = (inv - inv1) if not (np.isnan(inv) and np.isnan(inv1)) else 0.0
    dinv = 0.0 if np.isnan(dinv) else dinv
    out = {"ticker": ticker, "periodo": end.date(), "presentado": last_filed.date(),
           "NI": shares_growth(d, end),
           "AC": (ni - cfo) / np.nanmean([A, A1]) if A > 0 else np.nan,
           "NOA": ((A - cash) - (L - debt)) / A1 if A1 > 0 else np.nan,
           "PROF": gp / A if A > 0 else np.nan,
           "AG": A / A1 - 1 if A1 > 0 else np.nan,
           "ROA": ni / A1 if A1 > 0 else np.nan,
           "DPI2A": ((ppe - ppe1) + dinv) / A1 if A1 > 0 and not np.isnan(ppe - ppe1) else np.nan}
    return out


# ------------------------------------------------------------------ prices ----
def momentum(tickers, asof):
    import yfinance as yf
    syms = [t.replace(".", "-") for t in tickers]
    px = yf.download(syms, start=asof - timedelta(days=420), end=asof + timedelta(days=1),
                     auto_adjust=True, progress=False, threads=False)["Close"]
    px.columns = [c.replace("-", ".") for c in px.columns]
    px = px.ffill()
    me = px.resample("ME").last()
    me = me[me.index <= pd.Timestamp(asof)]
    # 12-1: from 12 month-ends ago to 1 month-end ago (skip the most recent month)
    r12_2 = me.iloc[-2] / me.iloc[-13] - 1 if len(me) >= 13 else pd.Series(np.nan, index=px.columns)
    return r12_2.rename("r12_2"), px.iloc[-1].rename("precio")


# ------------------------------------------------------------------- score ----
SIGN = {"NI": 1, "AC": 1, "NOA": 1, "r12_2": -1, "PROF": -1, "AG": 1, "ROA": -1, "DPI2A": 1}


def score(df):
    pct = pd.DataFrame({k: (df[k] * s).rank(pct=True) for k, s in SIGN.items()})
    df["n_anomalias"] = pct.notna().sum(axis=1)
    df["M"] = pct.mean(axis=1).where(df.n_anomalias >= 5)
    for k in SIGN:
        df["pct_" + k] = pct[k]
    df["rank_sobrevalorada"] = df.M.rank(ascending=False, method="first")
    df["rank_infravalorada"] = df.M.rank(ascending=True, method="first")
    return df.sort_values("M", ascending=False)


def sector_capped(df, n, cap=3):
    """Top-n most overpriced with at most `cap` names per GICS sector."""
    picked, count = [], {}
    for t, row in df[df.M.notna()].sort_values("M", ascending=False).iterrows():
        if count.get(row.sector, 0) < cap:
            picked.append(t)
            count[row.sector] = count.get(row.sector, 0) + 1
        if len(picked) == n:
            break
    return df.loc[picked]


def trade_list(df, holdings, n=N_SHORT, max_changes=3):
    """Weekly rule (no buffer, as in the backtest): hold the top n; replace at most
    `max_changes` names per week, worst-ranked first."""
    held = [h for h in holdings if h in df.index]
    rk = df.rank_sobrevalorada
    out = sorted([h for h in held if rk[h] > n], key=lambda h: -rk[h])
    gone = [h for h in holdings if h not in df.index]
    out = gone + out[: max(0, max_changes - len(gone))]
    keep = [h for h in holdings if h not in out]
    new = [t for t in rk.sort_values().index if t not in keep][: n - len(keep)]
    return out, new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=str(date.today()))
    ap.add_argument("--holdings", default=str(data.DATA / "live" / "holdings.csv"))
    args = ap.parse_args()
    asof = pd.Timestamp(args.asof)
    SEC.mkdir(parents=True, exist_ok=True)
    LIVE.mkdir(parents=True, exist_ok=True)

    dx = pd.read_csv(data.DATA / "darwinex" / "spread_history.csv")
    sp = pd.read_csv(data.DATA / "sp500_constituents_gics.csv")
    sp["mt5"] = sp.symbol.str.replace(".", "", regex=False)
    stocks = dx[(dx.swap_mode == 5) & (dx.contract_size == 1)]
    uni = sp[sp.mt5.isin(stocks.symbol)].copy()
    uni = uni.merge(stocks[["symbol", "avg_spread_bps", "last_price"]].rename(columns={"symbol": "mt5"}), on="mt5")
    tickers = uni.symbol.tolist()
    print(f"Universo: {len(tickers)} acciones S&P 500 disponibles en Darwinex", file=sys.stderr)

    cmap = cik_map()
    missing = download(tickers, cmap)
    rows = [r for t in tickers if (r := fundamentals(t, asof)) is not None]
    f = pd.DataFrame(rows).set_index("ticker")
    r12, last = momentum(tickers, asof)
    df = uni.set_index("symbol")[["name", "sector", "mt5", "avg_spread_bps"]].join(f).join(r12).join(last)
    df = score(df)
    df["dias_desde_presentacion"] = (asof - pd.to_datetime(df.presentado)).dt.days
    df["meses_desde_cierre"] = ((asof - pd.to_datetime(df.periodo)).dt.days / 30.4).round(1)
    stamp = asof.date().isoformat()
    df.to_csv(LIVE / f"syy_score_{stamp}.csv", float_format="%.4f")

    shorts = df[df.rank_sobrevalorada <= N_SHORT + N_BACKUP]
    longs = df.sort_values("M").head(N_SHORT)
    hold_path = Path(args.holdings)
    holdings = pd.read_csv(hold_path).ticker.tolist() if hold_path.exists() else []
    out, new = trade_list(df, holdings)
    cols = ["mt5", "name", "sector", "M", "n_anomalias", "precio", "avg_spread_bps", "r12_2",
            "periodo", "presentado", "meses_desde_cierre"]
    capped = sector_capped(df, N_SHORT + N_BACKUP)
    with open(LIVE / f"syy_orders_{stamp}.md", "w") as fh:
        fh.write(f"# Puntuación SYY a {stamp}\n\n")
        fh.write(f"Universo: {len(df)} acciones ({df.M.notna().sum()} con puntuación). "
                 f"Sin CIK en la SEC: {', '.join(missing) or 'ninguna'}.\n\n")
        fh.write("## Cortos: 10 más sobrevaloradas (y 10 suplentes por si no se pueden cortar)\n\n")
        fh.write(shorts[cols].round(3).to_markdown() + "\n\n")
        fh.write("## Cortos con límite de 3 por sector (recomendado: evita apostar a un sector)\n\n")
        fh.write(capped[cols].round(3).to_markdown() + "\n\n")
        fh.write("## Largos alternativos: 10 más infravaloradas (si no se cubre con SPY)\n\n")
        fh.write(longs[cols].round(3).to_markdown() + "\n\n")
        if holdings:
            fh.write(f"## Órdenes de esta semana (cartera actual: {', '.join(holdings)})\n\n")
            fh.write(f"* Cerrar cortos: {', '.join(out) or 'ninguno'}\n")
            fh.write(f"* Abrir cortos: {', '.join(new) or 'ninguno'}\n")
    print(df[cols].head(N_SHORT + N_BACKUP).round(3).to_string())
    print(f"\nEscrito: results/live/syy_score_{stamp}.csv y syy_orders_{stamp}.md", file=sys.stderr)


if __name__ == "__main__":
    main()
