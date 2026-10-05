"""Time-domain QNM extraction (G154 attack path 3).

Evolve  psi_tt = psi_xx - V(x) psi  on the tortoise grid with an explicit
second-order leapfrog scheme and outgoing (advection) boundary rows.
Record psi at a detector point on the far side, then extract the
damped-exponential content of the late-time signal with a matrix-pencil
(Prony) fit.

Why this route: the frequency-domain collocation with ingoing BC rows
returned the box-leakage branch (documented in README); the time-domain
signal is insensitive to BC details once the pulse has left the grid --
the late-time ringdown IS the QNM.  No BC approximation of the open
condition is needed; only enough grid for the extraction window.

Everything analytic: V is evaluated in closed form on the grid (RW
control problem), no interpolation of the potential.
"""
from __future__ import annotations

import numpy as np


def rw_setup(M: float = 0.5, ell: int = 2, xL: float = -35.0,
             xR: float = 40.0, n: int = 6000):
    """Analytic RW fields on a uniform tortoise grid.

    r(x) via Newton on x = r + 2M ln(r/(2M) - 1); V closed form.
    """
    def r_of(x0):
        # bracketed bisection-Newton: x(r) is monotone on (2M, inf)
        lo, hi = 2.0 * M * (1.0 + 1e-13), 2.0 * M + 1.0
        def f(r):
            return r + 2 * M * np.log(r / (2 * M) - 1.0) - x0
        while f(hi) < 0:
            hi = 2 * M + (hi - 2 * M) * 2 + 1e-12
        r = 0.5 * (lo + hi)
        for _ in range(200):
            fr = f(r)
            if abs(fr) < 1e-14:
                break
            if fr > 0:
                hi = r
            else:
                lo = r
            r = 0.5 * (lo + hi)
        return r

    x = np.linspace(xL, xR, int(n))
    r = np.array([r_of(float(v)) for v in x])
    f = 1.0 - 2.0 * M / r
    V = f * (ell * (ell + 1) / r**2 - 6.0 * M / r**3)
    return x, r, V


def evolve(x: np.ndarray, V: np.ndarray, x_det: float, t_max: float,
           pulse_center: float | None = None, pulse_sigma: float = 1.5,
           outflow: bool = True, cfl: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
    """Leapfrog evolution; returns (t, signal) sampled at x_det."""
    dx = x[1] - x[0]
    dt = cfl * dx
    n_t = int(t_max / dt)
    n = len(x)
    i_det = int(np.argmin(np.abs(x - x_det)))

    if pulse_center is None:
        pulse_center = x[0] + 0.25 * (x[-1] - x[0])

    psi = np.exp(-((x - pulse_center) ** 2) / (2 * pulse_sigma**2))
    # launch the pulse TOWARD the barrier: for psi_tt = psi_xx the
    # rightward solution is f(x - t), i.e. pi = psi_t = -f' = -dpsi
    dpsi = np.gradient(psi, dx)
    pi_ = -dpsi

    # sparse Laplacian applied via vectorized slicing (periodic-free):
    # lap = (psi[i-1] - 2 psi[i] + psi[i+1]) / dx^2, boundaries by copy
    inv_dx2 = 1.0 / (dx * dx)

    t = 0.0
    sig = np.empty(n_t)
    for k in range(n_t):
        sig[k] = psi[i_det]
        psi_h = psi + 0.5 * dt * pi_
        lap = np.empty(n)
        lap[1:-1] = (psi_h[:-2] - 2.0 * psi_h[1:-1] + psi_h[2:]) * inv_dx2
        lap[0] = lap[1]
        lap[-1] = lap[-2]
        pi_ = pi_ + dt * (lap - V * psi_h)
        psi = psi_h + 0.5 * dt * pi_
        if outflow:
            psi[0] = psi[1]
            psi[-1] = psi[-2]
            pi_[0] = pi_[1]
            pi_[-1] = pi_[-2]
        if not np.isfinite(psi).all():
            raise FloatingPointError(f"diverged at step {k} (t={t:.2f})")
        t += dt
    return np.linspace(0.0, t_max, n_t), sig


def extract_qnm(sig: np.ndarray, t: np.ndarray, n_modes: int = 3,
                t_start_frac: float = 0.5, max_rows: int = 2000) -> list[complex]:
    """Matrix-pencil QNM extraction (Hua-Sarkar TLS formulation, compact).

    The Hankel matrix is capped at `max_rows` rows (uniform row-skip)
    so the SVD stays bounded; the pencil poles are unchanged by row
    decimation as long as dt_eff stays the sampling of the model.
    """
    dt = float(t[1] - t[0])
    s = sig[int(len(sig) * t_start_frac):]
    N = len(s)
    if N > 4 * max_rows:
        skip = N // (4 * max_rows) + 1
        s = s[::skip]
        dt = dt * skip
        N = len(s)
    L = max(8, N // 3)
    Y = np.empty((N - L + 1, L), complex)
    for i in range(N - L + 1):
        Y[i] = s[i:i + L]
    U, sv, Vh = np.linalg.svd(Y, full_matrices=False)
    U = U[:, :n_modes]
    Vh = Vh[:n_modes]
    sv = sv[:n_modes]
    # TLS pencil
    Y1 = U @ np.diag(sv) @ Vh
    Z1 = Y1[:, :-1]
    Z2 = Y1[:, 1:]
    P = np.linalg.pinv(Z1) @ Z2
    poles = np.linalg.eigvals(P)
    mu = np.log(poles.astype(complex)) / dt
    # signal model: psi ~ exp(-i w t)  =>  mu = -i w  =>  w = +i*mu
    # (time dependence e^{+i w t} convention: w in lower half plane)
    omegas = 1j * mu
    # keep the physical branch: mu's real part must be NEGATIVE (decay)
    out = [
        complex(w) for w, m in zip(omegas, mu)
        if m.real < 0 and 0.05 < w.real < 20.0 and -20.0 < w.imag < -1e-6
    ]
    return sorted(out, key=lambda w: abs(w - complex(0.37, -0.09)))
