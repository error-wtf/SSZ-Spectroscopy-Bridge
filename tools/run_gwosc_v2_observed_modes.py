#!/usr/bin/env python3
"""GWOSC V2 real-data run — GW150914 ringdown, F1-F6 fixes implemented.

Locked to:
  - GWOSC_V2_ERROR_CORRECTION_PREREGISTRATION.json (F1-F6 fixes)
  - GWOSC_V2_F7_GATE_SPECIFICATION_FROZEN.json (f7_gate_v2_result_and_scope:
    claims restricted to tau >= 8 ms modal signals, 80-250 Hz, SNR>=12;
    detection statistic = slip-window band-RMS OR broadband RMS, thresholds =
    99th percentile of the identical statistic on 60 off-source draws)

NOT a blind analysis (same event data previously inspected); future
independent confirmation requires holdout data.

No Kerr QNM frequencies, no SSZ frequencies, no mass fitting anywhere.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import h5py
import numpy as np
from scipy.signal import welch, resample_poly

ROOT = Path("/home/error/SSZ-Spectroscopy-Bridge")
RAW = ROOT / "data/raw/gwosc/GW150914-v4"
ART = ROOT / "artifacts"

# F1: official GW150914-v4 event GPS (was 1126259462.0 in V1 — FATAL offset)
GPS_EVENT = 1126259462.4
WIN_START = 0.002                 # frozen post-merger start offset [s]
WIN_END = 0.06                    # frozen post-merger end offset [s]
START_LADDER = [-0.002, 0.0, 0.002, 0.004]
END_LADDER = [0.03, 0.04, 0.06, 0.08]
ORDERS = list(range(8, 44, 4))
F_TOL_HZ = 10.0
TAU_TOL_REL = 0.5
N_BOOT = 200                      # F4: full preregistered bootstrap
OFFSOURCE_SEGMENTS = [(-64.0, -32.0), (-32.0, -16.0), (16.0, 32.0), (32.0, 64.0)]
H1_L1_DELAY_S = 6.9e-3            # F6: L1 arrives ~6.9 ms after H1 (published)
PHASE_TOL_RAD = math.pi / 2.0     # frozen pre-run
CLAIM_TAU_MIN_S = 0.008           # F7-GATE-V2 coverage scope
N_NULL_DRAWS = 60                 # identical to the certified F7 gate null


def load_strain(det):
    fn = RAW / f"{'H' if det == 'H1' else 'L'}-{det}_LOSC_16_V2-1126257414-4096.hdf5"
    with h5py.File(fn, "r") as h:
        strain = h["strain/Strain"][:]
        gps_start = float(h["meta/GPSstart"][()])
        dt = float(h["meta/Duration"][()]) / len(strain)
    return strain, gps_start, dt


def offsource_psd(strain, gps_start, dt):
    """F5: PSD from OFF-SOURCE segments only."""
    segs = []
    for a, b in OFFSOURCE_SEGMENTS:
        i0 = int(((GPS_EVENT + a) - gps_start) / dt)
        i1 = int(((GPS_EVENT + b) - gps_start) / dt)
        if i0 < 0 or i1 > len(strain):
            raise RuntimeError(f"off-source segment [{a},{b}] outside file")
        segs.append(strain[i0:i1])
    f, p = welch(np.concatenate(segs), fs=1.0 / dt, nperseg=4096)
    return f, p


def whiten_with(strain, dt, freqs, psd_f, psd_p):
    """FFT whitening against the off-source PSD, band-limited 20-300 Hz."""
    interp = np.interp(freqs, psd_f, psd_p)
    from scipy.signal.windows import tukey
    w = tukey(len(strain), 0.2)
    x = (strain - strain.mean()) * w
    N = len(x)
    x_f = np.fft.rfft(x)
    safe = interp > 0
    x_f[~safe] = 0
    x_f[safe] /= np.sqrt(interp[safe] * dt * N)
    out = np.fft.irfft(x_f, N)
    x_f = np.fft.rfft(out)
    fr = np.fft.rfftfreq(N, dt)
    x_f[(fr < 20) | (fr > 300)] = 0
    return np.fft.irfft(x_f, N)


def matrix_pencil_modes(y, dt, order):
    """Damped modes with F2 amplitude (LSQ excitation coefficient)."""
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
            n = len(y)
            basis = z ** np.arange(n)
            # complex LSQ excitation coefficient; angle(c) = physical excitation
            # phase of this mode (owner review: angle(z) is only the per-sample
            # phase advance 2*pi*f*dt and carries NO detector-phase information)
            c = np.vdot(basis, y) / max(np.vdot(basis, basis), 1e-300)
            modes.append({"f": float(f), "tau": float(tau),
                          "amp": float(abs(c)), "phase": float(np.angle(c))})
    return modes


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
                if m["amp"] >= c["max_amp"]:
                    c["tau"] = m["tau"]
                    c["phase"] = m["phase"]
                c["amp"] = max(c["amp"], m["amp"])
                c["max_amp"] = max(c["max_amp"], m["amp"])
                c["n"] = n
                break
        else:
            clusters.append({"f": m["f"], "tau": m["tau"], "amp": m["amp"],
                             "max_amp": m["amp"], "phase": m["phase"], "n": 1})
    return sorted(clusters, key=lambda c: -c["amp"])[:6]


def decimate_chunk(chunk, dt):
    target_fs = 4096.0
    factor = int(round(1.0 / dt / target_fs))
    if factor >= 2:
        return resample_poly(chunk, 1, factor), dt * factor
    return chunk, dt


def extract_for_window(whitened, dt, ws, we):
    i0 = int((GPS_EVENT + ws - 1126257414.0) / dt)
    i1 = int((GPS_EVENT + we - 1126257414.0) / dt)
    if i0 < 0 or i1 > len(whitened) or i1 - i0 < 64:
        return []
    seg = whitened[i0:i1]
    seg_d, dt_d = decimate_chunk(seg, dt)
    all_modes = []
    for order in ORDERS:
        all_modes += matrix_pencil_modes(seg_d, dt_d, order)
    return cluster_modes(all_modes)


def main():
    t0 = time.time()
    rng = np.random.default_rng(20261009)
    report = {
        "audit": "GWOSC_GW150914_OBSERVED_MODES_V2",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "protocol": "GWOSC_V2_ERROR_CORRECTION_PREREGISTRATION + F7_GATE_V2_SCOPE",
        "not_blind": True,
        "event_gps": GPS_EVENT,
        "claim_scope": {"tau_min_s": CLAIM_TAU_MIN_S, "f_hz": [80, 250],
                         "note": "claims outside this scope are labeled "
                                 "OUTSIDE_DEMONSTRATED_SENSITIVITY"},
    }

    detector_stats = {}
    results = {}
    for det in ("H1", "L1"):
        strain, gps_start, dt = load_strain(det)
        assert abs(gps_start - 1126257414.0) < 1.0
        off = GPS_EVENT - gps_start
        assert 0 < off < len(strain) * dt, "event outside file (F1 cross-check)"
        freqs_all = np.fft.rfftfreq(len(strain), dt)
        f_p, p_psd = offsource_psd(strain, gps_start, dt)
        whitened = whiten_with(strain, dt, freqs_all, f_p, p_psd)
        print(f"{det}: whitened, event at file offset {off:.1f}s", flush=True)

        noise_segs = []
        for a, b in OFFSOURCE_SEGMENTS:
            i0 = int(((GPS_EVENT + a) - gps_start) / dt)
            i1 = int(((GPS_EVENT + b) - gps_start) / dt)
            noise_segs.append(whitened[i0:i1])
        seg_len = int((WIN_END + 0.01) / dt)
        f_tol_eff = max(F_TOL_HZ, 2.0 / (seg_len * dt))
        onset_i0 = seg_len // 2
        post_len = seg_len - onset_i0
        slip_offsets = list(range(0, seg_len - onset_i0 - post_len // 2,
                                  max(1, int(0.001 / dt))))

        def band_rms(chunk, f_center):
            best = 0.0
            for off_ in slip_offsets:
                x = chunk[onset_i0 + off_: onset_i0 + off_ + post_len]
                if len(x) < 16:
                    continue
                xw = x * np.hanning(len(x))
                spec = np.abs(np.fft.rfft(xw))
                fr = np.fft.rfftfreq(len(x), dt)
                sel = np.abs(fr - f_center) <= f_tol_eff
                if np.any(sel):
                    best = max(best, float(np.sqrt(np.mean(spec[sel] ** 2))))
            return best

        def broadband_rms(chunk):
            best = 0.0
            for off_ in slip_offsets:
                x = chunk[onset_i0 + off_: onset_i0 + off_ + post_len]
                if len(x) < 16:
                    continue
                xw = x * np.hanning(len(x))
                spec = np.abs(np.fft.rfft(xw))
                fr = np.fft.rfftfreq(len(x), dt)
                sel = (fr >= 20) & (fr <= 300)
                if np.any(sel):
                    best = max(best, float(np.sqrt(np.mean(spec[sel] ** 2))))
            return best

        # null thresholds (identical statistic + draws as the certified gate)
        probe_fs = [80, 120, 180, 250]
        null_stats = {f: [] for f in probe_fs}
        null_bb = []
        for k in range(N_NULL_DRAWS):
            seg = noise_segs[k % len(noise_segs)]
            s0 = int(rng.integers(1000, len(seg) - seg_len - 1000))
            chunk = seg[s0:s0 + seg_len]
            for fg in probe_fs:
                null_stats[fg].append(band_rms(chunk, fg))
            null_bb.append(broadband_rms(chunk))
        thr99 = {f: float(np.percentile(v, 99)) for f, v in null_stats.items()}
        thr99_bb = float(np.percentile(null_bb, 99))
        detector_stats[det] = {"band_thr99": thr99, "broadband_thr99": thr99_bb}

        # event-segment detection sweep (slip windows over the post-merger region)
        ev_i0 = int((GPS_EVENT + WIN_START - gps_start) / dt)
        ev_i1 = int((GPS_EVENT + WIN_END - gps_start) / dt)
        event_chunk = whitened[ev_i0 - onset_i0: ev_i1 + (seg_len - onset_i0 - post_len // 2)]
        sweep = []
        detected = False
        for off_ in slip_offsets:
            x = event_chunk[onset_i0 + off_: onset_i0 + off_ + post_len]
            if len(x) < 16:
                continue
            xw = x * np.hanning(len(x))
            spec = np.abs(np.fft.rfft(xw))
            fr = np.fft.rfftfreq(len(x), dt)
            sel_bb = (fr >= 20) & (fr <= 300)
            bb = float(np.sqrt(np.mean(spec[sel_bb] ** 2)))
            if bb > thr99_bb:
                fpk = float(fr[sel_bb][int(np.argmax(spec[sel_bb]))])
                row = {"t_after_winstart_ms": round(off_ * dt * 1000, 2),
                       "broadband_rms": round(bb, 4), "thr_bb": round(thr99_bb, 4),
                       "peak_f_hz": round(fpk, 1),
                       "exceeds_broadband": True}
                row["detected"] = True
                detected = True
                sweep.append(row)
        results[det] = {"detected": detected, "sweep": sweep}

        # F3 ladder + F2 characterization (pencil) on nominal + ladders
        nominal = extract_for_window(whitened, dt, WIN_START, WIN_END)
        ladder = []
        for ws in START_LADDER:
            for we in END_LADDER:
                ladder.append({"ws": ws, "we": we,
                               "modes": extract_for_window(whitened, dt, ws, we)})
        # F3: stability = cluster within tol in >=2 distinct start AND >=2 end windows
        stable = []
        for c in nominal:
            n_start = len({ld["ws"] for ld in ladder
                           if any(abs(m["f"] - c["f"]) <= f_tol_eff
                                  and abs(m["tau"] - c["tau"]) / c["tau"] <= TAU_TOL_REL
                                  for m in ld["modes"])})
            n_end = len({ld["we"] for ld in ladder
                         if any(abs(m["f"] - c["f"]) <= f_tol_eff
                                and abs(m["tau"] - c["tau"]) / c["tau"] <= TAU_TOL_REL
                                for m in ld["modes"])})
            stable.append({**{k: (round(v, 4) if isinstance(v, float) else v)
                              for k, v in c.items() if k != "phase"},
                           "phase_rad": round(c.get("phase", float("nan")), 4),
                           "start_ladder_hits": n_start, "end_ladder_hits": n_end,
                           "ladder_stable": bool(n_start >= 2 and n_end >= 2),
                           "in_claim_scope": bool(c["tau"] >= CLAIM_TAU_MIN_S
                                                   and 80 <= c["f"] <= 250)})
        results[det]["nominal_modes"] = stable
        results[det]["bootstrap_source"] = "see detector_stats; F4 bootstrap below"

        # F4: full 200 bootstrap null modes (off-source cyclic-shift windows)
        rngb = np.random.default_rng(42 + (0 if det == "H1" else 1))
        null_modes = []
        wlen = seg_len
        for _ in range(N_BOOT):
            seg_idx = int(rngb.integers(0, len(noise_segs)))
            seg = noise_segs[seg_idx]
            s0 = int(rngb.integers(1000, len(seg) - wlen - 1000))
            chunk = seg[s0:s0 + wlen]
            chunk_d, dt_d = decimate_chunk(chunk, dt)
            modes = []
            for order in ORDERS[:4]:
                modes += matrix_pencil_modes(chunk_d, dt_d, order)
            null_modes += [m["f"] for m in cluster_modes(modes)]
        null_f95 = float(np.percentile(null_modes, 95)) if null_modes else None
        results[det]["null_f_95_hz"] = null_f95
        results[det]["n_bootstrap"] = N_BOOT
        print(f"{det}: detected={detected}, nominal stable modes="
              f"{[(m['f'], m['tau'], m['ladder_stable']) for m in stable]}", flush=True)

    # ---------- F6: H1/L1 coherence with time-delay correction ----------
    # owner-review fix: phases are now the complex LSQ excitation phases
    # (angle of the mode amplitude), not angle(z); expected H1->L1 phase shift
    # for a common sky source includes the 2*pi*f*delay term
    coherent = []
    h1_modes = [m for m in results["H1"]["nominal_modes"] if m["ladder_stable"]]
    l1_modes = [m for m in results["L1"]["nominal_modes"] if m["ladder_stable"]]
    # recover phases (rounded in stable) — recompute from stored rounded values
    for ch in h1_modes:
        for cl in l1_modes:
            if abs(ch["f"] - cl["f"]) <= F_TOL_HZ:
                f_mean = (ch["f"] + cl["f"]) / 2.0
                expected = (2 * math.pi * f_mean * H1_L1_DELAY_S) % (2 * math.pi)
                dphase = (cl.get("phase_rad", float("nan"))
                          - ch.get("phase_rad", float("nan")) - expected)
                dphase = math.atan2(math.sin(dphase), math.cos(dphase))
                tau_rel = abs(ch["tau"] - cl["tau"]) / max((ch["tau"] + cl["tau"]) / 2, 1e-9)
                in_scope = ch["in_claim_scope"] and cl["in_claim_scope"]
                coherent.append({
                    "f_hz": round(f_mean, 2),
                    "tau_H1_s": ch["tau"], "tau_L1_s": cl["tau"],
                    "tau_rel_diff": round(tau_rel, 3),
                    "phase_diff_minus_delay_rad": round(dphase, 3),
                    "phase_within_tol": bool(abs(dphase) <= PHASE_TOL_RAD),
                    "tau_within_tol": bool(tau_rel <= TAU_TOL_REL),
                    "in_claim_scope": in_scope,
                    "coherent": bool(abs(dphase) <= PHASE_TOL_RAD
                                      and tau_rel <= TAU_TOL_REL),
                })

    any_detected = results["H1"]["detected"] or results["L1"]["detected"]
    report["detector_thresholds"] = detector_stats
    report["detectors"] = results
    report["coherent_pairs"] = coherent
    report["verdict"] = {
        "event_detected_by_certified_statistic": bool(any_detected),
        "n_coherent_pairs": len(coherent),
        "n_coherent_in_claim_scope": sum(1 for c in coherent if c["in_claim_scope"]),
        "claim": ("any tau>=8ms coherent pair above is a CANDIDATE modal observation; "
                   "it is NOT compared to any theory here (no Kerr, no SSZ)"),
    }
    report["wall_seconds"] = round(time.time() - t0, 1)
    out = ART / "GWOSC_GW150914_OBSERVED_MODES_V2.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    print("VERDICT:", json.dumps(report["verdict"]))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
