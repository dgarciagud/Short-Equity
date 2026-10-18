"""Daily adjusted closes for every historical S&P 500 member since 2011 (ml4t-data Yahoo provider).

Yahoo keeps history for many renamed/acquired tickers but not all; coverage is
reported by pit_backtest.py. Recycled tickers (now another company) are dropped there.
"""
import json
import sys

import pandas as pd
from ml4t.data.providers.yahoo import YahooFinanceProvider

import data

OUT = data.DATA / "prices_sp500_pit.parquet"


def main(start="2010-01-01", end=None):
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    tick = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    syms = sorted({t.replace(".", "-") for t in tick} | {"SPY"})
    df = YahooFinanceProvider().fetch_batch_ohlcv(syms, start, end, chunk_size=50, delay_seconds=1.0)
    px = df.to_pandas().pivot(index="timestamp", columns="symbol", values="close")
    px.columns = [c.replace("-", ".") for c in px.columns]
    px.to_parquet(OUT)
    print(px.shape, px.index.min(), px.index.max(), file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])
