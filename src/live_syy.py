"""Live Stambaugh-Yu-Yuan mispricing score and weekly Darwinex order list.

Same pipeline as the point-in-time backtest (pit_backtest.py, REPORT §12.b-c):
fundamentals from SEC companyfacts as filed (split-safe NI), prices from the ml4t-data
Yahoo provider. The per-company helpers (`fundamentals`, `shares_growth`) are a cross-check.

Universe: today's S&P 500 (Wikipedia) available as CFDs on Darwinex (MT5 export,
data/darwinex/spread_history.csv). Names with merger/tender filings are skipped.
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
       [--holdings data/live/holdings.csv] [--capital 1900] [--gross 1.0]
holdings.csv: columns `ticker,shares` with the open shorts and the SPY hedge (row SPY).
Weekly rule: up to --max-changes replacements; while the book has fewer than 10 shorts,
up to --build new names (default 4 the first week, then 3), SPY resized to the short total.
"""
import argparse
import io
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
    "cur_assets": ["AssetsCurrent"],
    "cur_liab": ["LiabilitiesCurrent"],
    "public_float": ["dei:EntityPublicFloat"],      # cover page of the 10-K, as of the last Q2 end
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
    ns = facts.get("facts", {})
    for key, names in CONCEPTS.items():
        for prio, name in enumerate(names):
            tax, name = name.split(":") if ":" in name else ("us-gaap", name)
            node = ns.get(tax, {}).get(name)
            if not node:
                continue
            unit = "shares" if key == "shares" else "USD"
            for f in node.get("units", {}).get(unit, []):
                if f.get("form", "").startswith(("10-K", "10-Q", "20-F", "40-F")):
                    rows.append((key, prio, f.get("start"), f["end"], float(f["val"]), f["filed"], f["form"]))
    return pd.DataFrame(rows, columns=["key", "prio", "start", "end", "val", "filed", "form"])


def download(tickers, cmap, max_age_days=6, force=False):
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
        if not force and not thin and time.time() - f.stat().st_mtime < max_age_days * 86400:
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
    # prefer the comparative restated in the same filing (split-adjusted), else the latest filing
    prev = prev.assign(same=prev.filed == c.filed).sort_values(["same", "filed"])
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


MNA_FORMS = {"DEFM14A", "PREM14A", "DEFM14C", "PREM14C", "SC 14D9", "SC TO-T", "SC 14D9/A", "SC TO-T/A", "425"}


def current_members():
    """Today's S&P 500 (symbol, name, GICS sector, CIK) from Wikipedia; cached copy as fallback."""
    cache = data.DATA / "sp500_current.csv"
    try:
        r = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                         headers={"User-Agent": "ShortEquityResearch/1.0 (research@example.org)"}, timeout=60)
        r.raise_for_status()
        t = pd.read_html(io.StringIO(r.text))[0]
        t = t.rename(columns={"Symbol": "symbol", "Security": "name", "GICS Sector": "sector", "CIK": "cik"})
        t[["symbol", "name", "sector", "cik"]].to_csv(cache, index=False)
    except (requests.RequestException, ValueError) as e:
        print(f"Wikipedia no disponible ({e}); uso {cache.name}", file=sys.stderr)
    return pd.read_csv(cache)


def mna_flags(ciks, since):
    """Merger / tender-offer filings (target side, or form 425) since `since`, per CIK."""
    s = requests.Session()
    s.headers["User-Agent"] = UA
    out = {}
    for c in ciks:
        try:
            j = s.get(f"https://data.sec.gov/submissions/CIK{int(c):010d}.json", timeout=60).json()
            f = j["filings"]["recent"]
            hits = sorted({fm for fm, d in zip(f["form"], f["filingDate"]) if fm in MNA_FORMS and d >= since})
            out[c] = ", ".join(hits)
        except (requests.RequestException, ValueError, KeyError):
            out[c] = "?"
        time.sleep(0.12)
    return out


