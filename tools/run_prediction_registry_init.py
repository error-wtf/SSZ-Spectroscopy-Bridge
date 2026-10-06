#!/usr/bin/env python3
"""SSZ_PREDICTION_REGISTRY_V1 — the pre-registration contract.

Position in the pipeline (Lino's frozen roadmap):
    S -> B8 -> F.4 -> B6 -> Jost+ECS -> CATALOG FREEZE -> REGISTRY FREEZE
    -> blind real-data test -> SSZ-vs-GR -> out-of-sample -> multi-event
    -> cross-observable -> adversarial phase.

This tool CREATES the registry in the only state that is honest today:
status = PENDING, every predicted quantity null, every falsification bound
declared but unfilled.  The registry becomes SEALABLE only when the
upstream chain reports CERTIFIED — until then any attempt to fill in
numbers is blocked BY DESIGN.  After sealing, the file is hash-chained:
each later modification must reference the previous seal hash, so the
git history alone proves whether predictions were edited after seeing
data.

Fail-closed rules (declared now, before any QNM exists):
  * PENDING: fill_from_catalog() refuses.
  * SEALED: any mutation without a valid prior-seal hash refuses.
  * mode values are dimensionless M*omega (GR-comparable), with the mass
    scaling declared separately so the blind test cannot tune mass post hoc.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/SSZ_PREDICTION_REGISTRY_V1.json"
CLOSURE = Path("/home/error/physics/clones/SSZ_FULL_CLOSURE")

# The declared upstream chain — every entry must be CLOSED (or an explicitly
# OPEN documented blocker) before the registry may be sealed.
UPSTREAM_CHAIN = [
    {"gate": "S",       "artifact": "closure:data/generated/spectral/V4_S_TERM_PROVENANCE.json",
     "state": "CLOSED"},
    {"gate": "B8",      "artifact": "bridge:artifacts/B8_SECTOR_TRACKING_V4_V1.json",
     "state": "OPEN", "blocker": "sector attribution requires B6 physical BCs "
                                  "(mass guard fired: indefinite B on V4 branch)"},
    {"gate": "F.4",     "artifact": "closure:data/generated/spectral/"
                                     "F4_FINITE_L_HEALTH_V4_S_PROJECTED_V1.json",
     "state": "OPEN", "blocker": "negative kinetic channel, attribution pending B8/B6"},
    {"gate": "B6",      "artifact": None, "state": "OPEN", "blocker": "not started"},
    {"gate": "Jost+ECS", "artifact": None, "state": "OPEN", "blocker": "not started"},
]

# The predicted quantities, declared by NAME and MEANING now — values only
# after catalog freeze.  Dimensionless: omega in units of 1/M of the
# perturbed background; the mass-scaling convention is fixed here so a
# later mass fit cannot move the target.
PREDICTED_QUANTITIES = {
    "mode_220": "fundamental l=2,n=0 QNM, Re/Im in M-units",
    "mode_221": "first overtone l=2,n=1",
    "mode_330": "l=3,n=0",
    "tau_220": "damping time tau = -1/Im(omega) in M-units",
    "Q_220": "quality factor Q = Re(omega) / (-2 Im(omega))",
    "ratio_221_220": "overtone ratio Re(omega_221)/Re(omega_220)",
    "ratio_330_220": "Re(omega_330)/Re(omega_220)",
    "residue_hierarchy": "mode-dependent excitation coefficients for the "
                          "declared source model (frozen before data)",
    "mass_scaling_law": "declared scaling of the spectrum with M (must be "
                         "fixed before the blind test; no post-hoc tuning)",
    "falsification_bounds": "per-quantity deviation from SSZ prediction that "
                             "counts as falsification, frozen with the seal",
}

SEAL_INPUTS = [
    "closure_commit_sha",
    "bridge_commit_sha",
    "spectro_commit_sha",
    "v4_branch_params",
    "operator_export_sha256",
    "catalog_sha256",
]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git_head(repo: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo,
                          capture_output=True, text=True,
                          check=False).stdout.strip()


def chain_states() -> list[dict]:
    out = []
    for step in UPSTREAM_CHAIN:
        entry = dict(step)
        art = step["artifact"]
        if art and ":" in art:
            repo, _, rel = art.partition(":")
            base = {"closure": CLOSURE,
                    "bridge": Path("/home/error/SSZ-Transport-Bridge"),
                    "spectro": ROOT}[repo]
            entry["artifact_exists"] = (base / rel).exists()
        else:
            entry["artifact_exists"] = False
        out.append(entry)
    return out


def main() -> int:
    registry = {
        "audit": "SSZ_PREDICTION_REGISTRY_V1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PENDING",
        "semantics": (
            "Pre-registration contract. Values are filled ONLY at catalog "
            "freeze, sealed ONLY after the upstream chain reports CLOSED, and "
            "never edited after data contact. Hash-chained seals; the git "
            "history is the tamper evidence."),
        "upstream_chain": chain_states(),
        "sealable": False,
        "seal_inputs_declared": SEAL_INPUTS,
        "predicted_quantities": {k: {"meaning": v, "value": None,
                                      "falsification_bound": None}
                                  for k, v in PREDICTED_QUANTITIES.items()},
        "mass_scaling_convention": (
            "omega is reported in units of 1/M_ref with M_ref declared at "
            "seal time; the blind test receives omega*M as the frozen target "
            "and may only convolve with DECLARED mass priors."),
        "evaluation_protocol": {
            "step1_blind_test": "frozen SSZ modes vs frozen observed catalog; "
                                 "scored jointly on f, tau, Q, relative amplitudes",
            "step2_ssz_vs_gr": "same data, same noise model, same astrophysical "
                                "priors; Bayes factor or information criterion "
                                "+ posterior predictive checks",
            "step3_out_of_sample": "pipeline hash frozen after the development "
                                    "set; new events scored with UNCHANGED thresholds",
            "step4_multi_event": "hierarchical p(theta_SSZ | d_1..d_N); dimensionless "
                                  "mode relations must hold across masses",
            "step5_cross_observable": "photon ring, redshift, orbital frequencies, "
                                       "phase/JIF, timing — one geometry, many observables",
            "step6_adversarial": "maximally attackable: un-fitted predictions "
                                  "(fixed mode ratios, extra damping branches, "
                                  "residue hierarchy, ring-structure relations)",
        },
        "outcome_semantics": {
            "worse_than_data_or_GR": "this member / this dynamics FALLS",
            "indistinguishable_from_GR": "current data cannot separate",
            "robust_extra_predictions": "declare new independent tests — NOT "
                                         "'SSZ confirmed'",
        },
    }

    # honest chain audit: sealable only if everything is CLOSED
    all_closed = all(s["state"] == "CLOSED" for s in registry["upstream_chain"])
    registry["sealable"] = all_closed
    open_items = [s["gate"] for s in registry["upstream_chain"]
                  if s["state"] != "CLOSED"]

    OUT.write_text(json.dumps(registry, indent=1, ensure_ascii=False) + "\n")
    digest = sha256_file(OUT)
    print(json.dumps({
        "status": registry["status"],
        "sealable": registry["sealable"],
        "open_gates": open_items,
        "predicted_quantities": len(PREDICTED_QUANTITIES),
        "registry_sha256": digest,
    }, indent=1))
    print("\nRegistry created in PENDING state — honest for today: the "
          "upstream chain (B8/B6/F.4/Jost+ECS) is open. fill/seal tools "
          "refuse until the chain reports CLOSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
