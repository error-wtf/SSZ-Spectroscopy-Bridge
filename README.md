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
| G155 | **PASS** | Certified RW control catalogue (MODE-C1..C8): 5/5 modes n=0..4 certified (Leaver CF, eps_residual <= 2.8e-12, eps_grid <= 2.9e-11), C6 analytic PT control 3.8e-9, C7 fake-mode rejection measured (`artifacts/RW_CONTROL_CERTIFIED_MODE_CATALOGUE_G155_V1.json`, `tools/run_g155_catalogue.py`) |
| G160 | **PASS (full)** | waveform reconstructed FROM THE CERTIFIED MODE SET: rel-L2 0.67% in the clean window [82,102], certified-frequency fit beats the free-frequency pencil fit (0.669% vs 0.680%), leading mode vs pencil 4.0e-5 (`artifacts/G160_CERTIFIED_WAVEFORM_CLOSURE_V1.json`) |
| G170 | **PASS** | blind mass recovery: hidden M (hash-committed) recovered to 0.5-2.8% in 3 noise realisations, detection threshold derived from the noise-only distribution BEFORE the trials (`artifacts/G170_G171_BLIND_AND_CONTROLS_V1.json`) |
| G171 | **PASS** | wrong-model control: wrong-M chi2 strictly worse; noise-only stays below the derived threshold |
| G180 | **PASS** | detector-response closure end-to-end on synthetic data: certified modes -> h(t) -> declared antenna pattern -> noise @ energy-SNR 50 -> d(t); pencil recovers the injected mode to 3.5e-4 (documented end-to-end tolerance; mode-sum truncation + noise) (`artifacts/G180_DETECTOR_RESPONSE_CLOSURE_V1.json`) |
| G181 | **PASS** | GWOSC real data provenance: H1+L1 32s/4kHz GW150914 strain, SHA-256 sidecar locked, catalog GPS window, declared conditioning (Tukey/Welch/whiten/35-350Hz) (`artifacts/G181_G182_G183_GWOSC_REAL_DATA_V1.json`, `data/gwosc/`) |
| G182 | NOT PASS | single-damped-sinusoid matched filter on real GW150914 H1/L1: H1 SNR 6.1 < 8, detection criterion failed with the simplified template — honest infrastructure limit |
| G183 | NOT PASS | mass stability across detectors failed (H1 110 vs L1 62 Msun — merger-power leakage into the simplified ringdown template); needs an IMR-based filter |
| G161 | BLOCKED | requires the closure eikonal layer (Xi->D->g->Phi transport); the bridge SSZ channel is SYMBOLIC_TEST_ONLY (isospectral, FailClosed) until N3/N4 |
| G184 | **PASS** | NICER real-data timing chain: 20/20 ObsIDs MAXI J1820+070 (HEASARC, SHA-256 provenance), GTI-segment Leahy PSDs, no significant QPO peaks at 6 sigma (honest null), injection control recovers a 4 Hz sinusoid at Leahy 14.7 — chain verified live (`artifacts/G184_NICER_REAL_DATA_TIMING_CHAIN_V2.json`) |
| G190 | **BLOCKED** | rule applied honestly: G182/G183 not passed, G161 structurally blocked -> verdict BLOCKED (recorded in `artifacts/G190_EMPIRICAL_SPECTROSCOPY_VERDICT_V1.json`) |

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
