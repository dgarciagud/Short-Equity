"""Data loading: AlgoSeek S&P 500 bars (ML4T repo), Yahoo long sample, GICS
sectors, Fama-French factors (via ml4t-data) and a curated customer->supplier map."""
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
# clone of https://github.com/stefan-jansen/machine-learning-for-trading
ML4T_REPO = Path(os.environ.get("ML4T_REPO", ROOT / "external" / "machine-learning-for-trading"))
ALGOSEEK = ML4T_REPO / "data" / "equities" / "market" / "sp500" / "daily_bars.parquet"
SECTOR_ETFS = {"SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLC", "XLRE"}


class Panel:
    """Wide daily panels (dates x symbols) plus static sector labels."""

    def __init__(self, name, close, dollar_vol, sectors):
        self.name = name
        self.close = close
        self.ret = close.pct_change(fill_method=None)
        # a stock is "in the universe" on days where it has a price
        self.ret = self.ret.where(close.notna())
        self.dollar_vol = dollar_vol
        self.sectors = sectors.reindex(close.columns)
        keep = self.sectors.notna()
        self.close, self.ret = self.close.loc[:, keep], self.ret.loc[:, keep]
        self.dollar_vol = self.dollar_vol.loc[:, keep]
        self.sectors = self.sectors[keep]

    @property
    def dates(self):
        return self.close.index


def sector_labels():
    cur = pd.read_csv(DATA / "sp500_constituents_gics.csv").set_index("symbol").sector
    sup = pd.read_csv(DATA / "sector_map_supplement.csv").set_index("symbol").sector
    return pd.concat([cur, sup[~sup.index.isin(cur.index)]])


def load_algoseek():
    """Point-in-time S&P 500 members 2017-2021 (survivorship-bias free).

    adj_factor is a forward cumulative split+dividend factor, so close*adj_factor
    is a total-return price series."""
    d = pd.read_parquet(ALGOSEEK, columns=["date", "symbol", "close", "volume", "adj_factor"])
    d["date"] = pd.to_datetime(d.date)
    d["tr"] = d.close * d.adj_factor
    d["dv"] = d.close * d.volume
    close = d.pivot(index="date", columns="symbol", values="tr")
    dv = d.pivot(index="date", columns="symbol", values="dv")
    return Panel("AlgoSeek S&P500 PIT 2017-2021", close, dv, sector_labels())


def load_yahoo():
    """Current S&P 500 members 2004-2026 from Yahoo (survivorship-biased)."""
    d = pd.read_parquet(DATA / "yahoo_sp500_2005_2026.parquet")
    d["date"] = pd.to_datetime(d.date)
    d = d[~d.symbol.isin(SECTOR_ETFS)]
    d["dv"] = d.close * d.volume
    close = d.pivot(index="date", columns="symbol", values="close")
    # drop days with almost no data (holidays in the Yahoo grid)
    close = close[close.notna().sum(axis=1) > 0.5 * close.notna().sum(axis=1).median()]
    dv = d.pivot(index="date", columns="symbol", values="dv").reindex(close.index)
    return Panel("Yahoo S&P500 actual 2004-2026", close, dv, sector_labels())


def load_ff_daily():
    ff = pd.read_parquet(DATA / "ff" / "ff5_daily.parquet").set_index("timestamp")
    mom = pd.read_parquet(DATA / "ff" / "mom_daily.parquet").set_index("timestamp")
    out = ff.join(mom, how="inner")
    out.index = pd.to_datetime(out.index)
    return out


# Customer -> supplier links (customer accounts for a material share of supplier
# revenue according to 10-K "major customer" disclosures). Approximate and static:
# it is meant to illustrate Cohen & Frazzini (2008), not to be a full dataset.
CUSTOMER_SUPPLIER = {
    # autos: OEMs -> component suppliers
    "GM": ["APTV", "DLPH", "BWA", "GT"],
    "F": ["APTV", "DLPH", "BWA", "GT"],
    "TSLA": ["APTV"],
    # Apple -> component suppliers
    "AAPL": ["AVGO", "QCOM", "SWKS", "QRVO", "GLW", "JBL", "CRUS"],
    # PC OEMs / chipmakers -> chips & equipment
    "HPQ": ["INTC", "MU"],
    "DELL": ["INTC", "MU", "NVDA"],
    "INTC": ["AMAT", "LRCX", "KLAC"],
    "MU": ["AMAT", "LRCX", "KLAC"],
    # big retailers -> consumer staples / toys / household
    "WMT": ["PG", "CLX", "KMB", "GIS", "K", "CPB", "CAG", "SJM", "HSY", "HRL", "MKC",
            "CHD", "KHC", "HAS", "MAT", "NWL"],
    "TGT": ["HAS", "MAT", "CLX", "GIS"],
    "COST": ["KMB", "CLX"],
    # home improvement retailers -> building products
    "HD": ["MAS", "FBHS", "WHR", "SWK", "MHK"],
    "LOW": ["MAS", "WHR", "SWK", "MHK", "FBHS"],
    # Boeing / airlines -> aerospace suppliers
    "BA": ["HWM", "ARNC", "TDG", "COL", "HEI"],
    "DAL": ["BA"], "UAL": ["BA"], "AAL": ["BA"], "LUV": ["BA"], "ALK": ["BA"],
    # carriers -> towers
    "T": ["AMT", "CCI", "SBAC"], "VZ": ["AMT", "CCI", "SBAC"], "TMUS": ["AMT", "CCI", "SBAC"],
    # e-commerce -> parcel delivery
    "AMZN": ["UPS", "FDX"],
    # hyperscalers -> networking
    "MSFT": ["ANET", "NVDA"], "META": ["ANET", "NVDA"], "FB": ["ANET", "NVDA"],
    # drug wholesalers -> pharma
    "MCK": ["PFE", "MRK", "ABBV", "AMGN", "GILD", "BMY", "LLY", "BIIB", "REGN", "VRTX"],
    "CAH": ["PFE", "MRK", "ABBV", "AMGN", "GILD", "BMY", "LLY", "BIIB", "REGN", "VRTX"],
    "ABC": ["PFE", "MRK", "ABBV", "AMGN", "GILD", "BMY", "LLY", "BIIB", "REGN", "VRTX"],
    "COR": ["PFE", "MRK", "ABBV", "AMGN", "GILD", "BMY", "LLY", "BIIB", "REGN", "VRTX"],
}


def supplier_customers(symbols):
    """Map supplier -> list of its customers present in `symbols`."""
    syms = set(symbols)
    out = {}
    for cust, sups in CUSTOMER_SUPPLIER.items():
        if cust not in syms:
            continue
        for s in sups:
            if s in syms:
                out.setdefault(s, []).append(cust)
    return out


def rebalance_dates(dates, freq):
    """Last trading day of each month ('M') or week ('W')."""
    s = pd.Series(dates, index=dates)
    key = s.dt.to_period("M" if freq == "M" else "W-FRI")
    return pd.DatetimeIndex(s.groupby(key).max().values)


def period_factor_returns(ff_daily, rebal):
    """Compound daily FF factors over each holding period (t, t_next]."""
    lg = np.log1p(ff_daily).cumsum()
    lg = lg.reindex(lg.index.union(rebal)).ffill()
    lv = lg.loc[rebal]
    return np.expm1(lv.diff().shift(-1)).iloc[:-1]
