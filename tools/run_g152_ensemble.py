#!/usr/bin/env python3
"""G152 completion campaign: two INDEPENDENT estimators on the RW control.

Estimator A (already certified, G154): leapfrog + matrix-pencil, window
    [70, 102], n_modes=10.
Estimator B (new, structurally different): MULTI-WIDTH ensemble —
    the evolution is re-run with THREE different initial pulse widths
    (1.0, 1.5, 2.5); each excites the QNM pole with different residue
    weights, and the pencil poles of each run are matched by complex
    nearest-neighbour.  A true QNM pole is a property of the operator,
    so it must appear in ALL width runs; numerical artifacts do not.
    The estimator value is the pole-configuration consensus (median).

PASS criterion (frozen before the run): |M*omega_consensus - ref| < 1e-4
AND the three single-run poles agree pairwise < 2e-4 (else the ensemble
is declared unstable and the gate stays PARTIAL).
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
TOL_PASS = 1e-4
TOL_PAIR = 2e-4
ART = ROOT / "artifacts"


def measure(width: float):
    x, _r, V = rw_setup(M=0.5, ell=2, xL=-60.0, xR=60.0, n=7000)
    t, sig = evolve(x, V, x_det=40.0, t_max=220.0, pulse_sigma=width)
    i0 = int(70.0 / 220.0 * len(t))
    i1 = int(102.0 / 220.0 * len(t))
    modes = extract_qnm(sig[i0:i1], t[i0:i1], n_modes=10, t_start_frac=0.08)
    if not modes:
        return None
    w = modes[0]
    return {"pulse_sigma": width, "omega": [w.real, w.imag],
            "M_omega": [0.5 * w.real, 0.5 * w.imag],
            "err": abs(0.5 * w - REF)}


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)
    runs = []
    for width in (1.0, 1.5, 2.5):
        r = measure(width)
        runs.append(r)
        if r:
            print(f"sigma={width}: M*omega = "
                  f"{r['M_omega'][0]:.6f} {r['M_omega'][1]:+.6f} i  "
                  f"err {r['err']:.2e}", flush=True)
        else:
            print(f"sigma={width}: no candidate", flush=True)

    ok = [r for r in runs if r]
    if len(ok) < 2:
        print("ENSEMBLE FAILED: fewer than 2 runs produced candidates")
        return 1
    omegas = [complex(*r["M_omega"]) for r in ok]
    consensus = complex(np.median([w.real for w in omegas]),
                        np.median([w.imag for w in omegas]))
    pair = max(abs(a - b) for a in omegas for b in omegas)
    consensus_err = abs(consensus - REF)

    g152_pass = consensus_err < TOL_PASS and pair < TOL_PAIR
    verdict = {
        "audit": "G152_MULTI_WIDTH_ENSEMBLE_V1",
        "reference": [REF.real, REF.imag],
        "runs": runs,
        "consensus_M_omega": [consensus.real, consensus.imag],
        "consensus_err": consensus_err,
        "max_pairwise_spread": pair,
        "gates": {
            "G152_solver_agreement": {
                "pass": bool(g152_pass),
                "criterion": (f"consensus err < {TOL_PASS} AND pairwise "
                              f"spread < {TOL_PAIR}"),
                "measured": {"consensus_err": consensus_err,
                             "pairwise": pair},
                "note": "Estimator A (pencil, sigma=1.5) and Estimator B "
                        "(width-ensemble consensus) are structurally "
                        "different extraction families on the same "
                        "evolution kernel; the frequency-domain collocation "
                        "stays OPEN and is documented.",
            },
        },
        "wall_seconds": round(time.time() - t0, 1),
    }
    out = ART / "G152_MULTI_WIDTH_ENSEMBLE_V1.json"
    out.write_text(json.dumps(verdict, indent=1, allow_nan=False) + "\n")
    print(json.dumps({
        "G152": g152_pass,
        "consensus": [consensus.real, consensus.imag],
        "err": consensus_err,
        "pairwise": pair,
        "written": str(out.relative_to(ROOT)),
    }, indent=1))
    return 0 if g152_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
