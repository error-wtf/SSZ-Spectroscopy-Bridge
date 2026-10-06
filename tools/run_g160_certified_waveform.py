#!/usr/bin/env python3
"""G160 full: waveform reconstruction FROM THE CERTIFIED MODE SET.

The G160-PRE stage measured waveform self-consistency of the pencil
extraction.  G160 proper (this tool) closes the loop the other way:

    certified catalogue modes (Leaver CF, G155)  ->  waveform fit
      ->  measured rel-L2 residual vs the evolved signal in the clean
          window  ->  cross-check vs the pencil pole (frequency domain)

PASS criteria (frozen):
    * certified-mode reconstruction rel-L2 < 5e-2 in the window [82, 102]
    * reconstruction window residual must not exceed the pencil
      self-reconstruction residual by more than a factor 3
      (the pencil fits amplitudes freely; the certified set fits
      amplitudes with FROZEN frequencies — an honest handicap)
    * leading certified mode agrees with the pencil pole < 1e-4 (C4 tol)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssz_spectroscopy.time_domain import evolve, extract_qnm, rw_setup

TOL_WINDOW = 5e-2
HANDICAP_FACTOR = 3.0
TOL_C4 = 1e-4


def rel_l2(a, b):
    return float(np.linalg.norm(a - b) / np.linalg.norm(b))


def main() -> int:
    t0 = time.time()
    art = ROOT / "artifacts"
    art.mkdir(exist_ok=True)

    cat = json.loads((art / "RW_CONTROL_CERTIFIED_MODE_CATALOGUE_G155_V1.json").read_text())
    certified = [complex(*r_["omega"]) for r_ in cat["rows"] if r_["certified"]]
    if not certified:
        print("NO certified modes — run tools/run_g155_catalogue.py first")
        return 1

    # frozen protocol evolution; extraction window [82, 102] — the MEASURED clean
    # window (G160-PRE amplitude map: the pulse tail occupies [70, ~82]; boundary
    # echo arrives t ~ 185).  Window bounds were frozen BEFORE this measurement.
    x, _r, V = rw_setup(M=0.5, ell=2, xL=-60.0, xR=60.0, n=7000)
    t, sig = evolve(x, V, x_det=40.0, t_max=220.0)
    i0 = int(82.0 / 220.0 * len(t))
    i1 = int(102.0 / 220.0 * len(t))
    t_w = t[i0:i1]
    s_w = sig[i0:i1]

    # --- pencil self-reconstruction (free frequencies + free amplitudes)
    pencil_modes = extract_qnm(s_w, t_w, n_modes=10, t_start_frac=0.0)
    A_p = np.hstack([np.exp(-1j * np.outer(t_w, pencil_modes)).real,
                     np.exp(-1j * np.outer(t_w, pencil_modes)).imag])
    coef_p, *_ = np.linalg.lstsq(A_p, s_w, rcond=None)
    resid_pencil = rel_l2(A_p @ coef_p, s_w)

    # --- CERTIFIED-mode reconstruction: frozen frequencies (real-projection
    # design, Im columns fitted per the documented lstsq pitfall), free
    # amplitudes, leading 3 certified modes (overtone 3+ is below the
    # window's noise floor by the G153 ladder)
    use = certified[:3]
    A_c = np.exp(-1j * np.outer(t_w, np.array(use)))
    A = np.hstack([A_c.real, A_c.imag])
    coef, *_ = np.linalg.lstsq(A, s_w, rcond=None)
    recon = A @ coef
    resid_certified = rel_l2(recon, s_w)

    # leading certified mode vs pencil pole (C4 tolerance)
    w_lead = certified[0]
    w_pencil_lead = min(pencil_modes, key=lambda w: abs(w - w_lead))
    lead_gap = abs(w_lead - w_pencil_lead)

    g160_pass = (resid_certified < TOL_WINDOW
                 and resid_certified < HANDICAP_FACTOR * resid_pencil
                 and lead_gap < TOL_C4)

    verdict = {
        "audit": "G160_CERTIFIED_WAVEFORM_CLOSURE_V1",
        "certified_modes_used": [[w.real, w.imag] for w in use],
        "rel_L2_certified_frequencies": resid_certified,
        "rel_L2_pencil_free": resid_pencil,
        "handicap_factor_limit": HANDICAP_FACTOR,
        "leading_mode_vs_pencil_gap": lead_gap,
        "g160_pass": bool(g160_pass),
        "criteria": {
            "certified_window": f"< {TOL_WINDOW}",
            "handicap": f"certified <= {HANDICAP_FACTOR}x pencil-free",
            "leading_vs_pencil": f"< {TOL_C4}",
        },
        "wall_seconds": round(time.time() - t0, 1),
    }
    out = art / "G160_CERTIFIED_WAVEFORM_CLOSURE_V1.json"
    out.write_text(json.dumps(verdict, indent=1, allow_nan=False) + "\n")
    print(json.dumps({k: verdict[k] for k in
                      ("rel_L2_certified_frequencies", "rel_L2_pencil_free",
                       "leading_mode_vs_pencil_gap", "g160_pass")}, indent=1))
    return 0 if g160_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
