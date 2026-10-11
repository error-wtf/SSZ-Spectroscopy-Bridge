#!/usr/bin/env python3
"""Demo 3 — Echte GW150914-Daten: Ringdown-Extraktion (nur Charakterisierung).

Laedt die GWOSC-HDF5-Segmente von H1 und L1 (Event GPS 1126259462) und
demonstriert die Extraktions-Stufe des SSZ-Workflows auf REAL-Daten:
Band-Pass, Peak-Suche, Least-Squares-Ringdown-Fit (exp*cos), Q-Berechnung.

Bewusst OHNE Signifikanz-Claim: der F7-Gate-HOLDOUT-FAIL
(H1 0.05 / L1 0.00 vs Floor 0.90) haelt den Extractor fuer Modal-Claims
BLOCKED. Dieses Demo zeigt nur die Roh-Extraktion — keine p-Werte,
keine LOD-Schaetzung, kein 'Detected!'.

Laufzeit < 60 s. Output: demos/demo3_gw150914_extraction.png und
demos/demo3_gw150914_walkthrough.gif
"""
from __future__ import annotations

import json
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation, PillowWriter
from scipy.signal import butter, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "gwosc" / "GW150914-v4"
FS_RAW = 16384.0

_V3 = json.loads((ROOT / "artifacts" /
                  "GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json").read_text())
GPS = float(_V3.get("gps_event", 1126259462.44))

FILES = {
    "H1": RAW / "H-H1_LOSC_16_V2-1126257414-4096.hdf5",
    "L1": RAW / "L-L1_LOSC_16_V2-1126257414-4096.hdf5",
}


def whiten(x, fs):
    """Spektrales Whitening: PSD per Welch, Division im Frequenzraum."""
    from scipy.signal import welch
    freqs, psd = welch(x, fs=fs, nperseg=min(len(x), 4096))
    X = np.fft.rfft(x)
    fbins = np.fft.rfftfreq(len(x), 1.0 / fs)
    gain = np.sqrt(np.interp(fbins, freqs, psd))
    gain[gain <= 0] = gain[gain > 0].min()
    w = np.fft.irfft(X / gain, n=len(x))
    return w / w.std()


def load_strain(det, t_start, t_end):
    """Laden inkl. Whitening (PSD aus dem Segment selbst) + Bandpass."""
    with h5py.File(FILES[det], "r") as f:
        gps0 = float(f["meta"]["GPSstart"][()])
        strain = f["strain"]["Strain"][()]
        try:
            fs = float(f["strain"]["Strain"].attrs["Xspacing"]) ** -1
        except (KeyError, TypeError):
            fs = FS_RAW
    t = gps0 + np.arange(len(strain)) / fs
    sel = (t >= t_start) & (t < t_end)
    t, x = t[sel], strain[sel].astype(np.float64)
    x = x - x.mean()
    x = whiten(x, fs)
    sos = butter(4, [30.0 / (fs / 2), 800.0 / (fs / 2)],
                 btype="band", output="sos")
    return t, sosfiltfilt(sos, x)


def spectrum(x_seg):
    w = x_seg * np.hanning(len(x_seg))
    spec = np.abs(np.fft.rfft(w, n=8192))
    fr = np.fft.rfftfreq(8192, d=1.0 / FS_RAW)
    return fr, spec


def fit_ringdown(t_rel, x, f0):
    """LSQ-Fit x ~ A e^{-t/tau} cos(2 pi f0 t + phi); tau auf 1..80 ms Gitter."""
    best = None
    for tau in np.linspace(0.001, 0.080, 158):
        w = np.exp(-t_rel / tau)
        M = np.column_stack([w * np.cos(2 * np.pi * f0 * t_rel),
                             w * np.sin(2 * np.pi * f0 * t_rel)])
        coef, *_ = np.linalg.lstsq(M, x, rcond=None)
        rss = float(np.sum((x - M @ coef) ** 2))
        if best is None or rss < best[0]:
            best = (rss, tau, coef)
    rss, tau, coef = best
    amp = float(np.hypot(coef[0], coef[1]))
    q = np.pi * f0 * tau
    return tau, amp, q


