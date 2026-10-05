"""SSZ axial QNM operator (G150 producer module).

STATUS (declared, fail-closed):
  * CONTROL channel: Regge-Wheeler axial gravitational operator is EXACT
    (analytic), used by G151/G154 before any SSZ claim:
        ds2 = -f dt2 + dr2/f + r2 dOmega^2,  f = 1 - 2M/r,
        dx = dr / f                          (tortoise)
        V_RW = f * [ l(l+1)/r^2 - 6 M / r^3 ]
    Reference spectrum (Chandrasekhar-Detweiler / Leaver):
        l=2 n=0:  omega = 0.3736723 - 0.0889623 i   (M = 1/2 units)
  * SSZ channel: the general-(f, h) axial potential on
        ds2 = -f dt2 + dr2/h + r2 dOmega^2
    is NOT yet implemented -- the symbolic derivation from the odd-parity
    master identity must land first (sympy, with the RW limit as an
    exactness test).  Every SSZ entry point raises FailClosed until then.
    Rationale: a "plausible" potential assembled from memory would risk
    failing the control limit silently; the contract forbids invented
    shortcuts (GATES_MANIFEST lineage rules).
"""
from __future__ import annotations

import numpy as np


class FailClosed(NotImplementedError):
    """Raised when an SSZ-channel entry point is used before its
    symbolic derivation and tests land."""


def rw_tortoise(r: np.ndarray, M: float = 0.5) -> np.ndarray:
    """x(r) = r + 2M ln(r/(2M) - 1), on r > 2M."""
    return r + 2.0 * M * np.log(r / (2.0 * M) - 1.0)


def rw_potential(r: np.ndarray, ell: int, M: float = 0.5) -> np.ndarray:
    """Regge-Wheeler axial gravitational potential, Schrodinger form."""
    f = 1.0 - 2.0 * M / r
    return f * (ell * (ell + 1) / r**2 - 6.0 * M / r**3)


def rw_operator_export(ell: int, M: float = 0.5, n_r: int = 2000,
                       r_min_factor: float = 1.02,
                       r_max: float = 60.0) -> dict:
    """G150-shaped export of the CONTROL operator (exact analytic form).

    Returns the fields, the tortoise grid and a hashable payload.  The
    independent re-derivation check (G150 criterion) for the control
    problem is analytic: V_RW against the closed form on random probes.
    """
    r = np.linspace(2.0 * M * r_min_factor, r_max, int(n_r))
    x = rw_tortoise(r, M)
    V = rw_potential(r, ell, M)
    f = 1.0 - 2.0 * M / r
    return {
        "operator": "axial_gravitational_reggewheeler",
        "form": "schrodinger",
        "ell": int(ell),
        "M": float(M),
        "r": r, "x": x, "V": V, "f": f,
        "reference_omega_l2n0": complex(0.3736723, -0.0889623),
        "assembly": "V = f [l(l+1)/r^2 - 6M/r^3], dx = dr/f (exact analytic)",
    }


def ssz_axial_operator(*_args, **_kwargs):
    """SSZ general-(f,h) axial operator: NOT IMPLEMENTED YET (fail-closed).

    Blocked on: symbolic derivation of the axial master potential for
    ds2 = -f dt2 + dr2/h + r2 dOmega2 from the odd-parity master identity,
    with the exact RW limit as an embedded test.  Do NOT assemble V from
    recalled formulas -- the control limit is the arbiter.
    """
    raise FailClosed(
        "ssz_axial_operator requires the symbolic (f,h) axial derivation "
        "(G150 pre-work); RW control channel is available via "
        "rw_operator_export()"
    )
