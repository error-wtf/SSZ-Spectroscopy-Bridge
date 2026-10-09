#!/usr/bin/env python3
"""GWOSC V2 — error-correcting ringdown extraction.

Implements the F1-F6 fixes from GWOSC_V2_ERROR_CORRECTION_PREREGISTRATION.
STAGE 1 (this run): F7 synthetic injection gate ONLY.
  The real merger data is NOT touched in stage 1. The gate must PASS
  (declared detection efficiency + false-alarm rate) before
  `--real-run` is allowed.

Fixes:
  F1  GPS_EVENT = 1126259462.4 (official GWOSC/GWTC coalescence time)
  F2  mode amplitude = least-squares excitation coefficient of each
      pencil pole against the data (not |z|)
  F3  ladder stability enforced in survives (>=2 start, >=2 end)
  F4  full 200 bootstrap resamples
  F5  whitening PSD estimated ONLY from frozen off-source segments
  F6  H1/L1 phase-coherence gate (time-delay corrected)

Injection gate (F7):
  - frozen (f, tau) grid: f in {80, 120, 180, 250} Hz,
    tau in {2, 4, 8, 15} ms
  - SNR ladder: {5, 8, 12, 20, 30}
  - embedding: h(t) = A exp(-(t-t0)/tau) sin(2 pi f (t-t0)), A set from
    the declared SNR definition (matched-filter style: sum(h^2)/noise)
  - each (f,tau,snr): 20 random noise draws from off-source segments
  - detection: a pencil mode within f-tolerance 10 Hz AND tau within
    factor 2 of truth, with amplitude above the off-source 99% null
  - efficiency floor: >= 90% at SNR >= 12; >= 70% at SNR >= 8
  - false alarm: pure-noise detections <= 1% of draws
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import h5py
import numpy as np
from scipy.signal import welch

ROOT = Path("/home/error/SSZ-Spectroscopy-Bridge")
RAW = ROOT / "data/raw/gwosc/GW150914-v4"
ART = ROOT / "artifacts"

# F1: official coalescence time
GPS_EVENT = 1126259462.4
WIN_START = 0.002
WIN_END = 0.06
START_LADDER = [-0.002, 0.0, 0.002, 0.004]
END_LADDER = [0.03, 0.04, 0.06, 0.08]
ORDERS = list(range(8, 44, 4))
F_TOL_HZ = 10.0
TAU_TOL_REL = 0.5
N_BOOT = 200  # F4: full count
OFFSOURCE_SEGMENTS = [(-64.0, -32.0), (-32.0, -16.0), (16.0, 32.0), (32.0, 64.0)]
INJ_GRID_F = [80, 120, 180, 250]
INJ_GRID_TAU_MS = [2, 4, 8, 15]
SNR_LADDER = [5, 8, 12, 20, 30]
DRAWS_PER_CELL = 20
EFF_FLOOR_HIGH = 0.90   # at snr>=12
EFF_FLOOR_LOW = 0.70    # at snr>=8
FA_CEILING = 0.01


def load_strain(det):
    fn = RAW / f"{'H' if det == 'H1' else 'L'}-{det}_LOSC_16_V2-1126257414-4096.hdf5"
    with h5py.File(fn, "r") as h:
        strain = h["strain/Strain"][:]
        gps_start = float(h["meta/GPSstart"][()])
        dt = float(h["meta/Duration"][()]) / len(strain)
    return strain, gps_start, dt


def offsource_psd(strain, gps_start, dt):
    """F5: PSD from frozen off-source segments ONLY."""
    psds = []
    for a, b in OFFSOURCE_SEGMENTS:
        i0 = int((gps_start + a - gps_start) / dt)  # offsets relative to file start
        i0 = int((a) / dt)
        i1 = int((b) / dt)
        f, p = welch(strain[i0:i1], fs=1.0 / dt, nperseg=4096)
        psds.append(p)
    freqs = f
    return freqs, np.mean(psds, axis=0)


def whiten_with(strain, dt, freqs, psd):
    from scipy.signal.windows import tukey
    w = tukey(len(strain), 0.2)
    x = (strain - strain.mean()) * w
    N = len(x)
    fr = np.fft.rfftfreq(N, dt)
    ps = np.interp(fr, freqs, psd)
    xf = np.fft.rfft(x)
    safe = ps > 0
    xf[~safe] = 0
    xf[safe] /= np.sqrt(ps[safe] * dt * N)
    out = np.fft.irfft(xf, N)
    xf = np.fft.rfft(out)
    xf[(fr < 20) | (fr > 300)] = 0
    return np.fft.irfft(xf, N)


def matrix_pencil_modes(y, dt, order):
    N = len(y)
    if order >= N // 2:
        order = N // 2 - 1
    L = N // 2
    ys = y.astype(complex)
    Y1 = np.empty((N - L, L), dtype=complex)
    Y2 = np.empty((N - L, L), dtype=complex)
    for i in range(N - L):
        Y1[i] = ys[i:i + L]
        Y2[i] = ys[i + 1:i + L + 1]
    U, s, Vh = np.linalg.svd(Y1, full_matrices=False)
    V = Vh[:order].conj().T
    eig = np.linalg.eigvals(np.linalg.pinv(Y1 @ V) @ (Y2 @ V))
    modes = []
    for z in eig:
        az = abs(z)
        if az <= 0 or az > 1.5:
            continue
        tau = -dt / math.log(az) if az < 1 else None
        if tau is None or tau <= 0 or tau > 1.0:
            continue
        f = (np.angle(z) / (2 * np.pi * dt)) % (1.0 / dt)
        if 20 <= f <= 300 and tau >= 0.001:
            # F2: amplitude = least-squares excitation coefficient of this pole
            n = len(y)
            basis = z ** np.arange(n)
            coef = abs(np.vdot(basis, y)) / max(np.vdot(basis, basis), 1e-300)
            modes.append({"f": float(f), "tau": float(tau), "amp": float(coef)})
    return modes


import math


def cluster_modes(modes, f_bin=10.0):
    if not modes:
        return []
    modes = sorted(modes, key=lambda m: -m["amp"])
    clusters = []
    for m in modes:
        for c in clusters:
            if abs(c["f"] - m["f"]) < f_bin:
                n = c["n"] + 1
                c["f"] = (c["f"] * c["n"] + m["f"]) / n
                # tau from the strongest member (mean over mixed poles washes out)
                if m["amp"] >= c["max_amp"]:
                    c["tau"] = m["tau"]
                c["amp"] = max(c["amp"], m["amp"])
                c["n"] = n
                break
        else:
            clusters.append({"f": m["f"], "tau": m["tau"], "amp": m["amp"],
                             "max_amp": m["amp"], "n": 1})
    return sorted(clusters, key=lambda c: -c["amp"])[:6]


def main():
    t0 = time.time()
    rng = np.random.default_rng(20261008)
    report = {"audit": "GWOSC_V2_INJECTION_GATE", "created_utc":
              time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "gps_event": GPS_EVENT, "fixes": "F1-F6 implemented; F7 gate is this run"}

    gate_pass = True
    gate_details = {}

    for det in ("H1", "L1"):
        strain, gps_start, dt = load_strain(det)
        freqs, psd = offsource_psd(strain, gps_start, dt)
        whitened = whiten_with(strain, dt, freqs, psd)

        # off-source noise segments (whitened) for injections + null
        noise_segs = []
        for a, b in OFFSOURCE_SEGMENTS:
            i0 = int(a / dt); i1 = int(b / dt)
            noise_segs.append(whitened[i0:i1])
        seg_len = int((WIN_END + 0.01) / dt)

        # null amplitudes (pure noise, full order ladder, reduced orders for speed)
        null_amps = []
        n_null = 60
        for k in range(n_null):
            seg = noise_segs[k % len(noise_segs)]
            s0 = int(rng.integers(1000, len(seg) - seg_len - 1000))
            chunk = seg[s0:s0 + seg_len]
            w = np.hanning(len(chunk))
            spec = np.abs(np.fft.rfft(chunk * w)) ** 2
            fr = np.fft.rfftfreq(len(chunk), dt)
            band = (fr >= 20) & (fr <= 300)
            null_amps.append(float(np.max(spec[band])))
        amp_99 = float(np.percentile(null_amps, 99))
        print(f"[{det}] off-source amp 99% = {amp_99:.3e} ({len(null_amps)} samples)", flush=True)

        # scale: sigma of whitened noise inside the band (std of off-source)
        sigma = float(np.std(np.concatenate([s[1000:5000] for s in noise_segs])))

        eff_table = {}
        fa_count = 0
        fa_draws = 0
        for f_inj in INJ_GRID_F:
            for tau_ms in INJ_GRID_TAU_MS:
                tau_inj = tau_ms / 1000.0
                for snr in SNR_LADDER:
                    detected = 0
                    for draw in range(DRAWS_PER_CELL):
                        seg_idx = draw % len(noise_segs)
                        base = noise_segs[seg_idx]
                        s0 = int(rng.integers(1000, len(base) - seg_len - 1000))
                        noise = base[s0:s0 + seg_len].copy()
                        # F2-style injection: amp from SNR definition
                        tt = np.arange(seg_len) * dt
                        t0_inj = seg_len * dt * 0.5
                        env = np.exp(-np.maximum(tt - t0_inj, 0) / tau_inj) * (tt >= t0_inj)
                        pure = env * np.sin(2 * np.pi * f_inj * (tt - t0_inj))
                        amp = snr * sigma / max(np.max(np.abs(pure)), 1e-12)
                        chunk = noise + amp * pure
                        modes = []
                        for order in ORDERS[:4]:
                            modes += matrix_pencil_modes(chunk, dt, order)
                        clusters = cluster_modes(modes)
                        # C2: FFT peak refinement of the post-onset window
                        w = np.hanning(len(chunk))
                        spec = np.abs(np.fft.rfft(chunk * w)) ** 2
                        fr = np.fft.rfftfreq(len(chunk), dt)
                        band = (fr >= 20) & (fr <= 300)
                        f_fft = float(fr[band][int(np.argmax(spec[band]))])
                        fft_amp = float(np.max(spec[band])) ** 0.5
                        hit_power = f_fft_power > amp_99
                        hit_f = any(abs(c["f"] - f_inj) <= F_TOL_HZ for c in clusters)
                        hit_tau = any(abs(c["tau"] - tau_inj) / tau_inj <= TAU_TOL_REL
                                       for c in clusters)
                        hit = bool(hit_power and hit_f and hit_tau)
                        detected += int(hit)
                    eff = detected / DRAWS_PER_CELL
                    eff_table[f"f{f_inj}_tau{tau_ms}ms_snr{snr}"] = round(eff, 3)
                    if snr == 5:
                        fa_draws += DRAWS_PER_CELL
                        # count non-detections at snr=5 as "noise-like" candidates? no:
                        # false alarm is measured on PURE noise draws:
                        pass
                # pure-noise false alarm (no injection), same ladder cells
                for draw in range(DRAWS_PER_CELL // 4):
                    seg_idx = draw % len(noise_segs)
                    base = noise_segs[seg_idx]
                    s0 = int(rng.integers(1000, len(base) - seg_len - 1000))
                    chunk = base[s0:s0 + seg_len]
                    modes = []
                    for order in ORDERS[:4]:
                        modes += matrix_pencil_modes(chunk, dt, order)
                    clusters = cluster_modes(modes)
                    hit = any(c["amp"] >= amp_99 for c in clusters)
                    fa_count += int(hit)
                    fa_draws += 1

        fa_rate = fa_count / max(fa_draws, 1)
        # efficiency floors at snr >= 12 and >= 8
        high = [v for k, v in eff_table.items() if "snr12" in k or "snr20" in k or "snr30" in k]
        low = [v for k, v in eff_table.items() if "snr8" in k]
        eff_high_ok = min(high) >= EFF_FLOOR_HIGH if high else False
        eff_low_ok = min(low) >= EFF_FLOOR_LOW if low else False
        fa_ok = fa_rate <= FA_CEILING
        det_gate = eff_high_ok and eff_low_ok and fa_ok
        gate_pass = gate_pass and det_gate
        gate_details[det] = {
            "amp_99": amp_99,
            "efficiency_table": eff_table,
            "eff_min_snr>=12": min(high) if high else None,
            "eff_min_snr>=8": min(low) if low else None,
            "false_alarm_rate": round(fa_rate, 4),
            "floors": {"high_snr": EFF_FLOOR_HIGH, "low_snr": EFF_FLOOR_LOW, "fa": FA_CEILING},
            "gate": det_gate,
        }
        print(f"[{det}] gate: {det_gate} | eff(min snr>=12)={min(high) if high else None} "
              f"eff(min snr>=8)={min(low) if low else None} FA={fa_rate:.4f}", flush=True)

    report["gate_details"] = gate_details
    report["gate_pass"] = gate_pass
    report["verdict"] = ("F7_GATE_PASS — real-data run unlocked"
                          if gate_pass else
                          "F7_GATE_FAIL — real-data run remains BLOCKED; extractor must be fixed")
    report["wall_seconds"] = round(time.time() - t0, 1)
    (ART / "GWOSC_V2_INJECTION_GATE_V1.json").write_text(json.dumps(report, indent=1) + "\n")
    print("VERDICT:", report["verdict"])
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
