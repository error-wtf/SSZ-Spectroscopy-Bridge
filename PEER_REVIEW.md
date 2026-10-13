# PEER_REVIEW.md — reviewer's map for SSZ-Spectroscopy-Bridge

Last updated: 2026-10-11. Everything below points at files you can open
and numbers you can re-derive. Nothing here is claimed beyond what the
recorded artifacts and the test suite actually show.

## Entry points (where to start reading)

| question | go to |
|---|---|
| What is this repo and what does it claim? | `README.md` (status banner + honest gate table) |
| Which gates exist, who owns them, what blocks what? | `docs/GATES_MANIFEST.json` (declared BEFORE implementation — anti-circularity) |
| What must a "certified mode" satisfy? | `docs/MODE_CERTIFICATION_CONTRACT.md` (MODE-C1..C8, frozen tolerances) |
| The one headline number, re-derived live? | `tools/run_gate_campaign_rw.py` (~90 s) |
| The gold-standard frequency-domain solver? | `src/ssz_spectroscopy/continued_fraction.py` + `tests/unit/test_leaver.py` |
| Independent second opinion on every gate? | `tools/run_full_pipeline.py` -> `FULL_PIPELINE_REPORT.md` |
| How do I rebuild everything from scratch? | `REPRODUCE.md` |
| Animated summary of the core results? | `demos/output/*.gif` (regen: `demos/animate_core_results.py`) |

## Core claims and the files that carry them

**C1. The fundamental RW mode is measured, not recalled.**
Time-domain leapfrog + matrix pencil on the clean window gives
M*omega(l=2,n=0) = 0.37365 - 0.08895 i vs published
0.37367 - 0.08896 i, |err| 2.1e-5 (gate tolerance 1e-4).
Carried by: `artifacts/GATE_CAMPAIGN_RW_CONTROL_V1.json`
(`measurements[0]`, fields `M_omega`, `err_vs_reference`),
re-derived by `tools/run_gate_campaign_rw.py`, cross-checked
frequency-domain in G151 (Leaver: 0.37367168 - 0.08896232 i,
CF misfit 5.2e-17).

**C2. The Leaver CF solver reproduces the published tables.**
Validated against Berti's Leaver-method tables to <= 4e-15 on 6
modes. Carried by: `tests/unit/test_leaver.py`,
`artifacts/G151_LEAVER_FREQUENCY_DOMAIN_V1.json`. Units: the CF works
in 2M=1, so omega = 0.7473433688 - 0.1779246314 i there; multiply by
M to compare with the catalogue.

**C3. The mode catalogue is certified under a frozen contract.**
5/5 modes n=0..4 certified (eps_residual <= 2.8e-12, eps_grid
<= 2.9e-11), analytic Poschl-Teller control to 3.8e-9, fake-mode
rejection measured. Carried by:
`artifacts/RW_CONTROL_CERTIFIED_MODE_CATALOGUE_G155_V1.json`
(`rows`, `controls`, `n_certified=5`, `all_controls_pass=true`).

**C4. The waveform closes back onto the certified mode set.**
Reconstructed FROM the certified set: rel-L2 0.67% in the clean
window, certified-frequency fit beats the free-frequency pencil fit
(0.669% vs 0.680%). Carried by:
`artifacts/G160_CERTIFIED_WAVEFORM_CLOSURE_V1.json`.

**C5. Inverse inference works blind on synthetic data.**
Hidden hash-committed mass recovered to 0.5-2.8% in 3 noise
realisations, threshold derived from the noise-only distribution
BEFORE the trials. Carried by:
`artifacts/G170_G171_BLIND_AND_CONTROLS_V1.json`.

**C6. Real detector data enters with locked provenance.**
GW150914 H1+L1 strain with SHA-256 sidecar; NICER MAXI J1820+070
20/20 ObsIDs with SHA-256 provenance. Carried by:
`artifacts/G181_G182_G183_GWOSC_REAL_DATA_V1.json`,
`artifacts/G184_NICER_REAL_DATA_TIMING_CHAIN_V2.json`,
`data/gwosc/`.

## Negative controls (the part that makes the PASSes mean something)

- **Fake-mode rejection (C7).** A deliberately wrong ("fake") mode is
  offered to the certification machinery; the contract rejects it.
  Recorded as a measured control in
  `RW_CONTROL_CERTIFIED_MODE_CATALOGUE_G155_V1.json`
  (`controls` -> `negative_control_fake_mode ...`).
- **Wrong-model control (G171).** A ringdown with the wrong M gives
  strictly worse chi2; noise-only stays below the derived detection
  threshold (`G170_G171_BLIND_AND_CONTROLS_V1.json`).
- **Analytic PT reference.** Factored shooting recovers the exact
  Poschl-Teller spectrum (closed form known) to 3.8e-9 — the solver
  stack is calibrated on a problem where the answer is independently
  known (`tests/unit/test_shooting_factored.py`).
- **Anti-circularity of the gates themselves.** Gates are declared in
  `docs/GATES_MANIFEST.json` before implementation; the verdict tool
  applies the recorded rules mechanically
  (`tools/run_g190_verdict.py`).

## Known limitations (stated plainly)

- **G182/G183 NOT PASS — single-sinusoid limit.** The real-event
  filter is a single damped sinusoid; on public GW150914 strain it
  yields H1 SNR 6.1 < 8 and inconsistent masses (H1 110 vs L1
  62 Msun, merger-power leakage). This is an honest infrastructure
  limit of the simplified template, NOT evidence against the mode
  catalogue. An IMR-based filter is the declared next step.
- **G161 BLOCKED — missing layer, not an error.** Frequency/phase
  equivalence needs the closure eikonal transport (Xi->D->g->Phi)
  owned by the N3/N4 repos; the SSZ channel here is
  SYMBOLIC_TEST_ONLY (isospectral, fail-closed) until then.
- **G190 BLOCKED — by design.** The empirical verdict is mechanically
  BLOCKED while G182/G183 are not passed and G161 is blocked. Keeping
  this visible is a feature of the methodology.
- **Open numerical problem (documented).** Chebyshev collocation with
  ingoing-wave BCs on a finite box returns the box-leakage branch
  (README, "Known open numerical problem"). The Leaver CF route is
  the working alternative; the collocation defect is documented, not
  hidden.

## What is NOT claimed

- No claim that real-event spectroscopy (G182/G183) succeeded — it
  did not, and the artifacts say so.
- No claim that the SSZ channel is physically derived here — it is
  symbolic/fail-closed pending N3/N4.
- No claim that the measured time-domain mode beats the published
  value — it agrees to 2.1e-5, within its declared O(grid)
  truncation; Leaver is the gold standard, the pencil carries the
  truncation.
- No fudged tolerances: no gate tolerance was loosened retroactively
  to convert a NOT PASS into a PASS.
- No claim of empirical/observational confirmation of SSZ-specific
  structure — the certified modes are RW control modes; the bridge to
  SSZ geometry is declared, hash-bound (G150), and waits on N3/N4.

## Independent verification a reviewer can run

1. `/home/error/physics/venv/bin/python -m pytest tests/ -q`
   (21 tests, ~85 s) — no network needed.
2. `/home/error/physics/venv/bin/python tools/run_full_pipeline.py`
   (~90 s) — regenerates `FULL_PIPELINE_REPORT.md`.
3. `/home/error/physics/venv/bin/python tools/run_gate_campaign_rw.py`
   (~90 s) — re-derives the headline measurement.
4. Inspect `artifacts/*.json` against `docs/GATES_MANIFEST.json` and
   the README table — statuses must match exactly (G182/G183
   NOT PASS, G161/G190 BLOCKED).
