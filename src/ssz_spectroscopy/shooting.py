"""Shooting solver for the Schrodinger-form QNM problem (G152 solver A).

Leaver-type integration of
    psi'' + [omega^2 - V(x)] psi = 0
on the tortoise grid with PURE INGOING boundary conditions
    psi ~ exp(-i omega x)  as x -> -infinity (horizon side),
    psi ~ exp(-i omega (x - X)) as x -> +infinity?  NO:
pure-ingoing at BOTH ends (quasinormal normalisation):
    psi ~ exp(-i omega x)   for x -> -inf
    psi ~ exp(+i omega x)   for x -> +inf
Wait: convention check lives in boundary_conditions.py with the analytic
Pöschl-Teller control problem; the solver itself only integrates the ODE
and minimises the Wronskian-mismatch misfit.
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import minimize


def _ingoing_mismatch(omega: complex, x: np.ndarray, V: np.ndarray,
                      x_match: float) -> float:
    """Integrate from both ends and return the log |Wronskian mismatch|."""

    def rhs(xv, y):
        return [y[1], (V(xv) - omega**2) * y[0]]

    # horizon side: psi = exp(-i w x) -> psi' = -i w psi
    y0_l = [1.0, -1j * omega]
    sol_l = solve_ivp(rhs, (x[0], x_match), y0_l, method="RK4",
                      t_eval=None, rtol=1e-10, atol=1e-12, dense_output=False)
    # infinity side: psi = exp(+i w (x - x[-1]))
    y0_r = [1.0, 1j * omega]
    _sol_r = solve_ivp(rhs, (x[-1], x_match), y0_r, method="RK4",
                      rtol=1e-10, atol=1e-12)

    def rhs_back(xv, y):
        return [-y[1], -(V(xv) - omega**2) * y[0]]

    sol_rb = solve_ivp(rhs_back, (x[-1], x_match), [1.0, -1j * omega],
                       method="RK4", rtol=1e-10, atol=1e-12)
    psi_l, dpsi_l = sol_l.y[0][-1], sol_l.y[1][-1]
    psi_r, dpsi_r = sol_rb.y[0][-1], -sol_rb.y[1][-1]
    W = psi_l * dpsi_r - dpsi_l * psi_r
    scale = (abs(psi_l) * abs(dpsi_r) + abs(dpsi_l) * abs(psi_r))
    if scale == 0 or not np.isfinite(W):
        return 50.0
    return float(np.log(abs(W) / scale + 1e-300))


def shoot_qnm(x: np.ndarray, V: np.ndarray, omega0: complex,
              match_frac: float = 0.5) -> dict:
    """Refine omega0 by minimising the boundary mismatch (Nelder-Mead).

    Returns the certified dict with the frozen C-gate fields.
    """
    Vf = lambda xv: np.interp(xv, x, V)
    x_match = x[0] + match_frac * (x[-1] - x[0])

    def misfit(z):
        return _ingoing_mismatch(complex(z[0], z[1]), x, Vf, x_match)

    res = minimize(misfit, [omega0.real, omega0.imag], method="Nelder-Mead",
                   options={"xatol": 1e-10, "fatol": 1e-12,
                            "maxiter": 4000})
    omega = complex(res.x[0], res.x[1])
    return {
        "omega": omega,
        "mismatch": float(res.fun),
        "solver": "shooting_rk4_neldermead",
        "nfev": int(res.nfev),
        "converged": bool(res.fun < 1e-8),
    }
