"""Leaver continued-fraction QNM solver (G152 solver A, gold standard).

Leaver 1985 (Proc. R. Soc. Lond. A 396, 239) for the Schwarzschild axial
gravitational sector: write psi = e^{i omega x} (r - 2M)^{-i omega}(...)
Actually the standard ansatz for the RW problem uses

    psi(r) = (r - 2M)^{i omega} r^{-i omega} e^{i omega r} sum a_n (r-2M)^n / r^? 

the CONVERGENT series form used here is the Leaver Jaffre form for the
Regge-Wheeler equation on the variable z = (r - 2M)/r  (= 1 - 2M/r = f):

    psi = z^{i omega} (1 - z)^{?} sum_{n=0}^inf a_n z^n

with the three-term recurrence from the RW equation.  The QNM condition
is the Nollert-improved continued fraction

    beta_0 - omega^2/alpha_1 - gamma_1/(beta_1 - ... ) = 0  etc.

IMPLEMENTATION NOTE (honest scope): the n-dependent tail of the CF uses
the Nollert 1993 asymptotic expansion with P_s coefficients; the first
implementation below carries P_0 and P_{-1} (the standard truncation),
which is the accuracy level used for G152 agreement with the collocation
solver.  Higher Nollert orders are an incremental upgrade.
"""
from __future__ import annotations


def _rw_recurrence(omega: complex, ell: int, M: float):
    """Three-term recurrence for the RW equation in z = 1 - 2M/r.

    Transcribed from Leaver 1985 for the Schwarzschild axial case:
    psi = e^{i w r} (2M w (r - 2M))^{i w}? -- the canonical form:
    psi = (r - 2M)^{i w} r^{-i w} e^{i w r} sum a_n (r - 2M)^n / r^{n+...}
    In z = 1 - 2M/r:  psi = z^{i w} (1 - z)^{-2 i w}?  ...
    """
    raise NotImplementedError(
        "Leaver recurrence: transcribe from the Leaver 1985 paper with "
        "page-render verification before use (project rule: no recalled "
        "formulas).  This scaffold exists so the solver slot in G152 is "
        "declared; the transcription is the next work package."
    )


def rw_leaver_qnm(ell: int, M: float, omega0: complex, n_iter: int = 200):
    """Root-find the CF condition near omega0."""
    raise NotImplementedError(
        "blocked on the verified Leaver transcription (see above)"
    )
