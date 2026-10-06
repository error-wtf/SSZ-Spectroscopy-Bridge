"""Leaver continued-fraction QNM solver (frequency-domain layer).

Transcribed from Leaver 1991, "Remarks on the continued-fraction method
for computing black-hole quasinormal frequencies and modes" (review of
Proc. R. Soc. Lond. A 402, 285 [1985]), with the recurrence coefficients
EXACTLY as printed there (Eq. 5):

    alpha_n = n^2 + (2 rho + 2) n + 2 rho + 1
    beta_n  = -[2 n^2 + (8 rho + 2) n + 8 rho^2 + 4 rho + l(l+1) - epsilon]
    gamma_n = n^2 + 4 rho n + 4 rho^2 - epsilon - 1
    rho = -i omega

Units: c = G = 2M = 1 (Leaver's convention; omega is 2x the M*omega of the
Konoplya-Rezzolla-Zhidenko tables).

Field spin parameter epsilon: -1 scalar, 0 electromagnetic, 3 gravitational.

The QNM condition is beta_0/alpha_0 + F(rho) = 0, where F is the continued
fraction of Eq. (6), evaluated downward (Gautschi) from a large n.  The
expression is analytic in rho, so |.| is a clean Nelder-Mead target.

VALIDATION (tests/unit/test_leaver.py): reproduces Berti's ringdown data
(pages.jh.edu/~eberti2/ringdown/, s2l2.dat / s0l0.dat, themselves Leaver-
method values with table errors ~1e-12) to |delta omega| <= 4e-15 on
l=2 n=0..3 (gravitational) and l=0 n=0,1 (scalar).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

# field spin parameter epsilon by perturbation family (Leaver Eq. 1: eps=-1,0,3)
EPSILON = {"scalar": -1, "em": 0, "gravitational": 3}


def _cf_misfit(omega: complex, ell: int, eps: int, n_max: int) -> float:
    """|beta_0/alpha_0 + F(rho)|: analytic, zero exactly at QNMs (Leaver Eq. 9)."""
    rho = -1j * omega

    def alpha(n: int) -> complex:
        return n * n + (2 * rho + 2) * n + 2 * rho + 1

    def beta(n: int) -> complex:
        return -(2 * n * n + (8 * rho + 2) * n + 8 * rho * rho
                 + 4 * rho + ell * (ell + 1) - eps)

    def gamma(n: int) -> complex:
        return n * n + 4 * rho * n + 4 * rho * rho - eps - 1

    tail = 0.0 + 0.0j
    for n in range(n_max, 1, -1):
        denom = beta(n) - tail
        if denom == 0:
            return 1e12
        tail = alpha(n - 1) * gamma(n) / denom
    frac = -gamma(1) / (beta(1) - tail)
    value = beta(0) / alpha(0) + frac
    if not np.isfinite(value):
        return 1e12
    return abs(value)


def rw_leaver_qnm(omega0: complex, ell: int = 2, family: str = "gravitational",
                  n_max: int = 800, xatol: float = 1e-13,
                  maxiter: int = 400) -> dict:
    """Refine omega0 (units 2M=1) to the nearest QNM root. Nelder-Mead.

    Returns dict with omega, misfit, converged (misfit < 1e-10), nfev.
    """
    if family not in EPSILON:
        raise ValueError(f"unknown family {family!r} (use {sorted(EPSILON)})")
    eps = EPSILON[family]

    def misfit(z) -> float:
        return _cf_misfit(complex(z[0], z[1]), ell, eps, n_max)

    res = minimize(misfit, [float(omega0.real), float(omega0.imag)],
                   method="Nelder-Mead",
                   options={"xatol": xatol, "fatol": 1e-18, "maxiter": maxiter})
    omega = complex(res.x[0], res.x[1])
    return {
        "omega": omega,
        "misfit": float(res.fun),
        "solver": "leaver_continued_fraction",
        "units": "c=G=2M=1",
        "ell": int(ell),
        "family": family,
        "n_max": int(n_max),
        "nfev": int(res.nfev),
        "converged": bool(res.fun < 1e-10),
    }
