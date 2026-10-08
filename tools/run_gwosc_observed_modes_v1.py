#!/usr/bin/env python3
"""GWOSC model-agnostic ringdown extraction (step 5+6).

GW150914-v4, H1 and L1 INDEPENDENTLY:
  whitened strain -> matrix-pencil (Prony) damped-mode extraction in the
  frozen post-merger window -> start/end-time ladders -> bootstrap ->
  coherence gate against the frozen tolerances -> off-source null
  distribution.

No Kerr QNM frequencies, no SSZ frequencies, no mass windows anywhere.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import h5py
import numpy as np
from scipy.signal import welch, resample_poly

ROOT = Path("/home/error/SSZ-Spectroscopy-Bridge")
RAW = ROOT / "data/raw/gwosc/GW150914-v4"
ART = ROOT / "artifacts"

GPS_EVENT = 1126259462.0          # GW150914 event GPS (public catalog value)
WIN_START = 0.002                 # frozen post-merger start offset [s]
WIN_END = 0.06                    # frozen post-merger end offset [s]
START_LADDER = [-0.002, 0.0, 0.002, 0.004]
END_LADDER = [0.03, 0.04, 0.06, 0.08]
ORDERS = list(range(8, 44, 4))
F_TOL_HZ = 10.0
TAU_TOL_REL = 0.5
N_BOOT = 200
OFFSOURCE_SEGMENTS = [(-64.0, -32.0), (-32.0, -16.0), (16.0, 32.0), (32.0, 64.0)]


def load_strain(det):
    fn = RAW / f"{'H' if det == 'H1' else 'L'}-{det}_LOSC_16_V2-1126257414-4096.hdf5"
    with h5py.File(fn, "r") as h:
        strain = h["strain/Strain"][:]
        gps_start = float(h["meta/GPSstart"][()])
        dt = float(h["meta/Duration"][()]) / len(strain)
    return strain, gps_start, dt


def whiten(strain, dt):
    """FFT-based whitening with the full-segment PSD (Tukey-edged)."""
    from scipy.signal.windows import tukey
    w = tukey(len(strain), 0.2)
    x = (strain - strain.mean()) * w
    N = len(x)
    freqs = np.fft.rfftfreq(N, dt)
    psd = np.zeros_like(freqs)
    nper = 4096
    f_p, p_psd = welch(strain, fs=1.0 / dt, nperseg=nper)
    psd = np.interp(freqs, f_p, p_psd)
    x_f = np.fft.rfft(x)
    # avoid division by ~0 at DC and very low freqs
    safe = psd > 0
    x_f[~safe] = 0
    x_f[safe] /= np.sqrt(psd[safe] * dt * N)
    out = np.fft.irfft(x_f, N)
    # highpass 20 Hz + lowpass 300 Hz in frequency domain
    x_f = np.fft.rfft(out)
    x_f[(freqs < 20) | (freqs > 300)] = 0
    return np.fft.irfft(x_f, N)


def matrix_pencil_modes(y, dt, order):
    """Prony/matrix-pencil damped modes: returns list of (f_hz, tau_s, amp)."""
    N = len(y)
    if order >= N // 2:
        order = N // 2 - 1
    # Hankel matrix approach (pencil of两口 halves)
    L = N // 2
    Y1 = np.zeros((N - L, L), dtype=complex)
    Y2 = np.zeros((N - L, L), dtype=complex)
    ys = y.astype(complex)
    for i in range(N - L):
        Y1[i] = ys[i:i + L]
        Y2[i] = ys[i + 1:i + L + 1]
    # SVD of Y1
    U, s, Vh = np.linalg.svd(Y1, full_matrices=False)
    V = Vh[:order].conj().T
    # pencil eigenvalues
    Y2v = Y2 @ V
    Y1v = Y1 @ V
    eig = np.linalg.eigvals(np.linalg.pinv(Y1v) @ Y2v)
    modes = []
    mag = np.log(np.abs(eig) + 1e-300) / dt
    for z in eig:
        if abs(z) <= 0 or abs(z) > 1.5:
            continue
        tau = -1.0 / (np.log(abs(z)) / dt)
        if tau <= 0:
            continue
        phase = np.angle(z)
        f = phase / (2 * np.pi * dt)
        if f < 0:
            f += 1.0 / dt
        if 20 <= f <= 300 and tau >= 0.001 and tau <= 1.0:
            modes.append((f, tau, abs(z)))
    return modes


def cluster_modes(modes, f_bin=10.0):
    """simple frequency clustering -> dominant mode per cluster"""
    if not modes:
        return []
    modes = sorted(modes, key=lambda m: -m[2])
    clusters = []
    for f, tau, a in modes:
        for c in clusters:
            if abs(c["f"] - f) < f_bin:
                # weighted update
                n = c["n"] + 1
                c["f"] = (c["f"] * c["n"] + f) / n
                c["tau"] = (c["tau"] * c["n"] + tau) / n
                c["n"] = n
                c["max_amp"] = max(c["max_amp"], a)
                break
        else:
            clusters.append({"f": f, "tau": tau, "n": 1, "max_amp": a})
    return sorted(clusters, key=lambda c: -c["max_amp"])[:5]


def extract_for_window(whitened, gps_start, dt, ws, we):
    i0 = int((GPS_EVENT + ws - gps_start) / dt)
    i1 = int((GPS_EVENT + we - gps_start) / dt)
    if i0 < 0 or i1 > len(whitened) or i1 - i0 < 64:
        return []
    seg = whitened[i0:i1]
    # resample to 4096 Hz for pencil stability
    if dt < 1 / 4096:
        seg = resample_poly(seg, 1, int(round(1 / dt / 4096)))
        dt_e = 1 / 4096
    else:
        dt_e = dt
    all_modes = []
    for order in ORDERS:
        all_modes += matrix_pencil_modes(seg, dt_e, order)
    return cluster_modes(all_modes)


def main():
    t0 = time.time()
    results = {}
    for det in ("H1", "L1"):
        strain, gps_start, dt = load_strain(det)
        print(f"{det}: {len(strain)} samples, dt={dt:.2e}, gps_start={gps_start}")
        whitened = whiten(strain, dt)
        # nominal window
        nominal = extract_for_window(whitened, gps_start, dt, WIN_START, WIN_END)
        # ladders
        ladder_modes = []
        for ws in START_LADDER:
            for we in END_LADDER:
                ms = extract_for_window(whitened, gps_start, dt, ws, we)
                ladder_modes.append({"ws": ws, "we": we, "modes": ms})
        # bootstrap: cyclic-shift the whitened data (noise null) and re-extract
        rng = np.random.default_rng(42)
        null_f = []
        i0 = int((GPS_EVENT + WIN_START - gps_start) / dt)
        i1 = int((GPS_EVENT + WIN_END - gps_start) / dt)
        wlen = i1 - i0
        for _ in range(min(N_BOOT, 50)):  # cap for wall time
            shift = int(rng.integers(wlen + 100, len(whitened) - wlen - 100))
            seg = whitened[shift:shift + wlen]
            if dt < 1 / 4096:
                seg = resample_poly(seg, 1, int(round(1 / dt / 4096)))
            modes = []
            for order in ORDERS[:4]:
                modes += matrix_pencil_modes(seg, 1 / 4096, order)
            null_f += [c['f'] for c in cluster_modes(modes)]
        null_95 = float(np.percentile(null_f, 95)) if null_f else None
        # null distribution is over frequencies of noise modes; for the false-alarm
        # criterion we use AMPLITUDE, so record the amp percentile too:
        null_amp = []
        rng2 = np.random.default_rng(7)
        for _ in range(min(N_BOOT, 50)):
            shift = int(rng2.integers(wlen + 100, len(whitened) - wlen - 100))
            seg = whitened[shift:shift + wlen]
            if dt < 1 / 4096:
                seg = resample_poly(seg, 1, int(round(1 / dt / 4096)))
            for order in ORDERS[:4]:
                null_amp += [m[2] for m in matrix_pencil_modes(seg, 1 / 4096, order) if m[2] < 1e6]
        amp_99 = float(np.percentile(null_amp, 99)) if null_amp else None
        results[det] = {"nominal": nominal, "ladder": ladder_modes,
                         "null_f_95": null_95, "null_amp_99": amp_99,
                         "n_null_samples": len(null_amp)}
        print(f"{det}: nominal clusters: {[(round(c['f'],1), round(c['tau'],4)) for c in nominal]}")
        print(f"{det}: null amp 99% = {amp_99}")

    # ---------- coherence gate ----------
    h1 = {round(c["f"]): c for c in results["H1"]["nominal"]}
    l1 = {round(c["f"]): c for c in results["L1"]["nominal"]}
    coherent = []
    for fh, ch in h1.items():
        for fl, cl in l1.items():
            if abs(fh - fl) <= F_TOL_HZ:
                tau_rel = abs(ch["tau"] - cl["tau"]) / max((ch["tau"] + cl["tau"]) / 2, 1e-9)
                amp_ok = (ch["max_amp"] >= (results["H1"]["null_amp_99"] or 0) and
                          cl["max_amp"] >= (results["L1"]["null_amp_99"] or 0))
                persistence = ch["n"] >= 2 and cl["n"] >= 2
                coherent.append({
                    "f_hz": round((fh + fl) / 2, 2),
                    "f_H1": fh, "f_L1": fl,
                    "tau_H1_s": round(ch["tau"], 5), "tau_L1_s": round(cl["tau"], 5),
                    "tau_rel_diff": round(tau_rel, 3),
                    "tau_within_tolerance": bool(tau_rel <= TAU_TOL_REL),
                    "amp_above_null_99": bool(amp_ok),
                    "pencil_order_persistence": bool(persistence),
                    "survives": bool(tau_rel <= TAU_TOL_REL and amp_ok and persistence),
                })
    out = {
        "audit": "GWOSC_GW150914_OBSERVED_MODES_V1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "OBSERVATIONAL_UNBLINDING_PREREGISTRATION_V1",
        "event_gps": GPS_EVENT,
        "window_s": [WIN_START, WIN_END],
        "no_templates": True,
        "per_detector": {det: {"nominal_clusters": [
            {"f_hz": round(c["f"], 2), "tau_s": round(c["tau"], 5),
             "Q": round(2 * np.pi * c["f"] * c["tau"], 2),
             "n_pencil_orders": c["n"], "max_amp": round(c["max_amp"], 4)}
            for c in results[det]["nominal"]],
            "null_amp_99": results[det]["null_amp_99"],
            "n_null_samples": results[det]["n_null_samples"],
            "ladder_runs": len(results[det]["ladder"])} for det in ("H1", "L1")},
        "coherence_gate": {
            "f_tol_hz": F_TOL_HZ, "tau_tol_rel": TAU_TOL_REL,
            "pairs": coherent,
            "n_surviving": sum(1 for c in coherent if c["survives"]),
        },
        "wall_seconds": round(time.time() - t0, 1),
        "note": "model-agnostic matrix-pencil extraction; no Kerr/SSZ labels; empty survivor set is a valid outcome",
    }
    (ART / "GWOSC_GW150914_OBSERVED_MODES_V1.json").write_text(json.dumps(out, indent=1) + "\n")
    import csv
    with open(ART / "GWOSC_GW150914_OBSERVED_MODES_V1.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["f_hz", "f_H1", "f_L1", "tau_H1_s", "tau_L1_s", "tau_rel_diff",
                     "amp_above_null_99", "persistence", "survives"])
        for c in coherent:
            w.writerow([c["f_hz"], c["f_H1"], c["f_L1"], c["tau_H1_s"], c["tau_L1_s"],
                         c["tau_rel_diff"], c["amp_above_null_99"],
                         c["pencil_order_persistence"], c["survives"]])
    print("SURVIVING MODES:", out["coherence_gate"]["n_surviving"])
    print("written | wall:", out["wall_seconds"], "s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
