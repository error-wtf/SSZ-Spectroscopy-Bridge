"""Leaver continued-fraction solver: validation against Berti's ringdown data.

Reference values downloaded from pages.jh.edu/~eberti2/ringdown/
(s2l2.dat, s0l0.dat; Berti's Leaver-method tables carry table errors
~1e-12, so agreement to |delta omega| < 1e-9 is machine-level success).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(SRC))

from ssz_spectroscopy.continued_fraction import rw_leaver_qnm

# (ell, family, overtone context, published omega (2M=1), seed = published value)
BERTI_REFS = [
    # s2l2.dat rows n=0..3 (gravitational, ell=2)
    (2, "gravitational", complex(0.7473433688360838, -0.1779246313778714)),
    (2, "gravitational", complex(0.6934219937583268, -0.5478297505824697)),
    (2, "gravitational", complex(0.6021069092247328, -0.9565539664461437)),
    (2, "gravitational", complex(0.5030099243711814, -1.4102964048669913)),
    # s0l0.dat rows n=0,1 (scalar, ell=0)
    (0, "scalar", complex(0.2209098781608393, -0.2097914341737619)),
    (0, "scalar", complex(0.1722338366727985, -0.6961048936129209)),
]


@pytest.mark.parametrize("ell,family,w_pub", BERTI_REFS)
def test_leaver_reproduces_berti_tables(ell, family, w_pub):
    # l=0 n=1 needs the deep tail (zero-tail truncation converges as n_max
    # grows; measured: 1.5e-8 @800, 3.6e-11 @1500, 2e-16 @4000)
    res = rw_leaver_qnm(w_pub, ell=ell, family=family, n_max=4000)
    assert res["converged"], f"misfit {res['misfit']:.2e}"
    assert abs(res["omega"] - w_pub) < 1e-9, (
        f"|root - published| = {abs(res['omega'] - w_pub):.2e}")


def test_leaver_recovers_gravitational_fundamental_from_crude_seed():
    # seed 1% away must still converge to the same root
    w_pub = complex(0.7473433688360838, -0.1779246313778714)
    res = rw_leaver_qnm(w_pub * 1.01, ell=2, family="gravitational")
    assert res["converged"]
    assert abs(res["omega"] - w_pub) < 1e-9


def test_leaver_units_documented():
    # omega is 2x M*omega: M*omega(l=2,n=0) must equal the published
    # 0.37367 - 0.08896i of the Konoplya-Rezzolla-Zhidenko tables
    res = rw_leaver_qnm(complex(0.7473433688360838, -0.1779246313778714),
                        ell=2, family="gravitational")
    m_omega = res["omega"] / 2
    assert abs(m_omega - complex(0.37367, -0.08896)) < 1e-5


def test_leaver_rejects_unknown_family():
    with pytest.raises(ValueError, match="unknown family"):
        rw_leaver_qnm(complex(0.7, -0.2), ell=2, family="fermionic")
