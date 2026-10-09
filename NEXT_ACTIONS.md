# NEXT_ACTIONS

Order-binding queue for the autonomous overnight run (master order
2026-10-08, Super Mode). Each step is covered by the frozen protocols.

## 1. F7 r2 gate verdict (BLOCKING, in progress)
- run_gwosc_v2_injection_gate.py still executing (H1 injection table)
- on completion: read artifacts/GWOSC_V2_INJECTION_GATE_V1.json
- verify gate constants against GWOSC_V2_INJECTION_GATE_PREREGISTRATION.json
  (commit 5c0525b) — any mismatch = STOP (I1 violation)

## 2a. If F7 PASS
- run real-data extraction: GPS 1126259462.4, window +0.002..+0.06 s,
  H1 and L1 independent, post-onset pencil window, F2 amplitudes,
  F3 ladder enforced, F4 200 bootstrap, F5 off-source PSD, F6 phase gate
- write GWOSC_GW150914_OBSERVED_MODES_V2.json/.csv with per-candidate
  accept/reject reasons and uncertainties
- allowed verdicts: OBSERVED_COHERENT_MODE |
  NO_SURVIVOR_UNDER_VALIDATED_TEST | SENSITIVITY_INSUFFICIENT |
  PIPELINE_VALIDATION_FAIL | INCONCLUSIVE

## 2b. If F7 FAIL
- synthetic-only diagnosis (no real data)
- fix extractor, append r3 entry to frozen spec, rerun gate
- no threshold changes after seeing results

## 3. Comparison (only after 2)
- SSZ_GWOSC_BLIND_COMPARISON_V2.json against the frozen SSZ state
  (L-ladder nulls; certificate untouched)
- allowed outcomes: MATCH | NO_MATCH | THEORY_PREDICTS_NO_DISCRETE_MODE |
  OBSERVATION_HAS_NO_STABLE_MODE | OUTSIDE_THEORY_SCAN_DOMAIN |
  SCALE_MAPPING_UNRESOLVED — honestly assigned

## 4. Morning handoff (mandatory before session end)
- MORNING_HANDOFF_2026-10-09.md (repos, branches, commits, SHA256, CI)
- MORNING_RESEARCH_VERDICT_2026-10-09.json (F1-F6 PASS/FAIL, F7 numbers,
  real-data verdict or NOT_RUN, NICER status, MCP provenance, open
  problems by scientific priority, exactly one next step)

## 5. Secondary (only if gate wait time is idle)
- NICER LF-V2 preregistration draft: dt <= 1/128 s (Nyquist fix for any
  64 Hz claim), LF band 0.05-1 Hz, declared sensitivity loss
- eps=+0.3 branch health gate (pre-registered theory task): rank(K)=3,
  K positive, pivots healthy, exterior valid, BC construction valid —
  theory-only, no scan

## HARD RULES (restated)
- No SSZ parameter changes. No theory frequencies as search aids.
- No threshold adjustments after seeing results.
- Real data blocked until gate PASS. FAIL is never replaced by PASS.
- No force-push, no deletion of raw data, no secrets in logs/commits.
