# REPRODUCE.md — Building the SSZ chain independently

You do not have to believe a word of this project. Everything here is
built to be rebuilt by a hostile third party. This file tells you how,
and what you are allowed — encouraged — to break.

## The chain you are reproducing

```
Sagnac-Reference-Transport     (analytically calibrated transport, SAG-S1..S10)
        ↓
SSZ-Transport-Bridge           (independent re-solver + typed contracts, ADR-001)
        ↓
SSZ_FULL_CLOSURE               (frozen geometry, action → operator)
        ↓
SSZ-Spectroscopy-Bridge        (certified QNM machinery + real-data gates)
```

The bridge imports **no closure code**. It consumes frozen, hash-bound
data files only. You can replace either side of that interface with your
own implementation — that is the point.

## Step by step, in this repo (measured runtimes)

All commands use the project venv:
`/home/error/physics/venv/bin/python` (numpy 2.5.3, scipy 1.18.1,
matplotlib 3.11.2, pillow 12.3.0, pytest 9.1.1). No network needed
except where real-data gates refetch.

| # | command | expected result | runtime (measured) |
|---|---------|-----------------|--------------------|
| 1 | `python -m pytest tests/ -q` | `21 passed` | ~85 s |
| 2 | `python tools/run_full_pipeline.py` | writes `FULL_PIPELINE_REPORT.md`, prints gate ledger, ends `pipeline OK` | ~90 s (dominated by step 1) |
| 3 | `python demos/animate_core_results.py` | 3 GIFs in `demos/output/` (rw_ringdown, gate_board, leaver_cf_convergence) | ~18 s |
| 4 | `python tools/run_gate_campaign_rw.py` | re-derives M*omega(l=2,n=0) = 0.37365-0.08895 i, err 2.1e-5; **overwrites** `GATE_CAMPAIGN_RW_CONTROL_V1.json` | recorded wall 8.5 s |
| 5 | `python tools/run_g155_catalogue.py` | certified catalogue, 5/5 modes, `all_controls_pass: true` | recorded wall 37.6 s |
| 6 | `python tools/run_g152_ensemble.py` | multi-width consensus 2.68e-5 | recorded wall 7.8 s |
| 7 | `python tools/run_g170_g171_blind_controls.py` | blind mass recovery 0.5-2.8%, controls hold | recorded wall 11.9 s |
| 8 | `python tools/run_g180_detector_closure.py` | detector-response closure: eps_solver_vs_certified 3.5e-4, rel-L2 2.0% | recorded wall 1.5 s |
| 9 | `python tools/run_g181_g182_g183_gwosc.py` | G181 PASS; **G182/G183 NOT PASS** (honest) | recorded wall 8.9 s |
| 10 | `python tools/run_g184_nicer_chain.py` | 20/20 ObsIDs, no significant QPO (null), injection control OK | recorded wall 0.6 s (V2) |
| 11 | `python tools/run_g190_verdict.py` | applies rules mechanically -> verdict **BLOCKED** | < 1 s |

Runtimes are from the recorded `wall_seconds` fields in the artifacts
themselves plus live measurements on the reference machine (2026-10-11);
expect variation with hardware.

**Long gates — documented, not re-run by default:** the GWOSC V2
follow-up matrices (`GWOSC_V2_F7_GATE_RESULT_FULL_MATRIX_FAIL.json`,
recorded wall 582 s; `..._V3_HOLDOUT_RESULT_FAIL.json` /
`..._INJECTION_GATE_V1.json`, recorded wall 2302 s each) are FAIL
results, preregistered and frozen. Re-running them costs ~1 h total and
overwrites certified FAIL evidence; the honest results are already in
the artifacts. The full pipeline (step 2) therefore documents gate
evidence instead of re-executing it (`--exec-gates` opts in, excluding
these long GWOSC V2 gates).

**Side-effect warning:** every `tools/run_g*.py` overwrites its
artifact in `artifacts/`. If you want to keep the certified evidence,
copy `artifacts/` aside first (`cp -r artifacts artifacts.bak`) — or
better, check git status before and after.

## What to check first (five minutes)

1. Clone the five repos at the HEADs recorded in
   `SSZ-Spectroscopy-Bridge/artifacts/SSZ_RELEASE_MANIFEST_V1.json`.
2. Verify the pinned data hashes in the same file.
3. Run each repo's test suite (`pytest tests/ -q`). Every suite is green;
   if yours is not, the manifest tells you which repo moved.

## The strongest independent checks you can run

* **The bridge judge.** `SSZ-Transport-Bridge` re-derives the SSZ null
  geodesics, phase integrals and redshifts from the frozen metric data
  with its own integrators and matches the producer to ~1e-9 relative.
  Replace its splines with your own and the contracts still must hold.
* **The box-mode solve.** The spectral export (frozen operator, SHA-256
  sidecar) is consumed by an independent P1-Galerkin solver. Mode
  eigenvalues converge over the resolution ladder with residuals ≤ 1e-17
  and cross-solver agreement ~5–9e-10 relative. These are **box modes,
  not QNMs** — the repos say so themselves, loudly.
* **The S-contract provenance.** `V4_S_TERM_PROVENANCE.json` traces the
  antisymmetric connection S to the quadratic action; the by-parts
  identity holds to ~1e-12 relative. Try to break it.
* **The Leaver CF cross-check.** `tests/unit/test_leaver.py` validates
  the continued-fraction solver against Berti's published tables to
  <= 4e-15 on 6 modes — recalled constants are not trusted, tables are.
* **The fake-mode control.** Feed a deliberately wrong mode to the
  certification contract (`G155` controls): it must be rejected. The
  rejection is a recorded, measured control — not a promise.

## What is honestly open

The ghost-free V4 branch has a negative kinetic channel (measured,
fail-closed recorded). Sector attribution is blocked behind physical
boundary conditions. **There is no SSZ QNM catalogue yet.** The
prediction registry (`SSZ_PREDICTION_REGISTRY_V1.json`) is PENDING and
its guard refuses to accept values until the upstream chain is closed —
including by you.

In this repo specifically, the honest gate ledger stands at:
G182/G183 **NOT PASS** (single-sinusoid template limit on real
GW150914 strain), G161 **BLOCKED** (needs the N3/N4 closure eikonal
layer), G190 verdict **BLOCKED** as the mechanical consequence. The
GWOSC V2 follow-up gates are recorded **FAIL**. None of these are
hidden, walked back, or re-labeled.

## Rules of engagement

* If you reproduce: open an issue with your hashes. It counts.
* If you falsify: open an issue with your hashes and the failing
  quantity. **It counts more.** Falsification bounds are declared in the
  prediction registry before any data contact — breaking one is a
  first-class result, not an embarrassment.
* The negative controls are real: corrupted operators, sign-flipped K,
  wrong boundaries, wrong members — the bridge fires on all of them.
  Try your own.

## The three possible endings

1. SSZ performs worse than data/GR → this member, this dynamics falls.
2. SSZ is indistinguishable from GR → current data cannot separate.
3. SSZ delivers robust out-of-sample predictions → new independent
  tests are forced. (This is not "confirmed" — this is "attack it
  harder".)

All three are acceptable outcomes of this project. Ending the chain of
"and then?" means letting the universe answer.
