#!/usr/bin/env python3
"""NICER event_cl refetch: for each of the 20 ObsIDs, list the HEASARC
event_cl directory (year from the file index), download the cleaned
event file(s), verify gzip+FITS magic, store under
data/raw/nicer/MAXI_J1820+070/<obsid>/xti/event_cl/ and append to the
file index. Fail-closed: any non-FITS download is recorded as FAILED."""
import csv
import gzip
import os
import sys
import time
from pathlib import Path

import urllib.request

ROOT = Path("/home/error/SSZ-Spectroscopy-Bridge")
ART = ROOT / "artifacts"
RAW = ROOT / "data/raw/nicer/MAXI_J1820+070"
INDEX = ART / "NICER_MAXI_J1820_FILE_INDEX_V1.csv"
BASE = "https://heasarc.gsfc.nasa.gov/FTP/nicer/data/obs"

def year_of(obsid):
    with open(INDEX) as f:
        for row in csv.DictReader(f):
            if row["obsid"] == obsid and row["remote_url"]:
                parts = row["remote_url"].split("/")
                i = parts.index("obs")
                return parts[i + 1]
    return None

def is_gzip(p):
    with open(p, "rb") as f:
        return f.read(2) == b"\x1f\x8b"

def is_fits(p):
    with gzip.open(p, "rb") as f:
        return f.read(6) == b"SIMPLE"

def http_get(url, dest, max_try=3):
    for a in range(max_try):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ssz-bridge/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            return True
        except Exception as e:
            if a == max_try - 1:
                print(f"    FAIL {url}: {e}")
                return False
            time.sleep(2 ** a)
    return False

def main():
    obsids = sorted(p.name for p in RAW.iterdir() if p.is_dir())
    print(f"{len(obsids)} ObsIDs")
    ok = fail = 0
    for obsid in obsids:
        year = year_of(obsid)
        if not year:
            print(f"{obsid}: no year mapping — SKIP")
            fail += 1
            continue
        listing_url = f"{BASE}/{year}/{obsid}/xti/event_cl/"
        try:
            html = urllib.request.urlopen(listing_url, timeout=60).read().decode()
        except Exception as e:
            print(f"{obsid}: listing FAIL {e}")
            fail += 1
            continue
        import re
        files = re.findall(r'href="(ni[^"]+_cl\.evt\.gz)"', html)
        if not files:
            print(f"{obsid}: no _cl.evt.gz in listing")
            fail += 1
            continue
        dest_dir = RAW / obsid / "xti" / "event_cl"
        dest_dir.mkdir(parents=True, exist_ok=True)
        got = False
        for fn in files:
            dest = dest_dir / fn
            if dest.exists() and is_gzip(dest) and is_fits(dest):
                got = True
                continue
            url = f"{BASE}/{year}/{obsid}/xti/event_cl/{fn}"
            if http_get(url, dest) and is_gzip(dest) and is_fits(dest):
                print(f"  {obsid}: OK {fn} ({dest.stat().st_size} bytes)")
                got = True
            else:
                dest.unlink(missing_ok=True)
                print(f"  {obsid}: INVALID {fn}")
        if got:
            ok += 1
        else:
            fail += 1
    print(f"OK: {ok} | FAIL: {fail}")
    return 0 if fail == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
