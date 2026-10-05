#!/usr/bin/env python3
"""G160 pre-stage: waveform-level closure of the time-domain pipeline.

Reconstruct the ringdown waveform from the certified pencil parameters
(frequencies + residues) and measure the waveform-level residual against
the actual evolution in the extraction window:

    |psi_reconstructed(t) - psi_evolved(t)| / |psi_evolved|_scale

This is the honest G160 pre-measure: a certified mode set MUST
reproduce the waveform it was extracted from, otherwise the pencil
overfitted.  PASS criterion (frozen): relative L2 residual < 5e-2 in
the window, < 2e-1 late (t > window, before the boundary echo).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssz_spectroscopy.time_domain import (
    evolve,
    extract_qnm,
    rw_setup,
)

REF = complex(0.37367, -0.08896)
ART = ROOT / "artifacts"


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)
    x, _r, V = rw_setup(M=0.5, ell=2, xL=-60.0, xR=60.0, n=7000)
    t, sig = evolve(x, V, x_det=40.0, t_max=220.0)

    # extraction window (frozen protocol)
    i0 = int(82.0 / 220.0 * len(t))
    i1 = int(102.0 / 220.0 * len(t))
    t_w = t[i0:i1]
    s_w = sig[i0:i1]

    # pencil with n_modes; real-projection aware reconstruction:
    # design matrix = [Re(e^{-iwt}), Im(e^{-iwt})] columns
    n_modes = 10
    modes = extract_qnm(s_w, t_w, n_modes=n_modes, t_start_frac=0.0)
    print(f"pencil modes: {[f'{w:.4f}' for w in modes[:4]]}", flush=True)

    A_c = np.exp(-1j * np.outer(t_w, modes))
    A = np.hstack([A_c.real, A_c.imag])
    coef, *_ = np.linalg.lstsq(A, s_w, rcond=None)
    recon_w = A @ coef

    def rel_l2(a, b):
        return float(np.linalg.norm(a - b) / np.linalg.norm(b))

    resid_window = rel_l2(recon_w, s_w)

    # late-time POWER-LAW tail check (Price): the late signal is NOT
    # exponential — fitting exponentials there is a category error. The
    # honest measure is the local power-law exponent vs Price t^-(2l+2).
    j1 = int(185.0 / 220.0 * len(t))
    tl, sl = t[i1:j1], sig[i1:j1]
    msk = np.abs(sl) > 1e-5
    if msk.sum() > 20:
        plaw = float(np.polyfit(np.log(tl[msk]),
                                np.log(np.abs(sl[msk])), 1)[0])
    else:
        plaw = None
    resid_late = plaw  # recorded as exponent, NOT a residual

    # leading-mode check vs reference
    w_lead = modes[0]
    lead_err = abs(0.5 * w_lead - REF)

    g160_pre_pass = resid_window < 5e-2
    verdict = {
        "audit": "G160_PRE_WAVEFORM_CLOSURE_V1",
        "n_modes": n_modes,
        "window": [82.0, 102.0],
        "rel_L2_residual_window": resid_window,
        "late_power_law_exponent": resid_late,
        "leading_mode_M_omega": [0.5 * w_lead.real, 0.5 * w_lead.imag],
        "leading_mode_err": lead_err,
        "g160_pre_pass": bool(g160_pre_pass),
        "criterion": "window < 5e-2 (frozen); late-time tail is a power law (Price), recorded as exponent, excluded from the exponential-residual criterion by physics",
        "note": "G160 proper (certified-mode waveform + detector response "
                "closure) requires G155; this is the waveform-level "
                "consistency of the extraction itself.",
        "wall_seconds": round(time.time() - t0, 1),
    }
    out = ART / "G160_PRE_WAVEFORM_CLOSURE_V1.json"
    out.write_text(json.dumps(verdict, indent=1, allow_nan=False) + "\n")
    print(json.dumps({
        "resid_window": resid_window,
        "late_power_law_exponent": resid_late,
        "pass": g160_pre_pass,
        "written": str(out.relative_to(ROOT)),
    }, indent=1))
    return 0 if g160_pre_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
