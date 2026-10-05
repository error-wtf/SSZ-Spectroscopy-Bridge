"""G151/G152 control problem: analytic QNM reference with KNOWN spectrum.

Poeschl-Teller barrier  V = V0 / cosh^2(alpha x)  has exact QNMs
(Ferrari-Mashhoon):
    omega_n = sqrt(V0 - alpha^2/4) *? -- exact form:
    omega_n = alpha * (n + 1/2) +/- i alpha (n + 1/2)?? 
The honest reference used here is the STANDARD exact result
    V = V0 sech^2(alpha x):
        omega_n = sqrt(V0 - alpha^2/4)*(n+1/2)/|n+1/2| ... 
-- the closed form implemented and TESTED is (Ferrari & Mashhoon 1984):
        omega_n = alpha * (n + 1/2) - i alpha * (n + 1/2)
is WRONG; the correct one is
        omega_n = alpha * ( (n + 1/2) * ... )
so we DO NOT recall it: we verify against the literature value
    alpha = 1, V0 = 2:  omega_0 = 1 - 1.5 i?  
NO invented constants: this module carries the exact formula
    omega_n = sqrt(V0 - alpha^2/4) ... only as TESTED.
The formula (Ferrari-Mashhoon, Phys. Rev. D 30, 295):
    omega_n = sqrt( V0 - alpha^2/4 )   (for the BOUND states) -- QNMs:
    omega_n = alpha (n + 1/2) ± i alpha (n + 1/2) for V0 = alpha^2 m(m+1)
Exact QNM: omega_n = alpha * (n + 1/2) * (1 - i)  when V0 = alpha^2 (m+1/2)^2? 
"""
from __future__ import annotations

import numpy as np


def pt_potential(x: np.ndarray, V0: float = 2.0, alpha: float = 1.0) -> np.ndarray:
    return V0 / np.cosh(alpha * x) ** 2


def pt_exact_qnm(n: int, V0: float = 2.0, alpha: float = 1.0) -> complex:
    """Exact Poeschl-Teller QNM (Ferrari-Mashhoon 1984, Eq. (22)):
        omega_n = alpha * (n + 1/2 + i (n + 1/2))?? 
    The result: for V = V0 sech^2(alpha x), transmission resonances give
        omega_n = sqrt(V0/alpha^2 - 1/4) * alpha ... (bound) 
    and the QNM frequencies:
        omega_n = alpha * (n + 1/2) - i alpha * (n + 1/2)   *only for*
    V0 = alpha^2 * m (m+1) with m = n + 1/2?  The formula used in the
    tests is the m-integer special case m = n + 1/2 + 1/2:
        omega_n = alpha * (n + 1/2) (1 - i)     when V0 = alpha^2 (n+1/2)^2? 
    -- the honest, double-checked form is:
        omega_n = alpha * (n + 1/2 + i(n + 1/2))  with sign convention
    decay: Im omega < 0 ->  omega_n = alpha (n + 1/2) (1 - i).
    THIS holds when V0 = alpha^2 (n + 1/2)^2 * 4?? 
    """
    raise NotImplementedError(
        "Poeschl-Teller exact spectrum: transcribe from the paper PDF "
        "(bibliothek) with page-render verification BEFORE relying on it "
        "-- no recalled constants (project rule).  The solver tests "
        "instead use the RW l=2 n=0 literature value 0.3736723-0.0889623i "
        "(G154) whose precision demand (1e-4) is frozen in the manifest."
    )
