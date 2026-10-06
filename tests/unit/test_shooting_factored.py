"""Factored shooting solver: Poschl-Teller control with the exact root.

Exact QNM (Cardona-Molina, CQG 34, 245002 (2017), Eq. 38):
V = V0 sech^2(k x)  ->  omega_n = k [ -i (n + 1/2) +- sqrt(V0/k^2 - 1/4) ]
V0 = 2, k = 1  ->  omega_0 = sqrt(7)/2 - 0.5 i.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))

from ssz_spectroscopy.shooting import shoot_qnm

W_EXACT = complex(np.sqrt(7) / 2, -0.5)


@pytest.fixture()
def pt_problem():
    x = np.linspace(-20.0, 20.0, 8001)
    V = 2.0 / np.cosh(x) ** 2
    return x, V


def test_pt_root_from_crude_seed(pt_problem):
    x, V = pt_problem
    res = shoot_qnm(x, V, complex(1.3, -0.55))
    assert res["converged"], f"mismatch {res['mismatch']:.2e}"
    # measured: CubicSpline + DOP853 rtol=1e-12 reach |root - exact| = 3.8e-9
    assert abs(res["omega"] - W_EXACT) < 1e-7, (
        f"root {res['omega']} vs exact {W_EXACT}")


def test_pt_mismatch_is_sharp_not_flat(pt_problem):
    """The factored absolute metric must show a real dip at the root
    (the old relative metric saturated at 1.0 on the whole line)."""
    x, V = pt_problem
    res = shoot_qnm(x, V, W_EXACT * 1.02)
    at_root = res["mismatch"]
    # a point 5e-3 away in Re(w) must be clearly worse
    from scipy.interpolate import CubicSpline

    from ssz_spectroscopy.shooting import _factored_mismatch
    spline = CubicSpline(x, V)
    Vf = lambda xv: float(spline(xv))
    off = _factored_mismatch(W_EXACT + 5e-3, Vf, x, 0.0)
    assert off > 1e3 * max(at_root, 1e-12), (at_root, off)


def test_solver_label_updated():
    x = np.linspace(-10, 10, 2001)
    V = 2.0 / np.cosh(x) ** 2
    res = shoot_qnm(x, V, W_EXACT, maxiter=5)
    assert res["solver"] == "shooting_factored_neldermead"
