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
| G150 | IN_PROGRESS | RW control channel exported analytically (`src/ssz_spectroscopy/operator.py`); SSZ channel fail-closed pending symbolic axial derivation |
| G151 | OPEN | physical BC layer: ingoing-wave collocation calibrated on the analytic Dirichlet box (exact to 5e-12) but NOT yet converged on the RW open problem (see below) |
| G152 | OPEN | second solver (Leaver continued fraction) scaffolded, blocked on paper-verified transcription |
| G154 | OPEN | reference value M*omega(l=2,n=0) = 0.37367 - 0.08896 i frozen from the Konoplya-Rezzolla-Zhidenko review Table 1 (PDF page 13, verified) |

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
