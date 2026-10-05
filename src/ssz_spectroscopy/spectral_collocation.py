"""Spectral collocation QNM solver (G152 solver B, Leaver-style).

Discretises psi'' + [omega^2 - V(x)] psi = 0 on a Chebyshev grid with
pure-ingoing boundary rows:

    interior rows:  omega^2 psi + D2 psi - V psi = 0
    x = xL (horizon):  D1 psi + i omega psi = 0
    x = xR (infinity): D1 psi - i omega psi = 0

This is a QUADRATIC eigenvalue problem (A2 w^2 + A1 w + A0) psi = 0,
solved through the standard companion linearisation

    [ 0    I  ] y = w [ I   0 ] y,   y = (w psi, psi),
    [ -A0 -A1 ]        [ 0   I ]

Spectrum filtered to Re w > 0, Im w < 0 (e^{+i w t} time convention:
QNMs in the lower half plane with Re w > 0).
"""
from __future__ import annotations

import numpy as np
from scipy.linalg import eig


def cheb_diff(n: int, xL: float, xR: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Chebyshev-Gauss-Lobatto grid + D1 + D2 on [xL, xR].

    Standard Trefethen construction: N = n+1 points on the CLOSED
    interval, D built row-wise and the diagonal fixed by the negative
    row-sum rule.
    """
    N = n + 1
    k = np.arange(N)
    theta = np.pi * k / n
    x = 0.5 * (xL + xR) - 0.5 * (xR - xL) * np.cos(theta)
    c = np.ones(N)
    c[0] = 2.0
    c[-1] = 2.0
    c[1:-1:2] = -1.0
    D1 = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            if i != j:
                D1[i, j] = (c[i] / c[j]) / (x[i] - x[j])
    np.fill_diagonal(D1, -D1.sum(axis=1))
    D2 = D1 @ D1
    return x, D1, D2


def colloc_qnm(V_func, xL: float, xR: float, n: int = 160,
               n_modes: int = 8) -> dict:
    """Solve the quadratic EVP; returns the QNM branch (Re>0, Im<0).

    ``V_func`` is a callable on the tortoise coordinate (use
    numpy.interp over an operator export, or an analytic potential).
    """
    x, D1, D2 = cheb_diff(n, xL, xR)
    V = np.asarray(V_func(x), float)
    N = n + 1
    I = np.eye(N)

    A0 = np.zeros((N, N), complex)   # constant part
    A1 = np.zeros((N, N), complex)   # linear in omega
    A2 = np.zeros((N, N), complex)   # quadratic part

    A0 = D2 - np.diag(V)
    A2 = I.copy()
    # BC rows are LINEAR in omega: their quadratic part MUST be zeroed
    A2[0] = 0.0
    A2[N - 1] = 0.0
    # BC rows:  D1 psi ± i omega psi = 0
    A0[0] = D1[0]
    A0[N - 1] = D1[N - 1]
    A1[0] = +1j * I[0]
    A1[N - 1] = -1j * I[N - 1]

    # companion linearisation (block algebra derived and calibrated on the
    # analytic Dirichlet box):  (A2 w^2 + A1 w + A0) psi = 0, y = (w psi, psi)
    #   row block 1:  y1 = w y2
    #   row block 2:  A2 w y1 + A1 y1 + A0 y2 = 0
    #                 -> MA[N:,:] = [A1, A0], MB[N:,:] = [-A2, 0]
    dim = 2 * N
    M_A = np.zeros((dim, dim), complex)
    M_B = np.zeros((dim, dim), complex)
    M_A[:N, :N] = I          # y1 - w y2 = 0
    M_B[:N, N:] = I
    M_A[N:, :N] = A1
    M_A[N:, N:] = A0
    M_B[N:, :N] = -A2

    vals = eig(M_A, M_B, right=False)
    vals = vals[np.isfinite(vals)]
    qnm = vals[(vals.real > 0) & (vals.imag < 0)]
    qnm = qnm[np.argsort(np.abs(qnm.imag))]
    return {
        "omega": [complex(w) for w in qnm[:n_modes]],
        "solver": "chebyshev_collocation_qevp",
        "n": int(n),
    }
