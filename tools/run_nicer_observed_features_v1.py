#!/usr/bin/env python3
"""NICER observed-feature catalogue (step 3+4): model-independent candidate
detection across the 20 frozen ObsIDs, blind discovery/validation split,
characterization as data description only."""
from __future__ import annotations

import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from astropy.io import fits

ROOT = Path("/home/error/SSZ-Spectroscopy-Bridge")
ART = ROOT / "artifacts"
DATA = ROOT / "data/raw/nicer/MAXI_J1820+070"

BAND = (0.05, 64.0)
DT = 1.0 / 64.0
MIN_SEG_S = 16.0
NB = 1024
PI_LO, PI_HI = 35, 900
SIGMA_HARD = 6.0   # classic G184 threshold
SIGMA_SOFT = 4.0   # catalogue extends below hard threshold, labeled

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def obsids():
    return sorted(p.name for p in DATA.iterdir() if p.is_dir())

def blind_split(obs):
    """deterministic odd/even hash split"""
    disc, val = [], []
    for o in obs:
        h = hashlib.sha256(o.encode()).hexdigest()
        (disc if int(h[0], 16) % 2 == 0 else val).append(o)
    return disc, val

def seg_psds(obsid):
    """per-GTI-segment Leahy PSDs, cleaned events"""
    ev = None
    for p in sorted((DATA / obsid / "xti" / "event_cl").glob("*cl.evt*")) if (DATA / obsid / "xti" / "event_cl").exists() else sorted((DATA / obsid).rglob("*cl.evt*")):
        ev = p
        break
    if ev is None:
        return None, None
    with fits.open(ev) as hdul:
        d = hdul[1].data
        t = d["TIME"].astype(float)
        pi = d["PI"].astype(int)
    m = (pi >= PI_LO) & (pi <= PI_HI)
    t = t[m]
    if len(t) < 1000:
        return None, None
    # segment boundaries from GTI gaps > 1 s
    t = np.sort(t)
    breaks = np.where(np.diff(t) > 1.0)[0]
    segs = np.split(t, breaks + 1)
    psds = []
    exposure = 0.0
    for s in segs:
        if len(s) < MIN_SEG_S / DT:
            continue
        t0 = s[0]
        rel = np.floor((s - t0) / DT).astype(np.int64)
        nb = NB
        nbin = int(rel.max()) + 1
        nsub = nbin // nb
        if nsub < 1:
            continue
        lc = np.zeros(nsub * nb)
        np.add.at(lc, rel[rel < nsub * nb], 1.0)
        lc = lc[: nsub * nb].reshape(nsub, nb)
        for row in lc:
            if row.sum() < 100:
                continue
            F = np.fft.rfft(row)
            p = (np.abs(F) ** 2) * 2.0 / row.sum()  # Leahy normalization
            freqs = np.fft.rfftfreq(nb, DT)
            band = (freqs >= BAND[0]) & (freqs <= BAND[1])
            psds.append((freqs[band], p[band]))
            exposure += nb * DT
    if not psds:
        return None, None
    P = np.mean([p for _, p in psds], axis=0)
    return (psds[0][0], P), exposure

def main():
    t0 = time.time()
    obs = obsids()
    disc, val = blind_split(obs)
    print(f"ObsIDs: {len(obs)} | discovery: {len(disc)} | validation: {len(val)}")

    noise_floor = 2.0
    # discovery pass
    cand_acc = {}  # rounded freq -> records
    per_obs_summary = {}
    for o in disc:
        res = seg_psds(o)
        if res is None or res[0] is None:
            per_obs_summary[o] = {"status": "no_data"}
            continue
        (freqs, P), exposure = res
        n_avg = max(1, len(P))
        sigma = 2.0 / np.sqrt(n_avg)
        # local maxima above soft threshold
        above = P > (noise_floor + SIGMA_SOFT * sigma * np.sqrt(max(1, np.mean(P) / 2.0)))
        is_max = np.r_[False, (P[1:-1] > P[:-2]) & (P[1:-1] > P[2:]), False]
        cand_idx = np.where(above & is_max)[0]
        per_obs_summary[o] = {"status": "ok", "n_candidates_raw": int(len(cand_idx)),
                               "exposure_s": round(float(exposure), 1)}
        for i in cand_idx:
            key = round(float(freqs[i]), 2)
            sig = float((P[i] - noise_floor) / max(sigma * np.sqrt(max(P[i], 2.0) / 2.0), 1e-9))
            cand_acc.setdefault(key, []).append({
                "obsid": o, "frequency_hz": float(freqs[i]), "power": float(P[i]),
                "local_significance_sigma_est": round(sig, 2)})

    # candidates recurring in >= 2 discovery ObsIDs OR any super-hard (>=6 sigma) single
    frozen_candidates = []
    for key, recs in sorted(cand_acc.items()):
        obs_set = sorted({r["obsid"] for r in recs}, key=lambda x: obs.index(x))
        # strongest record
        best = max(recs, key=lambda r: r["power"])
        # approximate sigma from averaged PSD chi2_2
        sig = best["local_significance_sigma_est"]
        if len(obs_set) >= 2 or sig >= SIGMA_HARD:
            frozen_candidates.append({
                "frequency_hz": key,
                "discovery_obsids": obs_set,
                "n_discovery_obsids": len(obs_set),
                "best_power": best["power"],
                "best_local_sigma_est": sig,
            })
    print(f"frozen discovery candidates: {len(frozen_candidates)}")

    # validation pass (frequencies frozen NOW)
    validation = []
    for c in frozen_candidates:
        f0 = c["frequency_hz"]
        hits = 0
        for o in val:
            res = seg_psds(o)
            if res is None or res[0] is None:
                continue
            (freqs, P), _ = res
            band = np.abs(freqs - f0) <= 0.25
            if not band.any():
                continue
            Pb = P[band]
            i = int(np.argmax(Pb))
            n_avg = max(1, len(P))
            sigma = 2.0 / np.sqrt(n_avg)
            sig = float((Pb[i] - noise_floor) / max(sigma * np.sqrt(max(Pb[i], 2.0) / 2.0), 1e-9))
            if Pb[i] >= noise_floor + SIGMA_SOFT * sigma * np.sqrt(max(Pb[i], 2.0) / 2.0):
                hits += 1
        validation.append({"frequency_hz": f0, "n_discovery_obsids": c["n_discovery_obsids"],
                            "n_validation_hits": hits,
                            "n_validation_obsids": len(val)})
    out = {
        "audit": "NICER_MAXI_J1820_OBSERVED_FEATURES_V1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "OBSERVATIONAL_UNBLINDING_PREREGISTRATION_V1",
        "blind_split": {"discovery": disc, "validation": val},
        "per_obs_summary": per_obs_summary,
        "frozen_candidates": frozen_candidates,
        "validation": validation,
        "n_frozen_candidates": len(frozen_candidates),
        "note": "model-independent cataloguing; Lorentzian/Q characterization deferred to description-only step; empty result is a valid outcome",
    }
    (ART / "NICER_MAXI_J1820_OBSERVED_FEATURES_V1.json").write_text(json.dumps(out, indent=1) + "\n")
    with open(ART / "NICER_MAXI_J1820_OBSERVED_FEATURES_V1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["frequency_hz", "n_discovery_obsids", "best_power", "best_local_sigma_est", "n_validation_hits"])
        for c, v in zip(frozen_candidates, validation):
            w.writerow([c["frequency_hz"], c["n_discovery_obsids"], c["best_power"], c["best_local_sigma_est"], v["n_validation_hits"]])
    print("catalogue written | wall:", round(time.time() - t0, 1), "s")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
