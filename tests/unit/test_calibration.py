"""Calibration tests: the solver infrastructure must be EXACT where an
analytic answer exists (this is the honesty anchor of G151/G152)."""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import eig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssz_spectroscopy.operator import (
    FailClosed,
    rw_potential,
    rw_tortoise,
)
from ssz_spectroscopy.spectral_collocation import cheb_diff


def test_cheb_matrices_spectral_accuracy():
    """D1/D2 must differentiate e^{ikx} to machine precision."""
    _x, D1, D2 = cheb_diff(40, -1.0, 1.0)
    k = 3.7
    psi = np.exp(1j * k * _x)
    err1 = np.max(np.abs(D1 @ psi - 1j * k * psi))
    err2 = np.max(np.abs(D2 @ psi + k**2 * psi))
    assert err1 < 1e-11
    assert err2 < 1e-9


def test_companion_linearisation_dirichlet_box_exact():
    """Free wave equation, Dirichlet box: omega = pi k /(2L) exactly.

    This is the calibration of the quadratic-EVP companion form; any
    failure here invalidates the QNM solver entirely.
    """
    L, n = 1.0, 80
    _x, _D1, D2 = cheb_diff(n, -L, L)
    N = n + 1
    I = np.eye(N)
    A0 = D2.copy()
    A1 = np.zeros((N, N), complex)
    A2 = I.copy()
    A0[0] = I[0]
    A0[N - 1] = I[N - 1]
    A2[0] = 0
    A2[N - 1] = 0
    dim = 2 * N
    MA = np.zeros((dim, dim), complex)
    MB = np.zeros((dim, dim), complex)
    MA[:N, :N] = I
    MA[N:, :N] = A1
    MA[N:, N:] = A0
    MB[:N, N:] = I
    MB[N:, :N] = -A2
    vals = eig(MA, MB, right=False)
    vals = vals[np.isfinite(vals)]
    vals = vals[np.abs(vals.imag) < 1e-8]
    got = np.sort(vals[vals.real > 0].real)[:5]
    ana = np.pi * np.arange(1, 6) / (2 * L)
    assert np.max(np.abs(got - ana)) < 1e-9


def test_rw_potential_closed_form():
    """V_RW must equal the analytic Regge-Wheeler expression on probes."""
    r = np.linspace(1.05, 40.0, 7)
    for ell in (2, 3):
        V = rw_potential(r, ell, M=0.5)
        f = 1.0 - 1.0 / r
        V_ref = f * (ell * (ell + 1) / r**2 - 3.0 / r**3)
        assert np.max(np.abs(V - V_ref)) < 1e-14


def test_rw_tortoise_monotone_and_known():
    x = rw_tortoise(np.array([1.2, 2.0, 3.0, 10.0]), M=0.5)
    assert np.all(np.diff(x) > 0)
    # x(r) = r + ln(r - 1) for M = 1/2
    assert abs(x[1] - (2.0 + np.log(1.0))) < 1e-12


def test_ssz_channel_is_fail_closed():
    from ssz_spectroscopy.operator import ssz_axial_operator
    with pytest.raises(FailClosed):
        ssz_axial_operator()
