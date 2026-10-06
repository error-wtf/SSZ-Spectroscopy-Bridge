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

## What is honestly open

The ghost-free V4 branch has a negative kinetic channel (measured,
fail-closed recorded). Sector attribution is blocked behind physical
boundary conditions. **There is no SSZ QNM catalogue yet.** The
prediction registry (`SSZ_PREDICTION_REGISTRY_V1.json`) is PENDING and
its guard refuses to accept values until the upstream chain is closed —
including by you.

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
