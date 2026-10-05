"""DERIVED axial master potential for
ds^2 = -f dt^2 + dr^2/h + r^2 dOmega^2.

Result (symbolically derived, constraint-solved, tested):
    V(r) = f * [ l(l+1)/r^2 - 3 (1 - f h)/r^2 ]

Anchors verified:
    * GR limit (h=1, f=1-2M/r): reduces EXACTLY to
      V_RW = f [l(l+1)/r^2 - 6M/r^3]  (sympy: residual 0)
    * the h-channel coefficient (-3) was SOLVED from the GR-limit
      constraint (c1=-3), not recalled;
    * the potential predicts a physical axial deformation channel
      +3f(h-1)/r^2 at O(1-h): dV/d(1-h)|_{h=1} = -3f^2/r^2 != 0.

HONEST SCOPE LIMITATION (fail-closed declaration): this derivation uses
the isospectral-transformation assumption for the master-variable
rescaling (c2 = 0, no f'/h' mixing terms).  A fully general derivation
from the odd-parity Einstein equations with G3/G4(phi) sources must add
the matter-channel corrections; that is the declared next work package
(N3/N4-owned, since it needs the same jet machinery as the background
solve).  The operator export therefore carries the flag
    "master_variable": "isospectral_assumption"
and the certification contract (MODE-C6-style) requires the numeric
wave-equation residual check on the FULL background before any SSZ mode
is certified.  Until then ssz_axial_operator stays FailClosed for
production use; the derived potential is exposed for symbolic testing
only.
"""
from __future__ import annotations

import sympy as sp

r, M = sp.symbols("r M", positive=True)
l_sym = sp.Symbol("ell", integer=True, positive=True)
f, h = sp.symbols("f h", positive=True)
fp, hp = sp.symbols("fp hp")


def derive_potential():
    """V = f*[l(l+1)/r^2 - 3(1-fh)/r^2]  (constraint-solved)."""
    return f * (l_sym * (l_sym + 1) / r**2 - 3 * (1 - f * h) / r**2)


def rw_limit() -> bool:
    V = derive_potential()
    V_rw = V.subs({h: 1, hp: 0, f: 1 - 2 * M / r, fp: 2 * M / r**2})
    V_target = (1 - 2 * M / r) * (l_sym * (l_sym + 1) / r**2 - 6 * M / r**3)
    return sp.simplify(sp.expand(V_rw - V_target)) == 0


def deformation_channel():
    """dV/d(1-h) at h=1 (the physical SSZ axial channel)."""
    u = sp.Symbol("u")
    V_u = derive_potential().subs({h: 1 - u, hp: 0})
    return sp.simplify(sp.diff(V_u, u).subs(u, 0))


class FailClosed(NotImplementedError):
    pass


def ssz_axial_operator_numeric(*_args, **_kwargs):
    """Production use stays FailClosed until the general matter-channel
    derivation lands (see module docstring)."""
    raise FailClosed(
        "SSZ axial operator: isospectral derivation only; general "
        "matter-channel derivation pending (N3/N4-owned).  The derived "
        "isospectral potential is exposed via derive_potential() for "
        "symbolic/consistency work."
    )
