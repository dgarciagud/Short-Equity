"""Split-adjusted but NOT dividend-adjusted daily closes (yfinance auto_adjust=False) for every
historical S&P 500 member since 2011. Needed for market value = shares x price: the ml4t-data
Yahoo provider returns total-return-adjusted closes, which understate past prices of dividend
payers. Share counts are taken as restated in the latest filing, i.e. on today's split basis."""
import json
import sys
import time

import pandas as pd
import yfinance as yf

import data

OUT = data.DATA / "close_sp500_pit.parquet"


def main(start="2010-01-01"):
    tick = sorted({t.replace(".", "-") for t in json.loads((data.DATA / "sp500_hist_cik.json").read_text())})
    parts = []
    for i in range(0, len(tick), 50):
        chunk = tick[i:i + 50]
        for attempt in range(3):
            try:
                d = yf.download(chunk, start=start, auto_adjust=False, progress=False, threads=True)["Close"]
                parts.append(d)
                break
            except Exception as e:                      # rate limits: back off and retry
                print(f"  reintento {chunk[0]}: {e}", file=sys.stderr)
                time.sleep(10 * (attempt + 1))
        time.sleep(1)
    px = pd.concat(parts, axis=1)
    px = px.loc[:, px.notna().any()]
    px.columns = [c.replace("-", ".") for c in px.columns]
    px.to_parquet(OUT)
    print(px.shape, px.index.min(), px.index.max(), file=sys.stderr)


if __name__ == "__main__":
    main()
