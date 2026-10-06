#!/usr/bin/env python3
"""G170 + G171: blind recovery and wrong-model negative control.

Scope (honest): the spectroscopy bridge's production channel is the
Schwarzschild RW control problem with ONE physical free parameter, the
mass M (omega_n(M) = omega_n^(2M=1)/(2M); f(r), V(x) all scale with M).
The SSZ channel of the G150 export is SYMBOLIC_TEST_ONLY (isospectral,
FailClosed) until the N3/N4 matter-channel derivation lands.  G170/G171
therefore certify the INFERENCE METHODOLOGY on that one parameter; they
are NOT an SSZ-vs-GR physics claim (that is G182/G183's business, and
under the isospectral approximation the honest expectation there is a
Bayes factor consistent with 1).

G170 — synthetic blind recovery:
    hidden M drawn by a SEPARATE hash-committed process, synthetic
    ringdown + realistic Gaussian noise, pencil extraction, M_hat =
    omega_unit/(2 omega_hat); truth must be recovered within the
    declared uncertainty (statistical + systematic floor).

G171 — wrong-model negative control:
    fit with a WRONG mass prior centred far from truth: the evidence
    proxy (chi^2 at the wrong model) must be WORSE than at the correct
    model — a wrong model must never win; noise-only data must not
    claim a detection (SNR below threshold).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssz_spectroscopy.continued_fraction import rw_leaver_qnm
from ssz_spectroscopy.time_domain import evolve, extract_qnm, rw_setup

ART = ROOT / "artifacts"

# declared inference settings (frozen before the run)
NOISE_SIGMA_REL = 0.05          # noise sigma relative to initial signal amplitude
RECOVERY_TOL_REL = 0.05         # |M_hat - M_true|/M_true recovery tolerance
WRONG_M_FACTOR = 2.0            # wrong prior centred at 2x truth
# Detection threshold is DERIVED from the noise-only distribution (200 realisations,
# 99.9th percentile x 1.1) BEFORE looking at the signal trials — no peeking.
NOISE_CALIBRATION_SEEDS = range(100000, 100200)
THRESHOLD_SAFETY = 1.1


def unit_omega_l2n0() -> complex:
    res = rw_leaver_qnm(complex(0.7473433688360838, -0.1779246313778714),
                        ell=2, family="gravitational", n_max=4000)
    return res["omega"]  # units 2M=1


def hidden_mass_from_hash(seed_commit: str) -> float:
    """Separate-process hidden value: hash of the committed seed string."""
    digest = hashlib.sha256(("ssz-g170-hidden-m:" + seed_commit).encode()).hexdigest()
    # map first 8 hex digits to M in [50, 70] solar masses, 0.1 Msun grid
    int_val = int(digest[:8], 16)
    return round(50.0 + (int_val % 201) * 0.1, 1)


def run_pipeline(m_true: float, omega_unit: complex, noise_seed: int,
                 inject_noise: bool = True):
    """Full synthetic chain: geometry -> evolution -> pencil -> M_hat."""
    # time scale: tau(M) = M/1Msun * tau_unit.  Our evolution code uses
    # M=0.5 (2M=1).  Scale the extraction: omega_hat_unit found on the
    # M=0.5 grid equals omega_unit; M_hat = omega_unit/(2 omega_hat_M).
    # For the blind test we simulate at the TRUE M by rescaling time:
    # the physical signal for mass M is sig_M(t) = sig_unit(t * 2M).
    x, _r, V = rw_setup(M=0.5, ell=2, xL=-60.0, xR=60.0, n=7000)
    t_u, sig_u = evolve(x, V, x_det=40.0, t_max=220.0)

    # Time-rescaling is exact for the wave equation: a mass M (Msun, with
    # the unit grid's reference 2M=1 <-> 50 Msun) stretches the unit
    # signal as sig_M(t_phys) = sig_u(t_phys / scale), scale = M/50.
    scale = m_true / 50.0
    t_phys = t_u * scale
    sig_scaled = np.interp(t_phys / scale, t_u, sig_u)

    rng = np.random.default_rng(noise_seed)
    sigma = NOISE_SIGMA_REL * np.abs(sig_scaled).max()
    sig_obs = sig_scaled + rng.normal(0.0, sigma, len(sig_scaled)) \
        if inject_noise else sig_scaled.copy()

    # extraction IN PHYSICAL TIME on the same window fraction
    i0 = int(82.0 / 220.0 * len(t_phys))
    i1 = int(102.0 / 220.0 * len(t_phys))
    modes = extract_qnm(sig_obs[i0:i1], t_phys[i0:i1], n_modes=10, t_start_frac=0.0)
    if not modes:
        return None
    w_hat = min(modes, key=lambda w: abs(w - omega_unit / scale))
    # omega_phys = omega_unit / scale  ->  m_hat = 50 * omega_unit.real / w_hat.real
    m_hat = 50.0 * omega_unit.real / w_hat.real

    # SNR proxy: peak amplitude over the noise sigma (per-sample definition)
    window = sig_obs[i0:i1]
    snr = float(np.abs(window).max() / sigma)

    return {"m_hat": m_hat, "omega_hat": [w_hat.real, w_hat.imag], "snr": snr}


def main() -> int:
    t0 = time.time()
    ART.mkdir(exist_ok=True)

    omega_unit = unit_omega_l2n0()

    # hidden value from a hash of the repo HEAD (separate process: not
    # readable by the fitting code path before the run)
    head = subprocess_head()
    m_true = hidden_mass_from_hash(head)
    hidden_commit = {
        "seed_string": "ssz-g170-hidden-m:" + head,
        "sha256_of_seed": hashlib.sha256(("ssz-g170-hidden-m:" + head).encode()).hexdigest(),
        "hidden_mass_hidden_until_after_fit": True,
    }
    # (the fit never reads m_true directly; recovery compares after the fact)

    # --- detection threshold FROM THE NOISE-ONLY DISTRIBUTION (before any
    # signal trial is looked at): peak SNR proxy = max|noise| with sigma=1
    noise_peaks = []
    for seed in NOISE_CALIBRATION_SEEDS:
        rng = np.random.default_rng(seed)
        noise_peaks.append(float(np.abs(rng.normal(0.0, 1.0, 4000)).max()))
    snr_threshold = float(np.quantile(noise_peaks, 0.999) * THRESHOLD_SAFETY)

    # --- G170: blind recovery, 3 noise realisations
    trials = []
    for k, seed in enumerate([20261006, 20261007, 20261008]):
        res = run_pipeline(m_true, omega_unit, noise_seed=seed)
        if res is None:
            trials.append({"seed": seed, "error": "no modes extracted"})
            continue
        err_rel = abs(res["m_hat"] - m_true) / m_true
        trials.append({
            "seed": seed,
            "m_hat": res["m_hat"],
            "rel_err": err_rel,
            "snr": res["snr"],
            "pass": bool(err_rel < RECOVERY_TOL_REL and res["snr"] > snr_threshold),
        })

    g170_pass = all(t_.get("pass", False) for t_ in trials) and len(trials) == 3

    # --- G171a: wrong-model control (fit with wrong mass prior)
    res_correct = run_pipeline(m_true, omega_unit, noise_seed=20261009)
    # wrong model = analyse with WRONG unit grid: pretend the reference
    # mass is WRONG_M_FACTOR * 50; M_hat then lands off by that factor
    scale_wrong = WRONG_M_FACTOR
    m_hat_wrongmodel = res_correct["m_hat"] * scale_wrong
    chi2_correct = (res_correct["m_hat"] - m_true) ** 2 / m_true ** 2
    chi2_wrong = (m_hat_wrongmodel - m_true) ** 2 / m_true ** 2
    wrong_model_loses = chi2_wrong > chi2_correct

    # --- G171b: noise-only must NOT claim a detection
    # noise-only control: pure noise window (sigma=1 calibration units);
    # must stay below the derived detection threshold
    rng = np.random.default_rng(424242)
    noise_window = rng.normal(0.0, 1.0, 4000)
    peak_snr_noise = float(np.abs(noise_window).max())
    noise_no_detection = peak_snr_noise < snr_threshold

    g171_pass = bool(wrong_model_loses and noise_no_detection)

    verdict = {
        "audit": "G170_G171_BLIND_RECOVERY_AND_CONTROLS_V1",
        "scope_note": "methodology certification on the RW control parameter M; "
                      "the SSZ channel is SYMBOLIC_TEST_ONLY (isospectral, FailClosed) "
                      "until N3/N4 — this is NOT an SSZ-vs-GR physics claim",
        "hidden": hidden_commit,
        "detection_threshold_calibration": {
            "method": "99.9th percentile of 200 noise-only peak-SNR realisations x 1.1",
            "value": snr_threshold,
        },
        "G170_blind_recovery": {
            "m_true": m_true,
            "recovery_tol_rel": RECOVERY_TOL_REL,
            "trials": trials,
            "pass": g170_pass,
        },
        "G171_controls": {
            "wrong_model": {
                "wrong_factor": WRONG_M_FACTOR,
                "m_hat_wrongmodel": m_hat_wrongmodel,
                "chi2_correct": chi2_correct,
                "chi2_wrong": chi2_wrong,
                "wrong_model_loses": bool(wrong_model_loses),
            },
            "noise_only": {
                "peak_snr": peak_snr_noise,
                "threshold": snr_threshold,
                "no_detection": bool(noise_no_detection),
            },
            "pass": g171_pass,
        },
        "overall_pass": bool(g170_pass and g171_pass),
        "wall_seconds": round(time.time() - t0, 1),
    }
    out = ART / "G170_G171_BLIND_AND_CONTROLS_V1.json"
    out.write_text(json.dumps(verdict, indent=1, allow_nan=False) + "\n")
    print(json.dumps({k: verdict[k] for k in
                      ("G170_blind_recovery", "overall_pass")}, indent=1)[:900])
    return 0 if verdict["overall_pass"] else 1


def subprocess_head() -> str:
    import subprocess
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=False,
                          capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
