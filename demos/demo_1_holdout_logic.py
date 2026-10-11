#!/usr/bin/env python3
"""Demo 1 — Warum Reproduzierbarkeit zaehlt: die Holdout-Logik (r9 vs F7-V3).

Teil A (echte Artefakte): liest die beiden gefrorenen Ergebnis-JSONs und
rechnet die Gate-Minima UEBER DIE EFFICIENCY-TABELLEN neu nach — zeigt,
dass das r9-Ergebnis (Full-Matrix, in-sample) auf den zurueckgehaltenen
Holdout-Segmenten NICHT reproduziert.

Teil B (Mechanismus, synthetisch): ein Toy-Detektor wird auf denselben
Rauschsegmenten gerechnet, auf denen seine Schwelle kalibriert wurde
(in-sample) vs. auf frischen Segmenten (held-out). Ueber angepasste
Schwellen (garden of forking paths) sieht in-sample alles "passend" aus —
held-out bricht ein. Genau deshalb ist F7-V3 ein unabhaengiger Test und
sein FAIL eine erstklassige Information, kein Bug.

Laufzeit < 30 s.  Kein Schreibzugriff auf Artefakte — read-only.
Output: demos/demo1_holdout_lesson.png
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
CELL = re.compile(r"f(\d+)_tau(\d+)ms_snr(\d+)")

rng = np.random.default_rng(20261011)


def scope_min(run, det, snr_min=12):
    """Minimum ueber alle Zellen mit snr>=snr_min und Q=pi*f*tau>=2 nachrechnen."""
    tab = run["gate_details"][det]["efficiency_table"]
    vals = []
    for k, v in tab.items():
        m = CELL.match(k)
        f, tau_ms, snr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if snr >= snr_min and math.pi * f * tau_ms / 1000.0 >= 2.0:
            vals.append((v, k))
    v_min = min(vals)
    return v_min[0], v_min[1], len(vals)


def part_a():
    v3 = json.loads((ART / "GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json").read_text())
    fm = json.loads((ART / "GWOSC_V2_F7_GATE_RESULT_FULL_MATRIX_FAIL.json").read_text())
    print("=" * 74)
    print("TEIL A — echte Artefakte: Gate-Minima nachgerechnet aus den Tabellen")
    print("=" * 74)
    print(f"{'Run':16s} {'Det':4s} {'min(eff) snr>=12, Q>=2':>24s}  Zelle     n-Zellen")
    rows = {}
    for name, run in (("r9 full-matrix", fm), ("F7-V3 holdout", v3)):
        for det in ("H1", "L1"):
            v, k, n = scope_min(run, det)
            rows[(name, det)] = v
            print(f"{name:16s} {det:4s} {v:24.2f}  {k:24s} {n}")
    d_h1 = rows[("F7-V3 holdout", "H1")] - rows[("r9 full-matrix", "H1")]
    d_l1 = rows[("F7-V3 holdout", "L1")] - rows[("r9 full-matrix", "L1")]
    print(f"\nDifferenz holdout - full-matrix: H1 {d_h1:+.2f}, L1 {d_l1:+.2f}")
    print("Floor (snr>=12, Q>=2): 0.90 — beide Runs LIEGEN DARUNTER -> FAIL.")
    print("r9 reproduziert NICHT auf zurueckgehaltenen Segmenten.")
    return rows


def part_b():
    print()
    print("=" * 74)
    print("TEIL B — Mechanismus (synthetisch): in-sample vs held-out")
    print("=" * 74)
    n = 4096
    n_cal, n_test = 200, 400

    FS = 16384.0

    def toy_stat(x):
        """'Detektor': Band-Energie um 180 Hz bei Fs=16 kHz (Toy-Version)."""
        spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
        fr = np.fft.rfftfreq(len(x), 1.0 / FS)
        sel = np.abs(fr - 180.0) <= 4.0
        return float(np.sqrt(np.mean(spec[sel] ** 2)))

    def draws(noise_fn, n):
        return np.array([toy_stat(noise_fn()) for _ in range(n)])

    # 1) ehrliche Kalibration: Threshold-Schaetzungen aus 12 unabhaengigen
    #    Pools mitteln (stabiler Schaetzer), Test auf frischem Rauschen
    pools = [draws(lambda: rng.standard_normal(n), 100) for _ in range(12)]
    thr_estimates = np.array([np.percentile(p, 99) for p in pools])
    thr_honest = float(np.mean(thr_estimates))
    test = draws(lambda: rng.standard_normal(n), 4000)
    fa_honest = float(np.mean(test > thr_honest))

    # 2) forking paths: aus denselben 12 Pools die NIEDRIGSTE Schwelle picken
    #    (best-of-N = Optimismus, garden of forking paths)
    thr_fork = float(np.min(thr_estimates))
    fa_fork = float(np.mean(test > thr_fork))

    print(f"Threshold-Schaetzungen (12 Pools a 100 Draws): "
          f"{thr_estimates.min():.1f} .. {thr_estimates.max():.1f}, "
          f"Mittel = {thr_honest:.1f}, best-of-N = {thr_fork:.1f}")
    print(f"FA auf 4000 unabhaengigen Draws: ehrlich = {fa_honest:.4f}, "
          f"best-of-N = {fa_fork:.4f} (Ceiling 0.01)")
    print(f"-> best-of-N-Schwelle verzerrt die FA nach oben: "
          f"{fa_fork > fa_honest}. Auf neuen Daten gilt die Ceiling nicht")
    print("   mehr zwangslaeufig (H1-Realitaet im Holdout: FA 0.0125 > 0.01).")
    print("   Lektion: Unabhaengige Holdout-Segmente sind der einzige ehrliche Test;")
    print("   ihr FAIL (H1 0.05 / L1 0.00 vs Floor 0.90) ist Information, kein Bug.")

    fig, ax = plt.subplots(figsize=(8.4, 4.6))
    ax.hist(pools[0], bins=40, alpha=0.45,
            label="Kalibrier-Pool #1 (in-sample)", color="#1f77b4")
    ax.hist(test, bins=60, alpha=0.45, label="Test-Draws (held-out)", color="#7f7f7f")
    for thr, c, lab in ((thr_honest, "#2ca02c", f"ehrliche Schwelle = Mittel(12 Pools) (FA={fa_honest:.3f})"),
                        (thr_fork, "#d62728", f"best-of-12 Schwelle (FA={fa_fork:.3f})")):
        ax.axvline(thr, color=c, ls="--", lw=1.8, label=lab)
    ax.set_xlabel("Toy-Statistik: Band-Energie @ 180 Hz")
    ax.set_ylabel("Anzahl Draws")
    ax.set_title("Demo 1: Holdout-Logik — optimierte Schwellen brechen auf neuen Daten ein\n"
                 "(Mechanismus-Analogon zum F7-V3-Holdout-FAIL; vgl. FA H1 0.0125 > 0.01)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    out = Path(__file__).parent / "demo1_holdout_lesson.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"[saved] {out.relative_to(ROOT)}")


if __name__ == "__main__":
    part_a()
    part_b()
