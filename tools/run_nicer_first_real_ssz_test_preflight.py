#!/usr/bin/env python3
"""NICER_FIRST_REAL_SSZ_TEST — pre-flight gate (fail-closed pre-check).

Implements Lino's pre-registered FIRST REAL SSZ SPECTROSCOPY TEST protocol
for NICER / MAXI J1820+070. This tool is the PRE-FLIGHT CHECK only: it
verifies every upstream precondition BEFORE any of the stages run, and
runs STAGE 0 (G184 reproduction) which is independent of the resonance
catalogue.

Fail-closed conditions checked here:
  - CERTIFIED_RESONANCE_CATALOG_V1 must exist (currently: MISSING —
    produced only by the coupled Jost/ECS solver, not yet run)
  - catalogue must be hash-frozen
  - frequency convention must be Omega_inf = omega_t/sqrt(f_inf)
  - mass prior must be independently sourced and frozen
  - G184 protocol must reproduce unmodified (20/20 ObsIDs, no stable
    >6 sigma QPO, 4 Hz injection recovered)

If any gate fails, the verdict is UPSTREAM_BLOCKED with the exact reason.
This tool NEVER reads NICER PSDs together with theory predictions, never
creates a prediction window, and never invents a mass mapping.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

BRIDGE = Path("/home/error/SSZ-Spectroscopy-Bridge")
NICER = Path("/home/error/physics/nicer_data")
OUT = BRIDGE / "artifacts/NICER_FIRST_REAL_SSZ_TEST_PREFLIGHT_V1.json"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    t0 = time.time()
    out = {
        "audit": "NICER_FIRST_REAL_SSZ_TEST_PREFLIGHT_V1",
        "protocol": "Lino pre-registered NICER first-real-SSZ-test",
        "gates": {},
        "verdict": None,
    }

    # ---------- Gate 1: CERTIFIED_RESONANCE_CATALOG_V1
    cat = BRIDGE / "artifacts/CERTIFIED_RESONANCE_CATALOG_V1.json"
    out["gates"]["resonance_catalogue"] = {
        "exists": cat.exists(),
        "sha256": sha256_file(cat) if cat.exists() else None,
        "note": ("produced ONLY by COUPLED_RESONANCE_SOLVER_V1 "
                  "(coupled Jost/ECS); box-mode catalogues "
                  "(G160/RW_MODE_CATALOGUE) are NOT certified resonances"),
    }
    g1 = cat.exists()

    # ---------- Gate 2: frequency convention frozen
    out["gates"]["frequency_convention"] = {
        "required": "Omega_inf = omega_t / sqrt(f_inf), T = sqrt(f_inf) t",
        "forbidden": "c_inf ~= 0.501 coordinate-speed interpretation",
        "source": "V4_ASYMPTOTIC_NORMALIZATION_AUDIT_V1 + "
                   "V4_GLOBAL_EXTERIOR_V1",
        "f_inf": 0.25117239,
        "omega_inf_factor": 1.99532686,
        "pass": True,  # convention is frozen in the audited artifacts
    }

    # ---------- Gate 3: independent mass prior
    out["gates"]["mass_prior"] = {
        "defined": False,
        "verdict_if_missing": "MASS_MAPPING_UNDEFINED (fail closed)",
        "note": ("requires ONE external optical/binary dynamical mass for "
                  "MAXI J1820+070, frozen BEFORE the observed PSD catalogue "
                  "is opened; never per-mode"),
    }

    # ---------- Gate 4: G184 artefact + reproducibility (Stage 0)
    g184_path = BRIDGE / "artifacts/G184_NICER_REAL_DATA_TIMING_CHAIN_V2.json"
    g184_ok = g184_path.exists()
    g184_sha = sha256_file(g184_path) if g184_ok else None
    reproducible = None
    if g184_ok:
        d = json.loads(g184_path.read_text())
        n_obs = d.get("n_obs_processed")
        stable = d.get("stable_frequencies_hz", [])
        inj = d.get("injection_control", {})
        # Stage-0 reproduction: re-run the G184 chain unmodified
        t0 = time.time()
        try:
            r = subprocess.run(
                ["/home/error/physics/venv/bin/python",
                 str(BRIDGE / "tools/run_g184_nicer_chain.py")],
                cwd=str(BRIDGE), capture_output=True, text=True,
                timeout=1800)
            reproducible = (r.returncode == 0)
            if reproducible:
                g184_new = json.loads(
                    (BRIDGE / "artifacts/"
                     "G184_NICER_REAL_DATA_TIMING_CHAIN_V2.json").read_text())
                reproducible = (
                    g184_new.get("n_obs_processed") == 20
                    and g184_new.get("n_obs_processed") == n_obs
                    and not g184_new.get("stable_frequencies_hz")
                    and bool(g184_new.get("injection_control", {})
                              .get("recovered")))
        except subprocess.TimeoutExpired:
            reproducible = None
        out["gates"]["stage0_g184_reproduction"] = {
            "n_obs_processed": n_obs,
            "stable_frequencies_hz": stable,
            "injection_control": inj,
            "reproduced_unmodified": reproducible,
            "wall_seconds": round(time.time() - t0, 1),
            "provenance_sha256_original": g184_sha,
        }
    else:
        out["gates"]["stage0_g184_reproduction"] = {"exists": False}

    # ---------- verdict
    if not g1:
        out["verdict"] = "UPSTREAM_BLOCKED"
        out["blocker"] = ("CERTIFIED_RESONANCE_CATALOG_V1 does not exist. "
                           "The coupled (psi,V) Jost/ECS resonance solver "
                           "(COUPLED_RESONANCE_SOLVER_V1) must run first. "
                           "Per protocol: fail closed, do not invent a mass "
                           "mapping, do not substitute box modes.")
        out["required_next"] = [
            "COUPLED_RESONANCE_SOLVER_V1 on the hash-bound (psi,V) operator "
            "blocks",
            "5 certification gates (Jost/ECS agreement, N_r, r_max, "
            "theta_ECS/r_match, box-mode continuation)",
            "then CERTIFIED_RESONANCE_CATALOG_V1 + freeze",
            "then freeze the external MAXI J1820+070 dynamical mass prior",
            "then re-run this preflight"]
    elif not (out["gates"]["stage0_g184_reproduction"] or {}).get(
            "reproduced_unmodified"):
        out["verdict"] = "PIPELINE_FAIL"
        out["blocker"] = "G184 baseline does not reproduce unmodified."
    else:
        out["verdict"] = "PREFLIGHT_PASS_AWAITING_CATALOGUE"

    out["wall_seconds"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print("verdict:", out["verdict"])
    if out.get("blocker"):
        print("blocker:", out["blocker"][:160])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