def main():
    print("=" * 74)
    print("Demo 3 — GW150914 (real data): Ringdown-Extraktion ohne Claim")
    print(f"GPS event (aus Artefakt): {GPS:.2f} | Fs = {FS_RAW:.0f} Hz")
    print("=" * 74)
    t0, t1 = GPS - 0.10, GPS + 0.12
    results, traces = {}, {}
    for det in ("H1", "L1"):
        t, x = load_strain(det, GPS - 0.40, GPS + 0.40)
        traces[det] = (t - GPS, x)
        # Peak-Suche NUR im Ereignisfenster [-0.05, +0.05] (whitened)
        near = (np.abs(t - GPS) <= 0.05)
        ipk = int(np.argmax(np.abs(x * near)))
        wsel = (t >= t[ipk]) & (t <= t[ipk] + 0.032)
        fr, spec = spectrum(x[wsel])
        band = (fr >= 100) & (fr <= 400)
        f0 = float(fr[band][np.argmax(spec[band])])
        tau, amp, q = fit_ringdown(t[wsel] - t[ipk], x[wsel], f0)
        results[det] = dict(f0=f0, tau=tau, amp=amp, q=q)
        print(f"{det}: f0 = {f0:6.1f} Hz | tau = {tau*1000:5.1f} ms | "
              f"Q = {q:5.2f} | amp = {amp:9.5f} | Q>=2: {q >= 2}")
    print("\nNur Charakterisierung. Modal-Claims sind BLOCKED bis ein Gate-Typ "
          "den Holdout-Floor 0.90 besteht ( aktuell H1 0.05 / L1 0.00).")

    # ---------------- static figure ----------------
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 6.6))
    for r, det in enumerate(("H1", "L1")):
        tt, xx = traces[det]
        axes[r, 0].plot(tt, xx, lw=0.5,
                        color="#1f77b4" if det == "H1" else "#d62728")
        axes[r, 0].axvspan(-0.10, 0.12, color="orange", alpha=0.15,
                           label="Fit-Fenster [-0.10, +0.12] s")
        axes[r, 0].set_xlim(-0.40, 0.40)
        axes[r, 0].set_title(f"{det} — band-passed strain (30–800 Hz)")
        axes[r, 0].set_xlabel("t − GPS event [s]")
        axes[r, 0].legend(fontsize=8)
        fr, spec = spectrum(xx[(tt >= -0.10) & (tt < 0.12)])
        f0 = results[det]["f0"]
        axes[r, 1].plot(fr, spec, lw=0.6,
                        color="#1f77b4" if det == "H1" else "#d62728")
        axes[r, 1].set_xlim(30, 400)
        axes[r, 1].axvline(f0, color="k", ls=":", lw=1.3,
                           label=f"Peak f0 ≈ {f0:.0f} Hz")
        axes[r, 1].set_title(f"{det} — Spektrum im Fit-Fenster | "
                             f"tau ≈ {results[det]['tau']*1000:.0f} ms | "
                             f"Q ≈ {results[det]['q']:.1f}")
        axes[r, 1].set_xlabel("Frequenz [Hz]")
        axes[r, 1].legend(fontsize=8)
    fig.suptitle(
        "Demo 3: GW150914-Ringdown-Extraktion auf echten Daten — "
        "Charakterisierung ohne Signifikanz-Claim\n"
        "F7-Gate-HOLDOUT-FAIL (H1 0.05 / L1 0.00 vs Floor 0.90) hält den "
        "Extractor für Modal-Claims BLOCKED", fontsize=10.5)
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(Path(__file__).parent / "demo3_gw150914_extraction.png")
    plt.close(fig)

    # ---------------- animation: sliding-window walkthrough (H1) ----------
    tt, xx = traces["H1"]
    win_starts = np.arange(-0.30, 0.26, 0.04)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2))

    def draw(k):
        ax1.clear(); ax2.clear()
        ws = float(win_starts[k])
        wsel = (tt >= ws) & (tt < ws + 0.032)
        fr, spec = spectrum(xx[wsel])
        ax1.plot(tt, xx, lw=0.4, color="#1f77b4")
        ax1.axvspan(ws, ws + 0.032, color="orange", alpha=0.35)
        ax1.set_xlim(-0.40, 0.40)
        ax1.set_title(f"H1 strain — 32-ms-Fenster @ {ws*1000:+.0f} ms "
                      f"({k+1}/{len(win_starts)})")
        ax1.set_xlabel("t − GPS event [s]")
        ax2.plot(fr, spec, lw=0.7, color="#1f77b4")
        ax2.set_xlim(30, 400)
        ax2.set_yscale("log")
        ax2.set_title("Fenster-Spektrum (32 ms, Hann)")
        ax2.set_xlabel("Frequenz [Hz]")

    ani = FuncAnimation(fig, draw, frames=len(win_starts), interval=650)
    ani.save(Path(__file__).parent / "demo3_gw150914_walkthrough.gif",
             writer=PillowWriter(fps=1.5))
    plt.close(fig)
    print("[saved] demos/demo3_gw150914_extraction.png")
    print("[saved] demos/demo3_gw150914_walkthrough.gif")


if __name__ == "__main__":
    main()
