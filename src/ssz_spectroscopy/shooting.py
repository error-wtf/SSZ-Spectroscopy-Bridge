"""Shooting solver for the Schrodinger-form QNM problem (G152 solver A2).

Integration of
    psi'' + [omega^2 - V(x)] psi = 0
on the tortoise grid with pure-ingoing/outgoing asymptotics
    psi ~ exp(-i omega x)  as x -> -inf (horizon side),
    psi ~ exp(+i omega x)  as x -> +inf.

CONTAMINATION FIX (measured 2026-10-06): integrating psi directly and
matching at a mid/edge point is numerically DEAD for |Im omega| * X >= 1
— the parasitic (inward-growing) solution overtakes the integrated one
by e^(2 |Im w| X): on [-40, 40] with Im w = -0.55 the right-side match
value was 3.1e14 and NO omega produced a sharp Wronskian minimum.
The fix is the standard asymptotic factorisation

    psi = exp(-i w x) u   (left),  psi = exp(+i w x) v   (right)

so the integrated functions u, v are O(1) and the matching condition is
the equality of the TOTAL log-derivatives

    u'/u - i w   =   v'/v + i w      at x_match,

compared with an ABSOLUTE metric |rp - lp|.  (A RELATIVE metric
|rp-lp|/(|lp|+|rp|) is degenerate exactly at roots, where both -> 0:
it returns 1.0 at the true root.  Measured on the Poschl-Teller
control: relative metric saturates at 1.000 on the whole line while
the absolute metric dips to 8.6e-7 at the exact root.)

Integration: DOP853 rtol=1e-12 (measured integrator-floor study:
RK45 rtol=1e-10 leaves a mismatch floor of 8.6e-7 AT the exact root
and NM stalls at 4.9e-9; DOP853 rtol=1e-12 drops the floor to 1.6e-8
and NM reaches gap 5.6e-16 with |root - exact| = 3.9e-9 in ~4 s).

POTENTIAL REPRESENTATION (measured 2026-10-06): np.interp as Vf inside
the RHS is BOTH the accuracy AND the speed bottleneck: with linear
interpolation the gap at the EXACT PT root saturates at 1.1e-5
(domain-independent — it is the kink error of piecewise-linear V, not
domain truncation), and each mismatch costs ~2 s (DOP853 makes dense
off-grid evaluations).  Switching Vf to a CubicSpline of the same grid
drops the gap at the exact root to 1.6e-8 and the full NM solve to
gap 5.0e-16, |root - exact| = 3.8e-9, in 6.4 s total (measured).
shoot_qnm therefore builds a CubicSpline from the input grid.

VALIDATED control (Cardona-Molina CQG 34, 245002 (2017) Eq. 38):
V = V0 sech^2(k x), V0=2, k=1 -> omega_n = sqrt(7)/2 - i(n+1/2);
the solver returns 1.3228757 - 0.50000021 i (misfit 2.4e-15) from a
crude seed.

NOTE ON SCOPE: for the RW potential the asymptotics are power-law
(V ~ 1/x^2), not exponential, so finite-domain shooting for RW inherits
a systematic that the Leaver continued-fraction solver
(`continued_fraction.py`, G151 gold standard) does not have.  This
solver is therefore the CONTROL-problem solver (exponential tails);
RW QNMs go through the CF route.
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize


def _factored_log_derivs(omega: complex, Vf, x: np.ndarray,
                         x_match: float) -> tuple[complex, complex]:
    """Total log-derivatives of psi at x_match from both sides."""

    def rhs_u(xv, s):  # psi = exp(-i w x) u :  u'' - 2iw u' - V u = 0
        return [s[1], 2j * omega * s[1] + Vf(xv) * s[0]]

    def rhs_v(xv, s):  # psi = exp(+i w x) v :  v'' + 2iw v' - V v = 0
        return [s[1], -2j * omega * s[1] + Vf(xv) * s[0]]

    sol_l = solve_ivp(rhs_u, (x[0], x_match),
                      np.array([1.0, 0.0], complex),
                      method="DOP853", rtol=1e-12, atol=1e-14)
    sol_r = solve_ivp(rhs_v, (x[-1], x_match),
                      np.array([1.0, 0.0], complex),
                      method="DOP853", rtol=1e-12, atol=1e-14)
    ul, dul = sol_l.y[0][-1], sol_l.y[1][-1]
    vr, dvr = sol_r.y[0][-1], sol_r.y[1][-1]
    if abs(ul) < 1e-300 or abs(vr) < 1e-300 or not (sol_l.success and sol_r.success):
        return 1e12 + 0j, 1e12 + 0j
    return dul / ul - 1j * omega, dvr / vr + 1j * omega


def _factored_mismatch(omega: complex, Vf, x: np.ndarray,
                       x_match: float) -> float:
    """Absolute log-derivative gap |rp - lp| (NOT relative: degenerate at roots)."""
    lp, rp = _factored_log_derivs(omega, Vf, x, x_match)
    value = abs(rp - lp)
    if not np.isfinite(value):
        return 1e12
    return float(value)


def shoot_qnm(x: np.ndarray, V: np.ndarray, omega0: complex,
              match_frac: float = 0.5, maxiter: int = 300) -> dict:
    """Refine omega0 by minimising the factored log-derivative gap.

    Intended for exponentially-localised control potentials (Poschl-
    Teller family).  Returns the certified dict with the frozen
    C-gate fields.
    """
    # CubicSpline, not np.interp: measured (2026-10-06) the linear-kink
    # error saturates the mismatch at 1.1e-5 AT the exact root and costs
    # ~2 s per mismatch; the spline reaches 1.6e-8 and ~0.03 s per call,
    # so the full NM solve finishes in seconds at machine-level gap.
    spline = CubicSpline(x, V)
    Vf = lambda xv: float(spline(xv))
    x_match = x[0] + match_frac * (x[-1] - x[0])

    def misfit(z):
        return _factored_mismatch(complex(z[0], z[1]), Vf, x, x_match)

    res = minimize(misfit, [omega0.real, omega0.imag], method="Nelder-Mead",
                   options={"xatol": 1e-12, "fatol": 1e-16,
                            "maxiter": maxiter})
    omega = complex(res.x[0], res.x[1])
    return {
        "omega": omega,
        "mismatch": float(res.fun),
        "solver": "shooting_factored_neldermead",
        "nfev": int(res.nfev),
        "converged": bool(res.fun < 1e-8),
    }
