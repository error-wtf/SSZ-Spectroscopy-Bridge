"""Tests for the symbolically derived SSZ axial potential."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ssz_spectroscopy.ssz_axial_symbolic import (
    FailClosed,
    deformation_channel,
    rw_limit,
    ssz_axial_operator_numeric,
)


def test_rw_limit_exact():
    assert rw_limit() is True


def test_deformation_channel_nonzero():
    """The physical SSZ axial channel: dV/d(1-h)|_{h=1} = -3 f^2/r^2 != 0.

    The axial sector DOES feel a conformal metric deformation at linear
    order in this derivation — that is a physics prediction, not a bug.
    """
    d = deformation_channel()
    assert d is not False
    assert d != 0


def test_potential_structure():
    """The h-channel must enter as -3(1-fh)/r^2 (constraint-solved)."""
    import sympy as sp

    from ssz_spectroscopy import ssz_axial_symbolic as mod

    V = mod.derive_potential()
    expected = mod.f * (mod.l_sym * (mod.l_sym + 1) / mod.r**2
                        - 3 * (1 - mod.f * mod.h) / mod.r**2)
    assert sp.simplify(V - expected) == 0


def test_production_entry_fail_closed():
    with pytest.raises(FailClosed):
        ssz_axial_operator_numeric()
