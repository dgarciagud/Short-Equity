"""Download daily prices (Yahoo Finance, the provider used by ml4t-data) for the
current S&P 500 constituents, SPY and the SPDR sector ETFs.

The sample is survivorship-biased (only today's members); it complements the
point-in-time AlgoSeek S&P 500 bars shipped with the ML4T repository.
"""
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "yahoo_sp500_2005_2026.parquet"
ETFS = ["SPY", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "XLC", "XLRE"]


def main(start="2004-01-01", end="2026-10-01"):
    cons = pd.read_csv(ROOT / "data" / "sp500_constituents_gics.csv")
    tickers = [s.replace(".", "-") for s in cons.symbol] + ETFS
    frames = []
    for i in range(0, len(tickers), 50):
        batch = tickers[i : i + 50]
        px = yf.download(batch, start=start, end=end, auto_adjust=True,
                         progress=False, threads=False, group_by="column")
        frames.append(px[["Close", "Volume"]].stack(level=1, future_stack=True)
                      .rename_axis(["date", "symbol"]).reset_index())
        print(f"{i + len(batch)}/{len(tickers)}", file=sys.stderr)
    df = pd.concat(frames).dropna(subset=["Close"])
    df.columns = ["date", "symbol", "close", "volume"]
    df["symbol"] = df.symbol.str.replace("-", ".")
    df.to_parquet(OUT, index=False)
    print(df.shape, df.symbol.nunique())


if __name__ == "__main__":
    main()
