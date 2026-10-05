# MODE CERTIFICATION CONTRACT V1 (MODE-C1..C8)

Status: contract frozen 2026-10-06, before the first certified mode exists.

A numerically found eigenvalue is NOT an "SSZ mode" until it carries a
complete certificate. Every catalogue row is the tuple

    (l, m, n, omega, eps_residual, eps_convergence, eps_solver, branch)

with the following gates. `PASS`/`FAIL` per gate; any FAIL disqualifies
the row from `certified: true` — the row stays in the catalogue with its
failing gate named (no silent dropping).

| Gate | Meaning | Measurement (frozen rule) |
|------|---------|---------------------------|
| C1 | boundary conditions satisfied | ingoing-wave BC residual at both ends below `tol_bc` on the certified grid |
| C2 | operator residual small | |L(omega) psi| / |psi|_scale < `tol_residual` at the eigenfunction |
| C3 | grid convergence | eigenvalue shift under grid refinement below `tol_grid`, measured order recorded |
| C4 | second solver agrees | |omega_shooting - omega_collocation| < `tol_solver` |
| C5 | branch continuation stable | mode tracked over the continuation parameter without branch-crossing (fingerprint = Re omega + sign Im omega at fixed n-ordering) |
| C6 | Schwarzschild/control limit recovered | at control-parameter value the mode matches the analytic reference spectrum within `tol_control` |
| C7 | deliberate fake mode rejected | the certification pipeline, fed a seeded fake eigenvalue, MUST reject it (measured, not asserted) |
| C8 | provenance/member hash locked | the operator export, member profile and law parameters carry SHA-256 recorded in the certificate |

## Frozen tolerances (campaign-derived, never tuned post hoc)

    tol_bc        = 1e-8   (relative to wavefunction scale at the boundaries)
    tol_residual  = 1e-6   (relative operator residual)
    tol_grid      = 1e-6   (relative eigenvalue shift, finest vs next)
    tol_solver    = 1e-4   (absolute, complex omega, cross-solver)
    tol_control   = 1e-4   (absolute, complex omega, vs reference spectrum)

Tolerances may be tightened by later campaigns; loosening requires a new
contract version and a written justification.
