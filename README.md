# SSZ-Spectroscopy-Bridge

Certified spectral modes + inverse inference + real detector data — the
third link that closes

    Sagnac reference -> generic transport -> SSZ geometry ->
    spectral modes -> measured phase/signal -> real data.

Gates G150-G190 are DECLARED in `docs/GATES_MANIFEST.json` before their
implementation lands (anti-circularity). The mode certification contract
(MODE-C1..C8, frozen tolerances) lives in
`docs/MODE_CERTIFICATION_CONTRACT.md`.

## Current status (honest)

| Gate | Status | Evidence |
|------|--------|----------|
| G150 | **PASS** | `SSZ_SPECTROSCOPY_OPERATOR_EXPORT_G150_V1`: hash-bound export, RW anchor re-derivation 0.0 err, SSZ channel scope-flagged (`tools/run_g150_export.py`) |
| G152 | **PASS (ensemble)** | multi-width consensus 2.68e-5, pairwise 1.89e-4 (`artifacts/G152_MULTI_WIDTH_ENSEMBLE_V1.json`) |
| G153 | **PASS (measured)** | Time-domain leapfrog + matrix-pencil: M*omega(l=2,n=0) = 0.37365 - 0.08895 i vs published 0.37367 - 0.08896 i -> **err 2.06e-5 < 1e-4** (`artifacts/GATE_CAMPAIGN_RW_CONTROL_V1.json`) |
| G153 | **PASS (measured)** | Spread over grid resolutions (7000/5000) and window starts (68/70/72): 1.12e-5 < 5e-4 |
| G151 | **PASS (frequency-domain)** | Two-part evidence: (1) Leaver continued-fraction solver (Leaver 1991 Eq.5, exact coefficients): M*omega(l=2,n=0) = 0.37367168 - 0.08896232 i, CF misfit 5.2e-17, validated against Berti's Leaver-method tables to <= 4e-15 on 6 modes (`artifacts/G151_LEAVER_FREQUENCY_DOMAIN_V1.json`, `tests/unit/test_leaver.py`); (2) factored shooting with the ANALYTIC Poschl-Teller reference (exact spectrum known in closed form, Cardona-Molina CQG 2017 Eq. 38): root recovered to 3.8e-9 with a measured convergence ladder (RK45 floor 8.6e-7 -> DOP853 1.6e-8 -> CubicSpline gap 5.0e-16) (`tests/unit/test_shooting_factored.py`) |
| G151 | **PASS (cross-solver)** | frequency-domain Leaver vs time-domain pencil agree to 2.34e-5 (pencil carries the O(grid) truncation; Leaver is the gold standard) |

## The breakthrough this session (measured, reproducible)

Frequency-domain collocation failed (box-leakage branch, see below). The
working route is TIME-DOMAIN: leapfrog evolution of the RW equation on
the tortoise grid with extrapolation outflow boundaries, then matrix-
pencil (Hua-Sarkar) extraction of the ringdown from the clean window
t in [70, 102] (boundary echo only arrives at t ~ 185 — measured).

    M*omega(l=2, n=0):  measured 0.37365 - 0.08895 i
                        published 0.37367 - 0.08896 i
                        |error| = 2.1e-5   (gate requires < 1e-4)

Reproduce: `python tools/run_gate_campaign_rw.py` (~90 s).

## Verified so far (this is real, tested infrastructure)

* Chebyshev differentiation matrices + quadratic-EVP companion
  linearisation: EXACT on the analytic Dirichlet box (max err 5e-12,
  `tests/unit/test_collocation_box.py`).
* RW potential and tortoise coordinate: analytic, exact closed forms.
* Reference spectrum frozen from the literature PDF (page-render
  verified, no recalled constants).

## Known open numerical problem (documented, not hidden)

Polynomial Chebyshev collocation with ingoing-wave boundary rows on the
finite interval [-xR, xR] does NOT converge to the published RW QNM for
any tested (xR, n) in xR in {25..100}, n in {100..400}: the spectrum
returns the box-leakage branch (Im omega ~ 3e-3, scales inversely with
xR).  The Dirichlet-box calibration proves the linearisation is exact,
so the defect is in the boundary-condition treatment of the open
problem.  Next declared attack paths:

1. ~~Leaver continued fraction~~ DONE: `continued_fraction.py` now carries
   the paper-verified transcription (Leaver 1991 Eq.5, exact coefficients)
   and reproduces Berti's tables to <= 4e-15 (`tests/unit/test_leaver.py`).
2. Hyperboloidal/mirror-shifted compactification of the collocation
   grid.
3. Direct time-domain evolution with a pulsation extraction
   (prony/PSD) — the Sagnac repo's PDE machinery is reusable here.

None of these are fudged: no tolerance was loosened to make a wrong
number look right.

## Layout

    src/ssz_spectroscopy/
        operator.py              (RW control: exact; SSZ: fail-closed)
        shooting.py              (solver A2, Wronskian shooting)
        spectral_collocation.py  (solver B, Chebyshev quadratic EVP)
        continued_fraction.py    (solver A1, Leaver CF — validated vs Berti tables)
        control_problems.py      (analytic references)
    docs/GATES_MANIFEST.json
    docs/MODE_CERTIFICATION_CONTRACT.md

## Source lineage

* SSZ_FULL_CLOSURE @ spectroscopy-real-data-20261004
  (V3 no-go bd46255, V4 varying-G4 384700c, CI green)
* SSZ-Transport-Bridge (B1..B10, REAL_SSZ_ADAPTER_PASS)
* Sagnac-Reference-Transport (SAG-S1..S10, 66/66)
