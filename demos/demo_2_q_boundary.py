#!/usr/bin/env python3
"""Demo 2 — Die Q-Grenze: warum die FAIL-Minima an Q=pi*f*tau=2 sitzen.

Liest die ECHTE efficiency_table des F7-V3-Holdout-Runs und zeigt:
  * jede Gitterzelle (f, tau, snr=12) als Punkt eff vs Q = pi*f*tau/1000,
  * die Floor-Linie 0.90 nur im gueltigen Scope (Q>=2, gefroren vor dem Lauf),
  * dass die Minima H1 0.05 / L1 0.00 in Zellen mit Q knapp >= 2 liegen
    (tau=4 ms @ 180/250 Hz: Q = 2.26 / 3.14),
  * dass Zellen mit tau>=8 ms bei snr>=12 fast alle bestehen
    (Ausnahme L1: f120/tau8ms/snr12 = 0.55 — auch dokumentiert).

Physik: Ein Modal-Statistik kann nicht verpflichtet werden, ein Signal
mit < ~2/pi Zyklen zu finden (Zeit-Bandbreite-Limit) — deshalb tragen
Q<2-Zellen (schraffiert) keinen Floor. Aber: der Holdout-FAIL kommt
NICHT nur von Grenzzellen — siehe Output-Tabelle.

Laufzeit < 10 s. Output: demos/demo2_q_boundary.png
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
V3 = json.loads((ROOT / "artifacts" /
                 "GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json").read_text())
CELL = re.compile(r"f(\d+)_tau(\d+)ms_snr(\d+)")
FLOOR = 0.90


def table(det, snr=12):
    out = []
    for k, v in V3["gate_details"][det]["efficiency_table"].items():
        m = CELL.match(k)
        f, tau_ms, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if s == snr:
            out.append((f, tau_ms, math.pi * f * tau_ms / 1000.0, v))
    return sorted(out, key=lambda r: r[2])


def main():
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.6), sharey=True)
    print("=" * 78)
    print("F7-V3 holdout: efficiency vs Q = pi*f*tau bei snr=12 (echte Tabelle)")
    print("=" * 78)
    for ax, det in zip(axes, ("H1", "L1")):
        rows = table(det)
        print(f"\n{det}:")
        print(f"  {'f [Hz]':>7s} {'tau':>6s} {'Q':>6s} {'eff':>6s}  Scope")
        for f, tau, q, eff in rows:
            scope = "Q>=2 (Floor verpflichtend)" if q >= 2 else "Q<2  (kein Floor)"
            flag = "   <<< FAIL-Treiber" if q >= 2 and eff < FLOOR else ""
            print(f"  {f:7d} {tau:4d}ms {q:6.2f} {eff:6.2f}  {scope}{flag}")
        qs = np.array([r[2] for r in rows])
        effs = np.array([r[3] for r in rows])
        ax.axvspan(0, 2, color="0.85", hatch="//", alpha=0.6)
        for (f, tau, q, eff) in rows:
            bad = q >= 2 and eff < FLOOR
            ax.scatter(q, eff, s=140 if bad else 70,
                       color="#d62728" if bad else "#2ca02c",
                       edgecolor="k", lw=0.6, zorder=3)
            ax.annotate(f"{f}Hz/{tau}ms", (q, eff), textcoords="offset points",
                        xytext=(5, 5), fontsize=7.5)
        ax.axhline(FLOOR, color="#d62728", ls="--", lw=1.6)
        ax.axvline(2.0, color="k", ls=":", lw=1.4)
        ax.text(2.05, 0.04, "Q = 2 (Scope-Grenze)", rotation=90, fontsize=8)
        ax.text(5.6, FLOOR + 0.02, f"Floor {FLOOR:.2f} (nur Q>=2)", color="#d62728",
                fontsize=8.5, ha="right")
        ax.set_xlabel("Q = pi*f*tau")
        ax.set_ylim(-0.06, 1.08)
        ax.set_title(f"{det} — F7-V3 holdout, snr=12\n"
                     "(Daten: efficiency_table in GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json)",
                     fontsize=9.5)
    axes[0].set_ylabel("efficiency @ snr 12")
    fig.suptitle("Demo 2: die FAIL-Minima sitzen an der Q-Grenze — und L1 f180/tau8ms "
                 "(Q=4.52, eff 0.80) zeigt: der FAIL ist kein Grenz-Artefakt", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    out = Path(__file__).parent / "demo2_q_boundary.png"
    fig.savefig(out)
    plt.close(fig)
    print(f"\n[saved] {out.relative_to(ROOT)}")
    print("\nFazit: rot = Q>=2-Scope-Zellen unter Floor 0.90 — das ist der ehrliche")
    print("F7-V3-HOLDOUT-FAIL (Min H1 0.05 / L1 0.00), KEIN Artefakt der Q-Regel:")
    print("L1 f180/tau8ms (Q=4.52) liegt mit eff 0.80 mitten im Scope unter Floor.")


if __name__ == "__main__":
    main()
