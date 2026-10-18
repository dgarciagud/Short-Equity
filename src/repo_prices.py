"""Daily adjusted closes for the Darwinex S&P 500 universe + SPY via ml4t-data's Yahoo provider."""
import sys

import pandas as pd
from ml4t.data.providers.yahoo import YahooFinanceProvider

import data
from repo_xbrl import universe

OUT = data.DATA / "prices_darwinex_universe.parquet"


def main(start="2010-01-01", end=None):
    end = end or pd.Timestamp.today().strftime("%Y-%m-%d")
    syms = [s.replace(".", "-") for s in universe().symbol] + ["SPY"]
    df = YahooFinanceProvider().fetch_batch_ohlcv(syms, start, end, chunk_size=50, delay_seconds=1.0)
    px = df.to_pandas().pivot(index="timestamp", columns="symbol", values="close")
    px.columns = [c.replace("-", ".") for c in px.columns]
    px.to_parquet(OUT)
    print(px.shape, px.index.min(), px.index.max(), file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])
