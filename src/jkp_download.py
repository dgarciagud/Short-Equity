"""Official Jensen-Kelly-Pedersen factor data from jkpfactors.com (public S3 bucket).

  data/jkp/themes_usa_<weight>.parquet   13 US theme returns, all stocks (vw_cap, ew)
  data/jkp/factors_usa_size.parquet      153 US factors inside the mega and large size groups
  data/jkp/cluster_labels.csv            factor -> theme and expected direction (bkelly-lab/
                                         ReplicationCrisis: Cluster Labels.csv, Factor Details.xlsx; in git)
The size-group files are raw high-minus-low tercile spreads: multiply by `direction` before
averaging into themes (kelly_jkp.py), as JKP do for their published theme series.
"""
import io
import sys
import zipfile

import pandas as pd
import requests

import data

S3 = "https://jkpfactors-data.s3.amazonaws.com/public"
OUT = data.DATA / "jkp"


def fetch(url):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    return pd.read_csv(z.open(z.namelist()[0]))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for w in ("vw_cap", "ew"):
        d = fetch(f"{S3}/%5Busa%5D_%5Ball_themes%5D_%5Bmonthly%5D_%5B{w}%5D.zip")
        d.to_parquet(OUT / f"themes_usa_{w}.parquet")
    lab = pd.read_csv(OUT / "cluster_labels.csv")
    parts = []
    for i, f in enumerate(lab.characteristic):
        for g in ("mega", "large"):
            parts.append(fetch(f"{S3}/factor/%5Busa%5D_%5B{f}%5D_%5B{g}%5D.zip"))
        if i % 25 == 0:
            print(f"  {i}/{len(lab)}", file=sys.stderr)
    pd.concat(parts).to_parquet(OUT / "factors_usa_size.parquet")


if __name__ == "__main__":
    main()
