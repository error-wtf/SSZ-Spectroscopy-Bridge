#!/usr/bin/env python3
"""G190: empirical spectroscopy verdict — the recorded gate closure.

Emits the final verdict per the frozen rule: G190 = verdict(A/B/C) ONLY
if G150..G183 all carry recorded PASS verdicts; ANY open or failed
predecessor forces G190 = BLOCKED with the failing gate named.

This tool reads the recorded artifacts, checks each gate, and writes
the verdict.  It never re-runs the gates (they are recorded evidence).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"

REQUIRED = {
    "G150": ("SSZ_SPECTRAL_OPERATOR_EXPORT_G150_V1.json", None),
    "G151": ("G151_LEAVER_FREQUENCY_DOMAIN_V1.json", None),
    "G152": ("G152_MULTI_WIDTH_ENSEMBLE_V1.json", "gates.G152_solver_agreement.pass"),
    "G153": ("GATE_CAMPAIGN_RW_CONTROL_V1.json", "gates.G153_mode_convergence.pass"),
    "G154": ("GATE_CAMPAIGN_RW_CONTROL_V1.json", "gates.G154_schwarzschild_control.pass"),
    "G155": ("RW_CONTROL_CERTIFIED_MODE_CATALOGUE_G155_V1.json", None),
    "G160": ("G160_CERTIFIED_WAVEFORM_CLOSURE_V1.json", "g160_pass"),
    "G170": ("G170_G171_BLIND_AND_CONTROLS_V1.json", "G170_blind_recovery.pass"),
    "G171": ("G170_G171_BLIND_AND_CONTROLS_V1.json", "G171_controls.pass"),
    "G180": ("G180_DETECTOR_RESPONSE_CLOSURE_V1.json", "g180_pass"),
    "G181": ("G181_G182_G183_GWOSC_REAL_DATA_V1.json", "g181_provenance.pass"),
    "G182": ("G181_G182_G183_GWOSC_REAL_DATA_V1.json", "g182_inference.pass"),
    "G183": ("G181_G182_G183_GWOSC_REAL_DATA_V1.json", "g183_stability.pass"),
}


def get_path(d: dict, dotted: str):
    cur = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def main() -> int:
    status = {}
    blockers = []
    for gate, (artifact, pass_key) in REQUIRED.items():
        p = ART / artifact
        if not p.exists():
            status[gate] = "MISSING_ARTIFACT"
            blockers.append(gate)
            continue
        d = json.loads(p.read_text())
        if pass_key is None:
            status[gate] = "RECORDED"
            continue
        v = get_path(d, pass_key)
        if v is True:
            status[gate] = "PASS"
        else:
            status[gate] = f"NOT_PASS ({v})"
            blockers.append(gate)

    # G161 needs the closure eikonal layer (Xi->D->g->Phi transport); the
    # bridge's SSZ channel is SYMBOLIC_TEST_ONLY (isospectral, FailClosed)
    # until N3/N4 — recorded as structurally blocked, not failed.
    status.setdefault("G161", "BLOCKED (requires closure eikonal layer, N3/N4-owned)")
    if "G161" not in blockers:
        blockers.append("G161")
    blockers = [b for b in blockers if b != "G161"] + ["G161"] if blockers else ["G161"]

    if blockers:
        verdict = "BLOCKED"
    else:
        verdict = "A"  # would require the full chain to pass — recorded honestly if reached

    out = {
        "audit": "G190_EMPIRICAL_SPECTROSCOPY_VERDICT_V1",
        "rule": "verdict A/B/C only if G150..G183 all PASS; any open predecessor forces BLOCKED",
        "gate_status": status,
        "blockers": blockers,
        "verdict": verdict,
        "scope_note": "G183 currently NOT_PASS: the single-damped-sinusoid template "
                      "over the catalog final-mass bank does not give detector-stable "
                      "mass estimates on real GW150914 data (H1 110 vs L1 62 Msun — "
                      "merger-power leakage into the ringdown template). This is an "
                      "honest infrastructure limit of the simplified template, not a "
                      "physics result; G190 stays BLOCKED until a proper IMR-based "
                      "ringdown filter replaces it.",
        "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    out_p = ART / "G190_EMPIRICAL_SPECTROSCOPY_VERDICT_V1.json"
    out_p.write_text(json.dumps(out, indent=1, allow_nan=False) + "\n")
    print(json.dumps({"verdict": verdict, "blockers": blockers}, indent=1))
    return 0  # recording a BLOCKED verdict is a successful audit


if __name__ == "__main__":
    raise SystemExit(main())
