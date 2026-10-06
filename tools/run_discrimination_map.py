#!/usr/bin/env python3
"""SSZ_DISCRIMINATION_MAP_V1 — targeted experiment design (fail-closed skeleton).

Purpose (Lino's escalation step "targeted discriminating experiment"):
    theta* = argmax_theta |O_SSZ(theta) - O_GR(theta)| / sigma_O(theta)

This tool computes NOTHING today by design: no certified QNM catalogue
exists yet (upstream B8/B6/Jost+ECS open).  It declares the observable
space, the required instrument-precision inputs, and the scoring rule,
and refuses to produce a map until the frozen SSZ catalogue AND a
reference GR catalogue (same M, same units) exist.

Observable space (each evaluated as Delta/sigma at scan points theta):
  * QNM frequency ratios      omega_221/omega_220, omega_330/omega_220
  * damping hierarchy         tau_1/tau_0
  * mode visibility           relative excitation amplitudes (declared
                              source model)
  * photon-ring properties    Lyapunov exponent, echo delay (if the SSZ
                              geometry produces an inner structure)
  * combined phase/redshift   the transport-chain observables already
                              certified on the Sagnac side

Instrument priors (declared, replaceable — never tuned post hoc):
  * LIGO/Virgo/KAGRA ringdown SNR scaling
  * LISA massive-black-hole ringdown
  * EHT photon-ring resolution
  * pulsar timing / redshift experiments

Protocol: the map is computed ONLY from frozen catalogues; instrument
priors are frozen BEFORE the scan; the output names, for each theta,
the best observable and the required precision — experiment design,
not a fit.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/SSZ_DISCRIMINATION_MAP_V1.json"

REQUIRED_INPUTS = {
    "ssz_catalog": "artifacts/SSZ_PREDICTION_REGISTRY_V1.json must be SEALED "
                    "with values (upstream chain closed)",
    "gr_catalog": "reference GR/Kerr catalogue, same mass grid, same units, "
                   "independently sourced (e.g. Berti_cardoso_will tables)",
    "instrument_priors": "sigma_O(theta) per observable, frozen before the scan",
}


def main() -> int:
    reg = ROOT / "artifacts/SSZ_PREDICTION_REGISTRY_V1.json"
    status = json.loads(reg.read_text()).get("status", "MISSING") if reg.exists() else "MISSING"

    out = {
        "audit": "SSZ_DISCRIMINATION_MAP_V1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "BLOCKED_PENDING_CATALOGS",
        "registry_status": status,
        "scoring_rule": (
            "theta* = argmax_theta |O_SSZ(theta) - O_GR(theta)| / sigma_O(theta); "
            "the map reports per-theta the best observable and the required "
            "precision for high-discrimination detection."),
        "observable_space": [
            "ratio_omega_221_220", "ratio_omega_330_220",
            "damping_hierarchy_tau1_tau0",
            "mode_visibility_relative_amplitudes",
            "photon_ring_lyapunov_and_echo_delay",
            "combined_phase_redshift_relation",
        ],
        "instrument_priors_declared": [
            "LVK ringdown SNR scaling", "LISA MBH ringdown",
            "EHT photon-ring resolution", "pulsar timing / redshift",
        ],
        "required_inputs": REQUIRED_INPUTS,
        "blocking": {
            "registry_status": status,
            "needed": ("SEALED registry (values present) + independent GR "
                        "reference catalogue + frozen instrument priors"),
        },
        "anti_flexibility_clause": (
            "SSZ must win with its FIXED structure, not flexibility: the "
            "comparison runs against GR/Kerr AND generic parametrized "
            "deviation models simultaneously. Beating one GR fit alone "
            "does not establish SSZ."),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"status": out["status"],
                       "observables_declared": len(out["observable_space"]),
                       "blocking": out["blocking"]["needed"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
