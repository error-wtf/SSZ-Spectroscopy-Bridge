#!/usr/bin/env python3
"""make_figures_v1.py — Publication figures + animations for the F7-V3 holdout FAIL.

Every number is read from frozen JSON artifacts — NOTHING is hardcoded:

  artifacts/GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json   (V3 holdout run, 2026-10-09)
  artifacts/GWOSC_V2_F7_GATE_RESULT_FULL_MATRIX_FAIL.json  (r9 full-matrix run)
  artifacts/GWOSC_V2_F7_GATE_SPECIFICATION_FROZEN.json     (frozen pre-run specification)

The scientific story these figures must tell HONESTLY:
  * The r9 full-matrix result did NOT reproduce on held-out off-source
    segments: min efficiency H1 0.05 / L1 0.00 vs floor 0.90 (snr>=12,
    Q>=2 scope) -> F7_GATE_FAIL -> extractor BLOCKED for modal claims.
  * The failing minima sit in the Q-boundary cells (tau=4 ms @ 180/250 Hz,
    Q = pi*f*tau just >= 2). Cells with tau>=8 ms at snr>=12 mostly pass.
  * H1 false-alarm rate drifts above the frozen ceiling (0.0125 > 0.01).

Usage:
    OMP_NUM_THREADS=2 /home/error/physics/venv/bin/python figures/make_figures_v1.py

Outputs (figures/):
    fig1_holdout_fail.png        fig2_eff_heatmap_snr12.png
    fig3_recovery.png            fig4_eff_vs_snr.gif
    fig5_tau_sweep_snr12.gif     figures_manifest.json
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

V3 = json.loads((ART / "GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json").read_text())
FM = json.loads((ART / "GWOSC_V2_F7_GATE_RESULT_FULL_MATRIX_FAIL.json").read_text())
SPEC = json.loads((ART / "GWOSC_V2_F7_GATE_SPECIFICATION_FROZEN.json").read_text())

RUNS = [("V3 holdout", V3), ("r9 full-matrix", FM)]
DETS = ["H1", "L1"]
CELL_RE = re.compile(r"f(\d+)_tau(\d+)ms_snr(\d+)")
FLOOR_HIGH = V3["gate_details"]["H1"]["floors"]["high_snr"]   # 0.90
FLOOR_LOW = V3["gate_details"]["H1"]["floors"]["low_snr"]     # 0.70
FA_CEIL = V3["gate_details"]["H1"]["floors"]["fa"]            # 0.01

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "figure.dpi": 110, "savefig.dpi": 150, "axes.grid": True,
    "grid.alpha": 0.3, "axes.axisbelow": True,
})
C = {"V3 holdout": "#1f77b4", "r9 full-matrix": "#7f7f7f",
     "H1": "#1f77b4", "L1": "#d62728", "floor": "#d62728", "pass": "#2ca02c"}


def cells(run):
    """efficiency_table -> {(f, tau_ms, snr): eff} for one run."""
    out = {}
    for det in DETS:
        tab = run["gate_details"][det]["efficiency_table"]
        d = {}
        for k, v in tab.items():
            m = CELL_RE.match(k)
            d[(int(m.group(1)), int(m.group(2)), int(m.group(3)))] = float(v)
        out[det] = d
    return out


CELLS = {name: cells(run) for name, run in RUNS}
FREQS = sorted({k[0] for k in CELLS["V3 holdout"]["H1"]})
TAUS = sorted({k[1] for k in CELLS["V3 holdout"]["H1"]})
SNRS = sorted({k[2] for k in CELLS["V3 holdout"]["H1"]})


def q_of(f_hz, tau_ms):
    return math.pi * f_hz * (tau_ms / 1000.0)


def in_scope(f_hz, tau_ms):
    """r9 floor scope: Q = pi*f*tau >= 2 (frozen pre-run)."""
    return q_of(f_hz, tau_ms) >= 2.0


def head():
    return (f"F7-V3 holdout FAIL | floor(snr>=12, Q>=2) = {FLOOR_HIGH:.2f} | "
            f"verdict: {V3['verdict'][:60]}")


# ---------------------------------------------------------------- fig 1 ----
def fig1():
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 4.2))
    labels, colors = [], []
    for name, _ in RUNS:
        for det in DETS:
            labels.append(f"{det}\n{name}")
            colors.append(C[det] if "V3" in name else "#7f7f7f")

    panels = [
        ("eff min, snr>=12, Q>=2 scope", "eff_min_snr>=12", FLOOR_HIGH,
         "detection-efficiency floor"),
        ("eff min, snr>=8, Q>=2 scope", "eff_min_snr>=8", FLOOR_LOW,
         "low-SNR floor"),
        ("false-alarm rate", "false_alarm_rate", FA_CEIL, "FA ceiling"),
    ]
    for ax, (title, key, floor, flabel) in zip(axes, panels):
        vals = [run["gate_details"][det][key] for _, run in RUNS for det in DETS]
        bars = ax.bar(range(len(vals)), vals, color=colors, edgecolor="k",
                      linewidth=0.6)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.4g}"
                    if key == "false_alarm_rate" else f"{v:.2f}",
                    ha="center", fontsize=9)
        ax.axhline(floor, color=C["floor"], ls="--", lw=1.6)
        ax.text(0.99, floor, f" {flabel} = {floor}", color=C["floor"],
                fontsize=8.5, ha="right", va="bottom", transform=ax.get_yaxis_transform())
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(title)
        ax.set_ylim(0, 1.05)
        ax.set_ylabel("efficiency" if "eff" in key else "FA rate")
        for b, v in zip(bars, vals):
            ok = v >= floor if "eff" in key else v <= floor
            b.set_edgecolor(C["pass"] if ok else C["floor"])
            b.set_linewidth(2.0 if not ok else 0.6)
    fig.suptitle("F7 gate: held-out revalidation FAIL — r9 does not reproduce "
                 f"(data: *V3_HOLDOUT_RESULT_FAIL.json, *FULL_MATRIX_FAIL.json)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(OUT / "fig1_holdout_fail.png")
    plt.close(fig)


# ---------------------------------------------------------------- fig 2 ----
def fig2():
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 7.2),
                             sharex=True, sharey=True)
    for r, det in enumerate(DETS):
        for c, (name, run) in enumerate(RUNS):
            ax = axes[r, c]
            M = np.full((len(TAUS), len(FREQS)), np.nan)
            for i, tau in enumerate(TAUS):
                for j, f in enumerate(FREQS):
                    M[i, j] = CELLS[name][det].get((f, tau, 12), np.nan)
            im = ax.imshow(M, vmin=0, vmax=1, cmap="RdYlGn", aspect="auto",
                           origin="lower")
            for i, tau in enumerate(TAUS):
                for j, f in enumerate(FREQS):
                    v = M[i, j]
                    if not np.isnan(v):
                        ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                                fontsize=9, fontweight="bold"
                                if in_scope(f, tau) else "normal")
                    if not in_scope(f, tau):
                        ax.add_patch(Rectangle((j - .5, i - .5), 1, 1,
                                               fill=False, hatch="//",
                                               edgecolor="0.35", lw=0))
                    elif v < FLOOR_HIGH:
                        ax.add_patch(Rectangle((j - .5, i - .5), 1, 1,
                                               fill=False, edgecolor=C["floor"],
                                               lw=2.2))
            ax.set_xticks(range(len(FREQS)), [str(f) for f in FREQS])
            ax.set_yticks(range(len(TAUS)), [f"{t} ms" for t in TAUS])
            ax.set_title(f"{det} — {name} (snr=12)", fontsize=10)
            if r == 1:
                ax.set_xlabel("injection frequency [Hz]")
            if c == 0:
                ax.set_ylabel("decay time tau")
            ax.grid(False)
    qnote = ("Q = pi*f*tau: hatched = Q<2 (outside frozen floor scope); "
             "red box = Q>=2 scope and eff < 0.90")
    fig.suptitle("Detection efficiency at snr=12 — minima sit at the Q>=2 "
                 f"boundary (tau=4 ms @ 180/250 Hz)\n{qnote}", fontsize=10.5)
    fig.colorbar(im, ax=axes, shrink=0.75, label="efficiency @ snr 12")
    fig.savefig(OUT / "fig2_eff_heatmap_snr12.png")
    plt.close(fig)


# ---------------------------------------------------------------- fig 3 ----
def fig3():
    fig, ax = plt.subplots(figsize=(9.0, 4.4))
    width = 0.19
    xs = np.arange(3)
    for k, (name, run) in enumerate(RUNS):
        for kd, det in enumerate(DETS):
            rec = run["gate_details"][det]["pencil_recovery_among_detections"]
            vals = [rec["f_within_tol"], rec["tau_within_tol"], rec["f_and_tau"]]
            off = (k * 2 + kd) * width - 1.5 * width
            bars = ax.bar(xs + off, vals, width,
                          label=f"{det} — {name}",
                          color=C[det] if "V3" in name else "#7f7f7f",
                          alpha=1.0 if "V3" in name else 0.55,
                          edgecolor="k", lw=0.5)
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}",
                        ha="center", fontsize=7.5)
    nd = {f"{d}|{n}": run["gate_details"][d]["pencil_recovery_among_detections"]["n_detected"]
          for n, run in RUNS for d in DETS}
    note = "n_detected: " + ", ".join(f"{k.replace('|',' ')}={v}" for k, v in nd.items())
    ax.set_xticks(xs, ["f within tol (10 Hz)", "tau within tol (50% rel)",
                       "f AND tau"])
    ax.set_ylabel("fraction among power-detections")
    ax.set_ylim(0, 1.1)
    ax.legend(fontsize=8, ncol=2, loc="upper left")
    ax.set_title("Matrix-pencil characterization among detections — "
                 "recovery degrades on holdout segments\n"
                 f"{note}\n(data: pencil_recovery_among_detections in both FAIL JSONs)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "fig3_recovery.png")
    plt.close(fig)


# ---------------------------------------------------------------- fig 4 ----
def fig4():
    """Animated: efficiency vs SNR, one frame per (f, tau) cell."""
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    cell_list = [(f, t) for t in TAUS for f in FREQS]

    def draw(frame):
        ax.clear()
        f, tau = cell_list[frame]
        q = q_of(f, tau)
        for name, run in RUNS:
            for det in DETS:
                ys = [CELLS[name][det][(f, tau, s)] for s in SNRS]
                ax.plot(SNRS, ys, "o-", color=C[det],
                        alpha=1.0 if "V3" in name else 0.5, lw=2 if "V3" in name else 1.2,
                        ms=5, label=f"{det} {name}")
        ax.axhspan(0, FLOOR_HIGH, color=C["floor"], alpha=0.06)
        ax.axhline(FLOOR_HIGH, color=C["floor"], ls="--", lw=1.5)
        ax.text(30, FLOOR_HIGH + 0.02, f"floor snr>=12 = {FLOOR_HIGH:.2f}",
                color=C["floor"], ha="right", fontsize=8.5)
        ax.axhline(FLOOR_LOW, color="#ff7f0e", ls=":", lw=1.3)
        ax.text(5, FLOOR_LOW + 0.02, f"floor snr=8 = {FLOOR_LOW:.2f}",
                color="#ff7f0e", fontsize=8.5)
        scope = "IN Q>=2 floor scope" if in_scope(f, tau) else "Q<2 — measured, no floor"
        ax.set_title(f"f = {f} Hz, tau = {tau} ms  (Q = pi*f*tau = {q:.2f}) — {scope}\n"
                     f"frame {frame + 1}/{len(cell_list)} | {head()}", fontsize=9.5)
        ax.set_xlabel("injection SNR")
        ax.set_ylabel("detection efficiency (20 draws/cell)")
        ax.set_ylim(-0.05, 1.1)
        ax.set_xticks(SNRS)
        ax.legend(fontsize=8, loc="lower right")

    ani = FuncAnimation(fig, draw, frames=len(cell_list), interval=1100)
    ani.save(OUT / "fig4_eff_vs_snr.gif", writer=PillowWriter(fps=1))
    plt.close(fig)


# ---------------------------------------------------------------- fig 5 ----
def fig5():
    """Animated tau-sweep at snr=12: where exactly the gate breaks."""
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    frames = [(run_name, tau) for run_name, _ in RUNS for tau in TAUS]

    def draw(frame):
        ax.clear()
        run_name, tau = frames[frame]
        run = dict(RUNS)[run_name]
        width = 0.35
        for kd, det in enumerate(DETS):
            vals = [CELLS[run_name][det][(f, tau, 12)] for f in FREQS]
            xs = np.arange(len(FREQS)) + (kd - 0.5) * width
            bars = ax.bar(xs, vals, width, color=C[det], edgecolor="k", lw=0.5,
                          label=det)
            for b, v, f in zip(bars, vals, FREQS):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}",
                        ha="center", fontsize=8.5)
                if in_scope(f, tau) and v < FLOOR_HIGH:
                    ax.add_patch(Rectangle((b.get_x(), 0), b.get_width(), 1.0,
                                           fill=False, edgecolor=C["floor"],
                                           lw=2.0, ls="-"))
        ax.axhline(FLOOR_HIGH, color=C["floor"], ls="--", lw=1.6)
        ax.text(3.45, FLOOR_HIGH + 0.02, f"floor = {FLOOR_HIGH:.2f}",
                color=C["floor"], ha="right", fontsize=9)
        qs = ", ".join(f"Q({f})={q_of(f, tau):.2f}" for f in FREQS)
        ax.set_xticks(range(len(FREQS)), [f"{f} Hz" for f in FREQS])
        ax.set_ylim(0, 1.08)
        ax.set_ylabel("efficiency @ snr 12")
        ax.legend(fontsize=9, loc="upper left")
        ax.set_title(f"{run_name} — tau = {tau} ms sweep at snr = 12\n"
                     f"{qs} | red frame = Q>=2 scope & below floor | "
                     f"frame {frame + 1}/{len(frames)}", fontsize=9.5)

    ani = FuncAnimation(fig, draw, frames=len(frames), interval=1500)
    ani.save(OUT / "fig5_tau_sweep_snr12.gif", writer=PillowWriter(fps=1))
    plt.close(fig)


# ------------------------------------------------------------- manifest ----
def manifest():
    info = {
        "generated_by": "figures/make_figures_v1.py",
        "sources": {
            "v3_holdout": "artifacts/GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json",
            "r9_full_matrix": "artifacts/GWOSC_V2_F7_GATE_RESULT_FULL_MATRIX_FAIL.json",
            "specification": "artifacts/GWOSC_V2_F7_GATE_SPECIFICATION_FROZEN.json",
        },
        "key_numbers": {
            "floor_high": FLOOR_HIGH, "floor_low": FLOOR_LOW, "fa_ceiling": FA_CEIL,
            "v3_eff_min_snr12": {d: V3["gate_details"][d]["eff_min_snr>=12"] for d in DETS},
            "v3_eff_min_snr8": {d: V3["gate_details"][d]["eff_min_snr>=8"] for d in DETS},
            "v3_fa": {d: V3["gate_details"][d]["false_alarm_rate"] for d in DETS},
            "fm_eff_min_snr12": {d: FM["gate_details"][d]["eff_min_snr>=12"] for d in DETS},
            "fm_eff_min_snr8": {d: FM["gate_details"][d]["eff_min_snr>=8"] for d in DETS},
            "fm_fa": {d: FM["gate_details"][d]["false_alarm_rate"] for d in DETS},
            "v3_gate_pass": V3["gate_pass"], "fm_gate_pass": FM["gate_pass"],
            "v3_verdict": V3["verdict"], "fm_verdict": FM["verdict"],
        },
        "grid": {"freqs_hz": FREQS, "taus_ms": TAUS, "snrs": SNRS,
                 "draws_per_cell": 20},
    }
    (OUT / "figures_manifest.json").write_text(json.dumps(info, indent=1) + "\n")


def main():
    print("grid:", FREQS, TAUS, SNRS)
    print("floors:", FLOOR_HIGH, FLOOR_LOW, FA_CEIL)
    print("V3 mins:", {d: V3["gate_details"][d]["eff_min_snr>=12"] for d in DETS},
          "FA:", {d: V3["gate_details"][d]["false_alarm_rate"] for d in DETS})
    print("FM mins:", {d: FM["gate_details"][d]["eff_min_snr>=12"] for d in DETS},
          "FA:", {d: FM["gate_details"][d]["false_alarm_rate"] for d in DETS})
    for fn in (fig1, fig2, fig3, fig4, fig5, manifest):
        print("->", fn.__name__, flush=True)
        fn()
    for p in sorted(OUT.iterdir()):
        print(f"  {p.name:32s} {p.stat().st_size:>10,d} B")
    print("OK: figures written to", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
