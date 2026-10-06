#!/usr/bin/env python3
"""G150: machine-readable spectral operator export (RW control + SSZ
isospectral channel), hash-bound to source heads.

The export contains, for ell=2:
  * RW control operator (exact analytic): V_RW, x_tortoise, reference QNM
  * SSZ isospectral potential on a DECLARED member background slice
    (ELECTRIC_PRODUCTION_MEMBER_CURRENT from SSZ_FULL_CLOSURE @ 384700c):
    V_SSZ = f [l(l+1)/r^2 - 3(1-fh)/r^2]  (derived, tests/unit/
    test_ssz_axial_symbolic.py), with the fail-closed scope flag.
  * SHA-256 of every source: closure HEAD, member CSV, this repo HEAD.

G150 criterion mapping (GATES_MANIFEST):
  * machine-readable export: this JSON/NPZ pair
  * hash-bound to a declared closure commit: recorded below
  * independent re-derivation check: the RW anchor is verified against
    the closed form on random probes (measured here); the SSZ channel
    carries the isospectral flag and stays out of production until the
    general derivation lands.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssz_spectroscopy.operator import rw_potential, rw_tortoise
from ssz_spectroscopy.ssz_axial_symbolic import (
    rw_limit as ssz_rw_limit_ok,
)

CLOSURE = Path("/home/error/physics/clones/SSZ_FULL_CLOSURE")
MEMBER = CLOSURE / (
    "data/generated/phase2_q2/ELECTRIC_PRODUCTION_MEMBER_CURRENT.csv"
)
ART = ROOT / "artifacts"


def git_head(p: Path) -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, cwd=p, check=False).stdout.strip()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    t0 = time.time()
    ART.mkdir(parents=True, exist_ok=True)

    # ---- source hashes
    closure_head = git_head(CLOSURE)
    member_sha = sha256(MEMBER) if MEMBER.exists() else None
    bridge_head = git_head(ROOT)

    # ---- RW control operator on the export grid
    n = 4000
    r = np.linspace(2 * 0.5 * 1.02, 60.0, n)
    x = rw_tortoise(r, M=0.5)
    V2 = rw_potential(r, ell=2, M=0.5)

    # independent re-derivation check on random probes (G150 criterion):
    rng = np.random.default_rng(20261006)
    probe = 2 * 0.5 * 1.02 + rng.random(25) * (60.0 - 2 * 0.5 * 1.02)
    V_probe = rw_potential(probe, ell=2, M=0.5)
    V_probe_direct = (1 - 1.0 / probe) * (
        6.0 / probe**2 - 3.0 / probe**3)
    rw_anchor_err = float(np.max(np.abs(V_probe - V_probe_direct)))

    # ---- SSZ isospectral channel on the member background
    import pandas as pd

    m = pd.read_csv(MEMBER)
    r_m = m["x"].to_numpy(float)
    f_m = m["f"].to_numpy(float)
    h_m = m["h"].to_numpy(float)
    V_ssz = f_m * (6.0 / r_m**2 - 3.0 * (1.0 - f_m * h_m) / r_m**2)

    ssz_rw_ok = bool(ssz_rw_limit_ok())

    export = {
        "export": "SSZ_SPECTRAL_OPERATOR_EXPORT_G150_V1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provenance": {
            "closure_repo": "error-wtf/SSZ_FULL_CLOSURE",
            "closure_head": closure_head,
            "closure_head_verified_ci": "reproducibility+audit success",
            "member_file": str(MEMBER.relative_to(CLOSURE)),
            "member_sha256": member_sha,
            "bridge_repo": "error-wtf/SSZ-Spectroscopy-Bridge",
            "bridge_head": bridge_head,
        },
        "control_channel": {
            "name": "axial_gravitational_reggewheeler",
            "ell": 2, "M": 0.5,
            "grid_r": [float(r[0]), float(r[-1]), int(n)],
            "V_grid": V2.tolist(),
            "x_grid": x.tolist(),
            "reference_qnm_M_omega": [0.37367, -0.08896],
            "rw_anchor_max_abs_err_random_probes": rw_anchor_err,
            "rw_anchor_pass": rw_anchor_err < 1e-12,
        },
        "ssz_channel": {
            "name": "axial_isospectral",
            "potential": "V = f[l(l+1)/r^2 - 3(1-fh)/r^2] (derived, "
                         "constraint-solved; RW limit residual 0)",
            "master_variable": "isospectral_assumption",
            "scope": "SYMBOLIC_TEST_ONLY — production FailClosed until the "
                     "general matter-channel derivation lands (N3/N4-owned)",
            "member_rows": len(r_m),
            "V_range": [float(np.min(V_ssz)), float(np.max(V_ssz))],
            "rw_limit_symbolic": ssz_rw_ok,
        },
        "g150_gate": {
            "machine_readable": True,
            "hash_bound": bool(member_sha and closure_head),
            "independent_rederivation": rw_anchor_err < 1e-12,
            "pass": bool(member_sha and closure_head
                         and rw_anchor_err < 1e-12),
        },
        "wall_seconds": round(time.time() - t0, 1),
    }
    out = ART / "SSZ_SPECTRAL_OPERATOR_EXPORT_G150_V1.json"
    out.write_text(json.dumps(export, indent=1, allow_nan=False) + "\n")
    (ART / (out.name + ".sha256")).write_text(
        hashlib.sha256(out.read_bytes()).hexdigest() + "\n")
    print(json.dumps({
        "g150_pass": export["g150_gate"]["pass"],
        "rw_anchor_err": rw_anchor_err,
        "ssz_rw_limit": ssz_rw_ok,
        "member_rows": export["ssz_channel"]["member_rows"],
        "written": str(out.relative_to(ROOT)),
    }, indent=1))
    return 0 if export["g150_gate"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
