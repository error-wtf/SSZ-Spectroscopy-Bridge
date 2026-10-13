#!/usr/bin/env python3
"""Animated GIF demos of the SSZ-Spectroscopy-Bridge core results.

Produces three dark-themed GIFs in demos/output/:

  1. rw_ringdown.gif          Regge-Wheeler potential V(r*) on the tortoise
                              coordinate + the certified fundamental QNM
                              (l=2, n=0) rendered as a decaying ringdown
                              oscillation exp(i omega t) sampled at a fixed
                              observer radius. omega is read from the
                              measured campaign artifact (real physics, no
                              hardcoded constants).
  2. gate_board.gif           The honest gate status board G150..G190,
                              animated row by row: green = PASS,
                              red = NOT PASS, yellow = BLOCKED.
  3. leaver_cf_convergence.gif  Convergence of the Leaver continued-fraction
                              solver (ssz_spectroscopy.continued_fraction)
                              toward the certified mode frequency as the
                              CF truncation order n_max increases, with the
                              published Berti-table reference.

All numbers are taken from artifacts/*.json or recomputed live with the
package's own solver. Run with the repo venv:

    /home/error/physics/venv/bin/python demos/animate_core_results.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.animation import FuncAnimation, PillowWriter  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "artifacts"
OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(REPO / "src"))

# ----------------------------------------------------------------_theme ----
plt.style.use("dark_background")
ACCENT = "#4fc3f7"      # cyan
GOOD = "#2e7d32"        # green (PASS)
GOOD_TXT = "#66bb6a"
BAD = "#c62828"         # red (NOT PASS)
BAD_TXT = "#ef5350"
WARN = "#f9a825"        # yellow/amber (BLOCKED)
WARN_TXT = "#ffca28"
GRID = "#37474f"
TXT = "#eceff1"


def _save(fig, anim: FuncAnimation, name: str, fps: int) -> Path:
    path = OUT / name
    anim.save(str(path), writer=PillowWriter(fps=fps))
    plt.close(fig)
    return path


# ----------------------------------------------------------------- GIF 1 ---
def gif_rw_ringdown() -> Path:
    """RW potential V(r*) + decaying QNM ringdown exp(i omega t)."""
    camp = json.loads((ART / "GATE_CAMPAIGN_RW_CONTROL_V1.json").read_text())
    meas = camp["measurements"][0]
    M_omega = complex(*meas["M_omega"])          # measured 0.37365 - 0.08895 i
    err = meas["err_vs_reference"]
    pub = complex(*camp["reference"]["M_omega"])  # published 0.37367 - 0.08896 i

    # Tortoise coordinate x = r* (units M=1):  x = r + 2 ln(r/2 - 1)
    def r_of_x(x):
        # monotonic inversion via Newton on f(r) = r + 2 ln(r/2 - 1) - x
        r = np.empty_like(x)
        inside = x <= 2.0
        r[inside] = 2.0 + np.exp(x[inside] / 2.0)
        r[~inside] = x[~inside] + 2.0 * np.log(x[~inside] / 2.0)
        for _ in range(60):
            f = r + 2.0 * np.log(r / 2.0 - 1.0) - x
            fp = 1.0 + 2.0 / (r - 2.0)
            step = f / fp
            r = r - step
            if np.max(np.abs(step)) < 1e-14:
                break
        return r

    ell = 2
    x = np.linspace(-8.0, 60.0, 2500)
    r = r_of_x(x)
    V = (1.0 - 2.0 / r) * (ell * (ell + 1) / r**2 + 2.0 / r**3)
    Vpeak = float(V.max())
    xpeak = float(x[V.argmax()])

    # Ringdown at fixed observer: psi(t) = exp(i omega t), omega = M_omega/M
    t = np.linspace(0.0, 80.0, 900)
    psi = np.exp(1j * M_omega.real * t) * np.exp(M_omega.imag * t)
    env = np.exp(M_omega.imag * t)

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(11.0, 4.6), facecolor="#101418"
    )
    for ax in (ax1, ax2):
        ax.set_facecolor("#101418")
        ax.grid(True, color=GRID, lw=0.5, alpha=0.7)
        ax.tick_params(colors=TXT)
        for sp in ax.spines.values():
            sp.set_color(GRID)

    ax1.plot(x, V, color=ACCENT, lw=2.0)
    ax1.set_xlabel("tortoise coordinate  $r_* / M$", color=TXT)
    ax1.set_ylabel("$V_{RW}(r_*)$", color=TXT)
    ax1.set_title(
        "Regge-Wheeler potential ($\\ell=2$, $M=1$)\n"
        f"barrier peak $V_\\max$ = {Vpeak:.4f} at $r_*$ = {xpeak:.2f} M",
        color=TXT, fontsize=10,
    )
    ax1.set_ylim(-0.02, 0.17)
    wavelet, = ax1.plot([], [], color=WARN_TXT, lw=1.2, alpha=0.9)
    ax1.axvline(xpeak, color=GRID, ls=":", lw=1)

    ax2.set_xlim(0, t[-1])
    ax2.set_ylim(-1.15, 1.15)
    ax2.set_xlabel("time  $t / M$", color=TXT)
    ax2.set_ylabel("$\\psi(t)$", color=TXT)
    ax2.set_title(
        "fundamental QNM ringdown  $\\psi \\propto e^{\\,i\\omega t}$\n"
        f"$M\\omega$ = {M_omega.real:.5f} {M_omega.imag:+.5f}i"
        f"   (err vs published {err:.1e})",
        color=TXT, fontsize=10,
    )
    reline, = ax2.plot([], [], color=ACCENT, lw=1.6, label="Re $\\psi$")
    imline, = ax2.plot([], [], color="#ce93d8", lw=1.2, alpha=0.85,
                       label="Im $\\psi$")
    ax2.plot(t, env, color=BAD_TXT, ls="--", lw=1.0, alpha=0.8)
    ax2.plot(t, -env, color=BAD_TXT, ls="--", lw=1.0, alpha=0.8)
    ax2.legend(loc="upper right", fontsize=8, facecolor="#101418",
               edgecolor=GRID, labelcolor=TXT)

    n_frames = 72
    tt = np.linspace(0.0, t[-1], n_frames)

    def update(frame):
        t0 = tt[frame]
        # wave packet draining off the barrier, amplitude tracks the envelope
        amp = float(np.exp(M_omega.imag * t0))
        sig = 3.5 + 4.0 * (1.0 - amp)
        packet = amp * 0.14 * np.exp(-0.5 * ((x - (xpeak + 1.5 + 0.02 * t0)) / sig) ** 2)
        wavelet.set_data(x, packet)
        m = t <= t0
        reline.set_data(t[m], psi[m].real)
        imline.set_data(t[m], psi[m].imag)
        return wavelet, reline, imline

    anim = FuncAnimation(fig, update, frames=n_frames, blit=False,
                         interval=90)
    return _save(fig, anim, "rw_ringdown.gif", fps=10)


# ----------------------------------------------------------------- GIF 2 ---
def gif_gate_board() -> Path:
    """Honest gate status board G150..G190, animated row by row."""
    verdict = json.loads(
        (ART / "G190_EMPIRICAL_SPECTROSCOPY_VERDICT_V1.json").read_text())
    status_raw = verdict["gate_status"]          # authoritative recorded dict

    # G190's own status map; G184 recorded in its own artifact, G190 itself
    # is the verdict row. RECORDED = evidence artifact locked, not blocking.
    board = []
    for gid in sorted(status_raw):
        st = status_raw[gid]
        if st == "RECORDED":
            label, color = "RECORDED (evidence locked)", GOOD_TXT
        elif st.startswith("PASS"):
            label, color = "PASS", GOOD
        elif st.startswith("NOT_PASS"):
            label, color = "NOT PASS", BAD
        else:
            label, color = "BLOCKED", WARN
        board.append((gid, label, color))

    try:
        g184 = json.loads(
            (ART / "G184_NICER_REAL_DATA_TIMING_CHAIN_V2.json").read_text())
        n_proc = g184.get("n_obs_processed")
        n_exp = g184.get("n_obs_expected")
        n_stable = len(g184.get("stable_frequencies_hz", []))
        g184_label = (f"RECORDED ({n_proc}/{n_exp} ObsIDs, "
                      f"{n_stable} stable freqs)")
    except Exception:
        g184_label = "RECORDED"
    board.append(("G184", g184_label, GOOD))
    board.append(("G190", verdict["verdict"], WARN))
    board.sort()

    names = {
        "G150": "spectral operator exported",
        "G151": "physical BC closed",
        "G152": "independent eigensolvers agree",
        "G153": "mode convergence",
        "G154": "Schwarzschild/Kerr control",
        "G155": "certified mode catalogue",
        "G160": "time-domain waveform",
        "G161": "frequency/phase-domain equivalence",
        "G170": "synthetic blind recovery",
        "G171": "wrong-model negative control",
        "G180": "detector-response closure",
        "G181": "real public data provenance",
        "G182": "real-event inference",
        "G183": "GR comparison",
        "G184": "NICER real-data timing chain",
        "G190": "empirical spectroscopy verdict",
    }

    n = len(board)
    fig, ax = plt.subplots(figsize=(9.6, 6.4), facecolor="#101418")
    ax.set_facecolor("#101418")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n)
    ax.axis("off")
    ax.set_title(
        "SSZ-Spectroscopy-Bridge — gate status board (honest, as recorded)",
        color=TXT, fontsize=12, pad=12,
    )
    legend_handles = [
        plt.Line2D([], [], marker="s", ls="", color=GOOD, markersize=9,
                   label="PASS / RECORDED"),
        plt.Line2D([], [], marker="s", ls="", color=BAD, markersize=9,
                   label="NOT PASS"),
        plt.Line2D([], [], marker="s", ls="", color=WARN, markersize=9,
                   label="BLOCKED"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=9,
              facecolor="#101418", edgecolor=GRID, labelcolor=TXT)

    cells = []
    for i, (gid, label, color) in enumerate(board):
        y = n - 1 - i
        chip = ax.add_patch(plt.Rectangle((0.03, y + 0.16), 0.094, 0.62,
                                          facecolor=color, edgecolor="none"))
        txt = ax.text(0.15, y + 0.47, gid, va="center", ha="left",
                      color=TXT, fontsize=11, family="monospace",
                      fontweight="bold")
        desc = ax.text(0.28, y + 0.47, names.get(gid, ""), va="center",
                       ha="left", color="#b0bec5", fontsize=9)
        stat = ax.text(0.97, y + 0.47, label, va="center", ha="right",
                       color=color, fontsize=10, fontweight="bold")
        cells.append((chip, txt, desc, stat))

    for _, *texts in cells:
        for obj in texts:
            obj.set_visible(False)
    for chip, *_ in cells:
        chip.set_visible(False)

    footer = ax.text(0.03, -0.35,
                     "status colors: green PASS / red NOT PASS / yellow BLOCKED"
                     " — G182/G183 and G161/G190 stay open honestly",
                     color="#78909c", fontsize=8)

    def update(frame):
        k = min(frame, n)
        for i, (chip, txt, desc, stat) in enumerate(cells):
            vis = i < k
            chip.set_visible(vis)
            txt.set_visible(vis)
            desc.set_visible(vis)
            stat.set_visible(vis)
        footer.set_text(
            f"revealing gate {k}/{n}"
            + ("  — every color is read from G190_EMPIRICAL_SPECTROSCOPY_"
               "VERDICT_V1.json" if k >= n else "")
        )
        return []

    anim = FuncAnimation(fig, update, frames=n + 10, interval=380)
    return _save(fig, anim, "gate_board.gif", fps=3)


# ----------------------------------------------------------------- GIF 3 ---
def gif_leaver_cf() -> Path:
    """Leaver CF convergence toward the certified mode frequency."""
    from ssz_spectroscopy.continued_fraction import rw_leaver_qnm

    g151 = json.loads((ART / "G151_LEAVER_FREQUENCY_DOMAIN_V1.json").read_text())
    ref = g151["mode"][0] if isinstance(g151.get("mode"), list) else None
    if ref is None:
        # fall back: certified catalogue row (l=2, m=0, n=0)
        cat = json.loads(
            (ART / "RW_CONTROL_CERTIFIED_MODE_CATALOGUE_G155_V1.json").read_text())
        ref = complex(*cat["rows"][0]["omega"])
    ref_M = 0.5 * ref  # units c=G=2M=1 -> M*omega

    ladder = [20, 40, 80, 160, 320, 640]
    results = []
    for nm in ladder:
        res = rw_leaver_qnm(complex(0.7473433688, -0.1779246314), ell=2,
                            family="gravitational", n_max=nm)
        results.append((nm, res["omega"], res["misfit"]))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.6),
                                   facecolor="#101418")
    for ax in (ax1, ax2):
        ax.set_facecolor("#101418")
        ax.grid(True, color=GRID, lw=0.5, alpha=0.7)
        ax.tick_params(colors=TXT)
        for sp in ax.spines.values():
            sp.set_color(GRID)

    ax1.set_xlabel("CF truncation order  $n_{\\max}$", color=TXT)
    ax1.set_ylabel("$|\\omega(n_{\\max}) - \\omega_{\\rm ref}|$", color=TXT)
    ax1.set_yscale("log")
    ax1.set_xlim(ladder[0] * 0.8, ladder[-1] * 1.2)
    ax1.set_ylim(1e-13, 1e-5)
    ax1.set_title("Leaver continued fraction — convergence ladder\n"
                  "reference: certified catalogue / Berti tables ($\\leq$ 4e-15)",
                  color=TXT, fontsize=10)

    ax2.set_xlabel("Re $\\,M\\omega$", color=TXT)
    ax2.set_ylabel("Im $\\,M\\omega$", color=TXT)
    pad = 6e-6
    ax2.set_xlim(ref_M.real - 40 * pad, ref_M.real + 40 * pad)
    ax2.set_ylim(ref_M.imag - 40 * pad, ref_M.imag + 40 * pad)
    ax2.set_title("complex plane approach\n"
                  f"$M\\omega \\to$ {ref_M.real:.8f} {ref_M.imag:+.8f}i",
                  color=TXT, fontsize=10)
    ax2.plot([ref_M.real], [ref_M.imag], marker="*", ms=14, color=WARN_TXT,
             ls="", label="certified $\\omega$")
    ax2.legend(loc="lower right", fontsize=8, facecolor="#101418",
               edgecolor=GRID, labelcolor=TXT)

    errline, = ax1.plot([], [], color=ACCENT, lw=1.8, marker="o", ms=5)
    ptline, = ax2.plot([], [], color=ACCENT, lw=1.5, marker="o", ms=6)
    note = ax1.text(0.35, 0.1, "", transform=ax1.transAxes, color=TXT,
                    fontsize=9)

    def update(frame):
        k = frame % (len(ladder) + 4)
        m = min(k, len(ladder))
        nms = ladder[:m]
        errs = [abs(w - ref) for _, w, _ in results[:m]]
        errline.set_data(nms, errs)
        ptline.set_data([0.5 * w.real for _, w, _ in results[:m]],
                        [0.5 * w.imag for _, w, _ in results[:m]])
        if m:
            nm, w, mis = results[m - 1]
            note.set_text(
                f"$n_{{\\max}}$ = {nm}\n"
                f"$M\\omega$ = {0.5 * w.real:.9f} {0.5 * w.imag:+.9f}i\n"
                f"|err| = {abs(w - ref):.2e}   misfit = {mis:.1e}"
            )
        return errline, ptline

    anim = FuncAnimation(fig, update, frames=len(ladder) + 4, interval=900)
    return _save(fig, anim, "leaver_cf_convergence.gif", fps=2)


def main() -> int:
    print("[1/3] RW potential + QNM ringdown ...")
    p1 = gif_rw_ringdown()
    print(f"      -> {p1}  ({p1.stat().st_size / 1024:.0f} KB)")
    print("[2/3] gate status board G150..G190 ...")
    p2 = gif_gate_board()
    print(f"      -> {p2}  ({p2.stat().st_size / 1024:.0f} KB)")
    print("[3/3] Leaver CF convergence (live solver) ...")
    p3 = gif_leaver_cf()
    print(f"      -> {p3}  ({p3.stat().st_size / 1024:.0f} KB)")
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
