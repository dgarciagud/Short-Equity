"""Flatten the Chen-Pelger-Zhu (2020) characteristic tensors into a long panel.

Each NPZ block (train 1967-86, valid 1987-91, test 1992-2016) holds
data[month, firm, var] with var[0] = 'ret'. Characteristics in a row are known at
that month-end and are cross-sectionally rank-normalised to [-0.5, 0.5]; 'ret' in
the same row is the return over the FOLLOWING month (verified: ST_REV[t] equals
the rank of ret[t-1]). Firm axes are persistent within a block only, so ids get
block offsets. Missing observations are coded -99.99.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.environ.get("CPZ_NPZ_DIR", ROOT / "external" / "cpz" / "datasets" / "char"))
OUT = ROOT / "data" / "cpz_panel.parquet"


def main():
    frames = []
    for k, split in enumerate(("train", "valid", "test")):
        with np.load(SRC / f"Char_{split}.npz") as a:
            dates, var, data = a["date"], [str(v) for v in a["variable"]], a["data"]
        t_idx, f_idx = np.nonzero(data[:, :, 0] != -99.99)
        df = pd.DataFrame(data[t_idx, f_idx], columns=var)
        df.insert(0, "firm", f_idx + k * 1_000_000)
        df.insert(0, "date", pd.to_datetime(dates[t_idx].astype(str), format="%Y%m%d"))
        frames.append(df)
        print(split, df.shape, df.date.min().date(), df.date.max().date(), file=sys.stderr)
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(OUT, index=False)
    print(out.shape)


if __name__ == "__main__":
    main()
