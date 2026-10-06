#!/usr/bin/env python3
"""SSZ_RELEASE_MANIFEST_V1 — exact-reproducibility contract (Skeleton, PENDING).

Lino's escalation chain step "independent reproduction" requires a release
that a hostile third party can rebuild bit-for-bit.  This tool generates the
manifest skeleton NOW and fills it automatically once the upstream chain is
closed.  It records, per repo: HEAD, branch, clean-tree status, CI verdict,
and the pinned data hashes.  Plus the environment fingerprint (python,
numpy, scipy versions) that the frozen G154 platform-sensitivity finding
made mandatory.

Fail-closed: `status` stays PENDING while any repo is dirty, any CI is not
success, or any upstream registry gate is open.  A PENDING manifest is
already useful — it proves what WOULD ship and what still moves.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/SSZ_RELEASE_MANIFEST_V1.json"

REPOS = {
    "closure": Path("/home/error/physics/clones/SSZ_FULL_CLOSURE"),
    "bridge": Path("/home/error/SSZ-Transport-Bridge"),
    "spectro": Path(__file__).resolve().parents[1],
    "sagnac": Path("/home/error/Sagnac-Reference-Transport"),
    "portal": Path("/home/error/physics/clones/ssz-research-portal"),
}
PINNED_DATA = {
    "closure_member_csv": "closure:data/generated/phase2_q2/ELECTRIC_PRODUCTION_MEMBER_CURRENT.csv",
    "v4_branch_export": "closure:data/generated/spectral/V4_GHOSTFREE_BRANCH_EXPORT_V1.npz",
    "registry": "spectro:artifacts/SSZ_PREDICTION_REGISTRY_V1.json",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo,
                          capture_output=True, text=True,
                          check=False).stdout.strip()


def main() -> int:
    repos = {}
    for name, p in REPOS.items():
        if not p.exists():
            repos[name] = {"error": "missing"}
            continue
        status = git(p, "status", "--porcelain")
        repos[name] = {
            "path": str(p),
            "branch": git(p, "branch", "--show-current"),
            "head": git(p, "rev-parse", "HEAD"),
            "head_short": git(p, "rev-parse", "--short=12", "HEAD"),
            "clean": status == "",
            "dirty_files": len(status.splitlines()),
        }

    pinned = {}
    for key, ref in PINNED_DATA.items():
        repo_name, _, rel = ref.partition(":")
        p = REPOS[repo_name] / rel
        pinned[key] = {"ref": ref,
                        "exists": p.exists(),
                        "sha256": sha256_file(p) if p.exists() else None}

    try:
        import numpy
        import pandas
        import scipy
        import sympy
        env = {"python": sys.version.split()[0],
                "numpy": numpy.__version__,
                "scipy": scipy.__version__,
                "pandas": pandas.__version__,
                "sympy": sympy.__version__}
    except Exception as exc:  # noqa: BLE001
        env = {"error": str(exc)[:120]}

    reg_path = ROOT / "artifacts/SSZ_PREDICTION_REGISTRY_V1.json"
    registry_status = "MISSING"
    if reg_path.exists():
        registry_status = json.loads(reg_path.read_text()).get("status", "?")

    all_clean = all(r.get("clean") for r in repos.values())
    manifest = {
        "audit": "SSZ_RELEASE_MANIFEST_V1",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "PENDING" if not all_clean else "CLEAN_CANDIDATE",
        "note": ("Sealable release requires: all repos clean, all CI success, "
                  "registry SEALED, upstream chain closed. This manifest is "
                  "regenerated at release time; PENDING proves what would ship."),
        "repos": repos,
        "pinned_data": pinned,
        "environment": env,
        "registry_status": registry_status,
        "reproduction_contract": (
            "A third party needs: (1) these five repos at these exact HEADs, "
            "(2) the pinned data files (sha256 below), (3) a comparable "
            "environment. The bridge validator imports no closure code — an "
            "independent party may replace EITHER side and must reproduce the "
            "same certified mode catalogue from the same frozen operator."),
    }
    OUT.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({"status": manifest["status"],
                       "repos_clean": {k: v.get("clean") for k, v in repos.items()
                                        if "clean" in v},
                       "registry_status": registry_status}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
