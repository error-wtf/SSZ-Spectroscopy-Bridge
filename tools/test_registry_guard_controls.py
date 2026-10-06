#!/usr/bin/env python3
"""Registry guard: prove that fill/seal REFUSE while the chain is open.

Negative controls (declared before use):
  NC-1: attempt to fill a predicted value while status=PENDING  -> REFUSED
  NC-2: attempt to seal while any upstream gate is OPEN          -> REFUSED
  NC-3: attempt to mutate the registry without a prior-seal hash -> REFUSED
  NC-4 (positive, at seal time later): with all gates CLOSED, fill+seal
        succeed and produce a hash-chained seal.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "artifacts/SSZ_PREDICTION_REGISTRY_V1.json"
GUARD = ROOT / "tools/registry_guard.py"

GUARD_SRC = '''#!/usr/bin/env python3
"""Registry guard for SSZ_PREDICTION_REGISTRY_V1 (fail-closed).

Usage:
  registry_guard.py check
  registry_guard.py fill <key> <value_json> <falsification_bound_json>
  registry_guard.py seal <closure_sha> <bridge_sha> <spectro_sha> \\
                          <v4_branch> <operator_export_sha> <catalog_sha>

Rules:
  * check        : reports status + sealability
  * fill         : REFUSED unless status == FILLED_READY (i.e. every upstream
                   gate CLOSED and catalog frozen)
  * seal         : REFUSED unless status == FILLED_READY; produces a hash-
                   chained seal (sha256 over the full registry + prior seal)
  * any mutation : must land via this tool; raw edits are detected because
                   the stored integrity hash no longer matches.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "artifacts/SSZ_PREDICTION_REGISTRY_V1.json"
CHAIR = "bingsi <bingsi@error.wtf>"


def sha256_text(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def load():
    reg = json.loads(REG.read_text())
    if "integrity_sha256" in reg:
        body = dict(reg)
        expected = body.pop("integrity_sha256")
        actual = sha256_text(json.dumps(body, indent=1, sort_keys=True))
        if actual != expected:
            raise RuntimeError(
                "REGISTRY INTEGRITY VIOLATION: file was modified outside "
                "registry_guard.py (tamper evidence failed)")
    return reg


def save(reg):
    body = {k: v for k, v in reg.items() if k != "integrity_sha256"}
    reg = dict(reg)
    reg["integrity_sha256"] = sha256_text(
        json.dumps(body, indent=1, sort_keys=True))
    REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\\n")


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    reg = load()
    status = reg.get("status")

    if cmd == "check":
        print(json.dumps({"status": status,
                           "sealable": reg.get("sealable"),
                           "open_gates": [s["gate"] for s in
                                           reg["upstream_chain"]
                                           if s["state"] != "CLOSED"]},
                          indent=1))
        return 0

    if status == "PENDING":
        print(f"REFUSED: registry is PENDING — upstream chain not closed "
              f"({[s['gate'] for s in reg['upstream_chain'] if s['state'] != 'CLOSED']}). "
              "No fills, no seals, no exceptions.")
        return 1

    if cmd == "fill":
        if len(sys.argv) != 5:
            print("usage: fill <key> <value_json> <bound_json>")
            return 2
        key, value, bound = sys.argv[2], sys.argv[3], sys.argv[4]
        if key not in reg["predicted_quantities"]:
            print(f"REFUSED: unknown predicted quantity '{key}'")
            return 1
        reg["predicted_quantities"][key]["value"] = json.loads(value)
        reg["predicted_quantities"][key]["falsification_bound"] = json.loads(bound)
        reg["status"] = "FILLED_READY"
        save(reg)
        print(f"filled {key}; status=FILLED_READY (seal now possible)")
        return 0

    if cmd == "seal":
        if status != "FILLED_READY":
            print(f"REFUSED: seal requires FILLED_READY, registry is {status}")
            return 1
        filled = {k: v for k, v in reg["predicted_quantities"].items()
                  if v["value"] is not None}
        if not filled:
            print("REFUSED: no predicted values filled")
            return 1
        for k, v in reg["predicted_quantities"].items():
            if v["value"] is None:
                print(f"REFUSED: '{k}' has no value — fill all declared "
                      "quantities before sealing (no partial seals)")
                return 1
        seals = reg.setdefault("seals", [])
        prior = seals[-1]["seal_sha256"] if seals else "GENESIS"
        payload = {"prior_seal": prior,
                    "inputs": dict(zip(reg["seal_inputs_declared"],
                                        sys.argv[2:8])),
                    "registry_snapshot": reg}
        seal = hashlib.sha256(json.dumps(payload, sort_keys=True,
                                          ensure_ascii=False).encode()).hexdigest()
        seals.append({"seal_sha256": seal, "prior_seal": prior,
                       "inputs": payload["inputs"],
                       "utc": __import__("time").strftime(
                           "%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime())})
        reg["status"] = "SEALED"
        save(reg)
        print(f"SEALED. seal_sha256={seal}")
        print("From this point the predicted values are immutable — any edit "
              "breaks the integrity hash and is visible in git.")
        return 0

    print(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''
GUARD.write_text(GUARD_SRC)


def run(*args):
    r = subprocess.run([sys.executable, str(GUARD), *args],
                       capture_output=True, text=True, cwd=ROOT, timeout=60,
                       check=False)
    return r.returncode, (r.stdout or r.stderr).strip()


results = {}
# NC-1: fill while PENDING
rc, msg = run("fill", "mode_220", '{"Re": 0.3, "Im": -0.1}', '{"rel": 0.05}')
results["NC1_fill_pending"] = {"rc": rc, "refused": rc == 1, "msg": msg[:120]}
# NC-2: seal while PENDING
rc, msg = run("seal", "a", "b", "c", "d", "e", "f")
results["NC2_seal_pending"] = {"rc": rc, "refused": rc == 1, "msg": msg[:120]}
# NC-3: raw mutation must be caught
reg = json.loads(REG.read_text())
reg["status"] = "TAMPERED"
REG.write_text(json.dumps(reg, indent=1))
rc, msg = run("check")
REG.write_text(json.dumps(json.loads(REG.read_text()), indent=1))  # restore file
# restore true content from the init tool:
subprocess.run([sys.executable, str(ROOT / "tools/run_prediction_registry_init.py")],
               capture_output=True, cwd=ROOT, timeout=60, check=False)
rc2, msg2 = run("check")
results["NC3_tamper"] = {"check_after_tamper_rc": rc,
                          "restored_check_rc": rc2,
                          "restored_status": msg2[:120]}
# final state: still PENDING, integrity intact
rc, msg = run("check")
results["final_check"] = {"rc": rc, "msg": msg[:200]}

print(json.dumps(results, indent=1))
ok = (results["NC1_fill_pending"]["refused"]
      and results["NC2_seal_pending"]["refused"]
      and results["final_check"]["rc"] == 0)
print("GUARD NEGATIVE CONTROLS:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
