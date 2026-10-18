"""Point-in-time XBRL fundamentals built with the ML4T repository's SEC downloader.

Reuses data/equities/fundamentals/xbrl_download.py from
stefan-jansen/machine-learning-for-trading:
  * `_build_fundamentals`  - Frames API grid (instant + quarterly duration concepts)
  * `_fetch_xbrl_frame`    - single frame fetch (used for annual frames and the
                             share-count concept, which is in 'shares', not USD)
  * `_add_filing_dates`    - Submissions API; a row is dated by the filing of the
                             LAST of its facts (conservative, no look-ahead)
  * `_finalize`            - canonical schema
Panels written to data/sec/frames/:
  instant.parquet   balance-sheet items per (cik, quarter)
  quarterly.parquet net income per quarter (3-month frames)
  shares.parquet    diluted weighted-average shares per quarter
  annual.parquet    net income, operating cash flow, gross profit, revenue, cost of revenue
Each panel is dated independently, so a late comparative in one panel does not
delay the others.
"""
import importlib.util
import os
import sys
import time

import pandas as pd
import polars as pl

import data

OUT = data.DATA / "sec" / "frames"
UA = os.environ.get("SEC_USER_AGENT", "ShortEquityResearch research@example.org")

INSTANT = ["Assets", "Liabilities", "LiabilitiesAndStockholdersEquity", "StockholdersEquity",
           "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
           "CashAndCashEquivalentsAtCarryingValue",
           "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
           "ShortTermInvestments", "MarketableSecuritiesCurrent",
           "LongTermDebtNoncurrent", "LongTermDebt", "DebtCurrent", "LongTermDebtCurrent",
           "ShortTermBorrowings", "PropertyPlantAndEquipmentNet", "InventoryNet"]
QUARTERLY = ["NetIncomeLoss", "ProfitLoss"]
ANNUAL = ["NetIncomeLoss", "ProfitLoss", "NetCashProvidedByUsedInOperatingActivities",
          "GrossProfit", "Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
          "CostOfRevenue", "CostOfGoodsAndServicesSold"]
SHARES = "WeightedAverageNumberOfDilutedSharesOutstanding"


def repo_module():
    root = data.ML4T_REPO
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location(
        "ml4t_xbrl", root / "data" / "equities" / "fundamentals" / "xbrl_download.py")
    xb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(xb)
    xb.HEADERS = {"User-Agent": UA}   # identify ourselves to the SEC, not the book author
    return xb


def grid(xb, ciks, concepts, unit, periods):
    """Same record logic as the repo's `_build_fundamentals`, for arbitrary periods/units."""
    records = {}
    for period in periods:
        for concept in concepts:
            rows = xb._fetch_xbrl_frame("us-gaap", concept, unit, period)
            time.sleep(xb.RATE_LIMIT_S)
            for r in rows or []:
                if r.get("cik") not in ciks:
                    continue
                key = (r["cik"], r.get("end"))
                rec = records.setdefault(key, {"cik": r["cik"], "entity_name": r.get("entityName"),
                                               "period_end": r.get("end"), "start": r.get("start"),
                                               "accessions": set()})
                if r.get("accn"):
                    rec["accessions"].add(r["accn"])
                rec[concept.lower()] = r.get("val")
        print(f"  {period}: {len(records)} records", file=sys.stderr)
    rows = [{**rec, "accessions": sorted(rec["accessions"])} for rec in records.values()]
    return pl.DataFrame(rows) if rows else pl.DataFrame()


def build(ciks_to_ticker, years, out=OUT):
    xb = repo_module()
    out.mkdir(parents=True, exist_ok=True)
    cache = OUT / "filing_dates"            # shared accession -> filing-date cache
    ciks = set(ciks_to_ticker)
    q_periods = [f"CY{y}Q{q}" for y in years for q in range(1, 5)]
    jobs = {
        "instant": lambda: xb._build_fundamentals(ciks, INSTANT, [], years),
        "quarterly": lambda: xb._build_fundamentals(ciks, [], QUARTERLY, years),
        "shares": lambda: grid(xb, ciks, [SHARES], "shares", q_periods),
        "annual": lambda: grid(xb, ciks, ANNUAL, "USD", [f"CY{y}" for y in years]),
    }
    for name, fn in jobs.items():
        path = out / f"{name}.parquet"
        print(f"== {name}", file=sys.stderr)
        df = fn()
        if "start" in df.columns:
            df = df.drop("start")
        df = xb._finalize(xb._add_filing_dates(df, cache), ciks_to_ticker)
        df.write_parquet(path)
        print(f"   -> {path.name}: {df.height} rows", file=sys.stderr)


def universe():
    """S&P 500 stocks available as Darwinex CFDs, with SEC CIKs."""
    dx = pd.read_csv(data.DATA / "darwinex" / "spread_history.csv")
    sp = pd.read_csv(data.DATA / "sp500_constituents_gics.csv")
    sp["mt5"] = sp.symbol.str.replace(".", "", regex=False)
    st = dx[(dx.swap_mode == 5) & (dx.contract_size == 1)]
    uni = sp[sp.mt5.isin(st.symbol)].merge(
        st[["symbol", "avg_spread_bps"]].rename(columns={"symbol": "mt5"}), on="mt5")
    from live_syy import cik_map              # SEC company_tickers.json (cached weekly)
    uni["cik"] = uni.symbol.map(cik_map())
    return uni.dropna(subset=["cik"]).astype({"cik": int})


if __name__ == "__main__":
    uni = universe()
    print(f"Universe: {len(uni)} stocks", file=sys.stderr)
    build(dict(zip(uni.cik, uni.symbol)), list(range(2010, 2027)))
