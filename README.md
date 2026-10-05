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
| G154 | **PASS (measured)** | Time-domain leapfrog + matrix-pencil: M*omega(l=2,n=0) = 0.37365 - 0.08895 i vs published 0.37367 - 0.08896 i -> **err 2.06e-5 < 1e-4** (`artifacts/GATE_CAMPAIGN_RW_CONTROL_V1.json`) |
| G153 | **PASS (measured)** | Spread over grid resolutions (7000/5000) and window starts (68/70/72): 1.12e-5 < 5e-4 |
| G152 | PARTIAL | pencil vs heterodyne: 1.55e-2 > declared 5e-3 — the heterodyne estimator is biased by the short window; the frequency-domain second solver remains OPEN (documented box-leakage problem). Gate NOT claimed. |
| G151 | PARTIAL | outflow boundaries verified clean (boundary echo measured at t~185, extraction window ends at 102); frequency-domain ingoing-wave BC layer OPEN |
| G150 | IN_PROGRESS | RW control channel exported analytically; SSZ channel fail-closed pending symbolic axial derivation |

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

1. Leaver continued fraction (gold standard, no BC approximation),
   blocked on a paper-verified transcription of the three-term
   recurrence (Leaver 1985).
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
        continued_fraction.py    (solver A1, Leaver — scaffold)
        control_problems.py      (analytic references)
    docs/GATES_MANIFEST.json
    docs/MODE_CERTIFICATION_CONTRACT.md

## Source lineage

* SSZ_FULL_CLOSURE @ spectroscopy-real-data-20261004
  (V3 no-go bd46255, V4 varying-G4 384700c, CI green)
* SSZ-Transport-Bridge (B1..B10, REAL_SSZ_ADAPTER_PASS)
* Sagnac-Reference-Transport (SAG-S1..S10, 66/66)
