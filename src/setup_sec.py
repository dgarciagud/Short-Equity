"""SEC companyfacts (as filed) for every historical S&P 500 member since 2011 and today's
Darwinex universe, plus SIC codes (sector fallback). Cached in data/sec/ (not in git)."""
import json
import sys
import time

import requests

import data
from live_syy import SEC, UA, download
from repo_xbrl import universe


def main():
    m = json.loads((data.DATA / "sp500_hist_cik.json").read_text())
    u = universe()
    cmap = {**m, **dict(zip(u.symbol, u.cik))}
    rep = {}
    for t, c in sorted(cmap.items()):          # one facts file per CIK
        if c not in rep.values():
            rep[t] = c
    for t, c in zip(u.symbol, u.cik):          # live scripts look facts up by today's ticker
        rep.setdefault(t, c)
    print(f"companyfacts: {len(rep)} ficheros", file=sys.stderr)
    download(list(rep), rep, max_age_days=3650)
    sic, s = {}, requests.Session()
    s.headers["User-Agent"] = UA
    for c in sorted(set(cmap.values())):
        r = s.get(f"https://data.sec.gov/submissions/CIK{c:010d}.json", timeout=60)
        if r.status_code == 200:
            j = r.json()
            sic[c] = (j.get("sic"), j.get("sicDescription"), j.get("name"))
        time.sleep(0.12)
    (SEC / "sic.json").write_text(json.dumps(sic))
    print(f"SIC: {len(sic)}", file=sys.stderr)


if __name__ == "__main__":
    main()