def main():
    """Weekly order list with the SAME pipeline as the point-in-time backtest (pit_backtest.py):
    companyfacts as-filed fundamentals, split-safe NI, today's S&P 500 members that Darwinex
    offers as CFDs (MT5 export), ml4t-data Yahoo prices, 10 shorts (max 3 per sector) vs SPY."""
    import recent_backtest as rb
    from ml4t.data.providers.yahoo import YahooFinanceProvider

    ap = argparse.ArgumentParser()
    ap.add_argument("--asof", default=str(date.today()))
    ap.add_argument("--holdings", default=str(data.DATA / "live" / "holdings.csv"))
    ap.add_argument("--capital", type=float, default=1900.0, help="account equity")
    ap.add_argument("--currency", choices=["EUR", "USD"], default="EUR")
    ap.add_argument("--gross", type=float, default=1.0, help="short notional / equity (same for the SPY long)")
    ap.add_argument("--max-changes", type=int, default=3, help="max replacements per week")
    ap.add_argument("--build", type=int, default=None,
                    help="max new names into empty slots per week (default 4 the first week, then 3)")
    args = ap.parse_args()
    asof = pd.Timestamp(args.asof)
    stamp = asof.date().isoformat()
    LIVE.mkdir(parents=True, exist_ok=True)

    dx = pd.read_csv(data.DATA / "darwinex" / "spread_history.csv")
    st = dx[(dx.swap_mode == 5) & (dx.contract_size == 1)].set_index("symbol")
    eurusd = dx.set_index("symbol").last_price.get("EURUSD", 1.1)
    cap_usd = args.capital * (eurusd if args.currency == "EUR" else 1.0)
    sp = current_members()
    sp["mt5"] = sp.symbol.str.replace(".", "", regex=False)
    uni = sp[sp.mt5.isin(st.index)].copy()
    uni["avg_spread_bps"] = uni.mt5.map(st.avg_spread_bps)
    uni["cik"] = uni.cik.astype(int)
    print(f"S&P 500 hoy: {len(sp)}; disponibles en Darwinex: {len(uni)}", file=sys.stderr)

    cmap = dict(zip(uni.symbol, uni.cik))
    download(list(cmap), cmap)                                   # companyfacts, refreshed weekly
    rb.CF_UNIVERSE = [(t, c) for t, c in cmap.items() if (SEC / "facts" / f"{t}.parquet").exists()]
    tables = rb.feature_tables("companyfacts")
    f = rb.asof(tables, asof).replace([np.inf, -np.inf], np.nan)
    last_ann = pd.concat([tab[tab.ann <= asof].groupby("cik").ann.max() for tab, _ in tables.values()],
                         axis=1).max(axis=1)

    syms = [t.replace(".", "-") for t in uni.symbol] + ["SPY"]
    start = (asof - timedelta(days=430)).date().isoformat()
    end = (asof + timedelta(days=1)).date().isoformat()
    px = YahooFinanceProvider().fetch_batch_ohlcv(syms, start, end, chunk_size=50, delay_seconds=1.0)
    px = px.to_pandas().pivot(index="timestamp", columns="symbol", values="close")
    px.columns = [c.replace("-", ".") for c in px.columns]
    px = px[px.index <= asof]
    me = px.resample("ME").last()
    me = me[me.index < asof.to_period("M").to_timestamp()]          # completed months: t = me[-1]
    mom = me.iloc[-2] / me.iloc[-12] - 1                              # as in the backtest: t-1 / t-12

    df = uni.set_index("symbol")[["name", "sector", "mt5", "cik", "avg_spread_bps"]]
    df = df.join(f, on="cik")
    df["r12_2"] = mom.reindex(df.index)
    df["precio"] = px.ffill().iloc[-1].reindex(df.index)
    df["ultimo_informe"] = df.cik.map(last_ann).dt.date
    df = score(df)
    df.to_csv(LIVE / f"syy_score_{stamp}.csv", float_format="%.4f")

    cand = sector_capped(df, 30)
    flags = mna_flags(cand.cik, (asof - timedelta(days=180)).date().isoformat())
    cand = cand.assign(fusiones_SEC=cand.cik.map(flags))
    target = cap_usd * args.gross / N_SHORT
    cand["acciones"] = (target / cand.precio).round().clip(lower=1).astype(int)
    cand["nocional_usd"] = cand.acciones * cand.precio
    ok = (cand.precio <= 1.5 * target) & (cand.fusiones_SEC == "")
    book = cand[ok].head(N_SHORT)
    skipped = cand[~ok & (cand.M >= book.M.min())]

    # Current book: holdings.csv with columns ticker[,shares]; the SPY row is the hedge.
    hold_path = Path(args.holdings)
    hold = pd.read_csv(hold_path) if hold_path.exists() else pd.DataFrame(columns=["ticker", "shares"])
    if "shares" not in hold:
        hold["shares"] = np.nan
    hold["ticker"] = hold.ticker.astype(str).str.upper()
    spy_held = hold.loc[hold.ticker == "SPY", "shares"].sum()
    holdings = [t for t in hold.ticker if t != "SPY"]
    ranked = df.loc[[t for t in cand.index if ok[t]] + [t for t in df.index if t not in cand.index]]
    ranked = ranked.assign(rank_sobrevalorada=np.arange(1, len(ranked) + 1))
    out, new = trade_list(ranked, holdings, max_changes=args.max_changes)
    # Staggered build: replacements one-for-one, plus at most `build` names into empty slots.
    build = args.build if args.build is not None else (4 if not holdings else args.max_changes)
    empty = max(0, N_SHORT - len([h for h in holdings if h in df.index]))
    new = new[: len(out) + min(empty, build)]
    final = [h for h in holdings if h not in out] + new

    price = df.precio
    held_sh = hold.set_index("ticker").shares
    def notional(t):
        if t in new:
            return cand.nocional_usd.get(t, target)
        sh = held_sh.get(t, np.nan)
        return sh * price.get(t, np.nan) if pd.notna(sh) else target
    short_usd = sum(notional(t) for t in final)
    spy_px = px["SPY"].dropna().iloc[-1]
    spy_n = int(round(short_usd / spy_px))
    spy_trade = spy_n - (int(spy_held) if pd.notna(spy_held) else 0)
    if new and new[0] not in cand.index:      # opened from outside the sized candidate list
        cand = pd.concat([cand, df.loc[[t for t in new if t not in cand.index]]])
        cand["acciones"] = cand.acciones.fillna((target / cand.precio).round()).astype(int)
        cand["nocional_usd"] = cand.acciones * cand.precio
    after = pd.DataFrame({"ticker": final + ["SPY"],
                          "shares": [int(cand.acciones[t]) if t in new else held_sh.get(t, np.nan)
                                     for t in final] + [spy_n]})
    after.to_csv(LIVE / f"holdings_tras_ordenes_{stamp}.csv", index=False)

    cols = ["mt5", "name", "sector", "M", "n_anomalias", "precio", "acciones", "nocional_usd",
            "avg_spread_bps", "ultimo_informe", "fusiones_SEC"]
    with open(LIVE / f"syy_orders_{stamp}.md", "w") as fh:
        fh.write(f"# Órdenes SYY semana del {stamp} — Darwinex Zero\n\n")
        fh.write(f"Capital {args.capital:,.0f} {args.currency} (= {cap_usd:,.0f} USD), "
                 f"corto bruto {args.gross:.1f}× ⇒ objetivo {target:,.0f} USD por valor. Precios de cierre "
                 f"{px.index[-1].date()}; momentum hasta {me.index[-2].date()}.\n\n")
        fh.write(f"Universo: {len(df)} valores del S&P 500 disponibles en Darwinex, "
                 f"{df.M.notna().sum()} con puntuación.\n\n")
        fh.write("## Órdenes\n\n| Acción | Símbolo MT5 | Acciones | Precio ref. | Nocional USD |\n|---|---|---:|---:|---:|\n")
        for t in out:
            fh.write(f"| Cerrar corto (comprar) | {t.replace('.', '')} | posición actual | | |\n")
        for t in new:
            r = cand.loc[t]
            fh.write(f"| Abrir corto (vender) | {r.mt5} | {r.acciones} | {r.precio:.2f} | {r.nocional_usd:,.0f} |\n")
        if spy_trade:
            fh.write(f"| Cobertura: {'comprar' if spy_trade > 0 else 'vender'} SPY | SPY | {abs(spy_trade)} | "
                     f"{spy_px:.2f} | {abs(spy_trade) * spy_px:,.0f} |\n")
        fh.write(f"\nTras las órdenes: {len(final)} cortos por {short_usd:,.0f} USD frente a {spy_n} SPY "
                 f"({spy_n * spy_px:,.0f} USD).")
        if len(final) < N_SHORT:
            fh.write(f" Cartera en construcción: faltan {N_SHORT - len(final)} cortos, que entrarán en las "
                     f"próximas semanas con el ranking de cada semana.")
        fh.write(f"\n\nSi ejecutas todo tal cual, copia `results/live/holdings_tras_ordenes_{stamp}.csv` a "
                 f"`data/live/holdings.csv` (pon las acciones reales si difieren).\n\n")
        fh.write("## Cartera tras las órdenes\n\n")
        fh.write(df.reindex(final).assign(acciones=after.set_index("ticker").shares.reindex(final))
                 [[c for c in cols if c in df or c == "acciones"]].round(3).to_markdown() + "\n\n")
        if len(skipped):
            fh.write("## Descartados\n\nPrecio > 1,5× el objetivo por valor (1 acción pesa demasiado) o "
                     "presentación de fusión/OPA ante la SEC en los últimos 180 días:\n\n")
            fh.write(skipped[cols].round(3).to_markdown() + "\n\n")
        fh.write("## Siguientes en el ranking (suplentes y candidatos de las próximas semanas)\n\n")
        fh.write(cand[ok & ~cand.index.isin(final)].head(10)[cols].round(3).to_markdown() + "\n")
    print(open(LIVE / f"syy_orders_{stamp}.md").read())


if __name__ == "__main__":
    main()
