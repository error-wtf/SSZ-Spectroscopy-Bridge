# Full Pipeline Report — 2026-10-11

Repo: `/home/error/physics/SSZ-Spectroscopy-Bridge` (branch `main`, head `41ec242` = `origin/main`, in sync).
Environment: `/home/error/physics/venv/bin/python`, `OMP_NUM_THREADS=2`, keine Netzwerkzugriffe.
Alle Zahlen in diesem Report stammen aus eingefrorenen JSON-Artefakten bzw. Live-Läufen (Logs unten); nichts ist hardcodiert.

---

## 1. Kernbefund (unchanged, honest)

**F7-V3 HOLDOUT RESULT: FAIL on both detectors — H1 0.05, L1 0.00 vs Floor 0.90.**
Das r9-Ergebnis (full-matrix, tau>=8ms-Scope: H1 0.85 / L1 0.55, commit `7c3036c`) reproduziert
NICHT auf zurückgehaltenen Off-Source-Segmenten. Der Extraktor bleibt **BLOCKED** für Modal-Claims.
Zusätzlich verletzt H1 die False-Alarm-Ceiling: FA 0.0125 > 0.01 (eingefroren).

Quellen:
- `artifacts/GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json` (created 2026-10-09T16:40:31Z, wall 2302.5 s)
- `artifacts/GWOSC_V2_F7_GATE_RESULT_FULL_MATRIX_FAIL.json` (created 2026-10-09T12:40:18Z, wall 582.3 s)
- `artifacts/GWOSC_V2_F7_GATE_SPECIFICATION_FROZEN.json` (Floors 0.90/0.70, FA-Ceiling 0.01, tau>=8ms-Scope, neue Off-Source-Segmente 96–224 s, Seed 20261009)
- Runner: `tools/run_gwosc_v2_injection_gate_v3_holdout.py`

### 1.1 Zahlen im Detail (aus den Artefakten gelesen)

| Metrik | r9 full-matrix | F7-V3 holdout | Bewertung |
|---|---|---|---|
| min eff, H1, snr>=12 & Q>=2 | 0.00 (Zelle `f180_tau4ms_snr20`) | **0.05** (Zelle `f250_tau4ms_snr12`) | beide < 0.90 → FAIL |
| min eff, L1, snr>=12 & Q>=2 | 0.05 (Zelle `f180_tau4ms_snr20`) | **0.00** (Zelle `f250_tau4ms_snr12`) | beide < 0.90 → FAIL |
| false-alarm H1 | 0.0000 | **0.0125** | > Ceiling 0.01 → Verletzung |
| false-alarm L1 | 0.0100 | 0.0100 | an der Ceiling |
| gate_pass | false | false | — |
| verdict | F7_GATE_FAIL | F7_GATE_FAIL | — |

FAIL-Treiber (V3, snr=12): Q-Grenzzellen `f180_tau4ms` (Q=2.26: H1 0.35 / L1 0.10) und
`f250_tau4ms` (Q=3.14: H1 0.05 / L1 0.00); außerdem `L1 f180_tau8ms` (Q=4.52, eff 0.80) als
Nicht-Grenzzellen-FAIL mitten im Scope. Zellen mit tau>=15 ms erreichen 1.00; `f80_tau8ms` = 1.00.
Vollständige Tabellen: `gate_details.{H1,L1}.efficiency_table` in beiden Ergebnis-JSONs.

### 1.2 Was „BLOCKED" konkret bedeutet

Keine Modal-Claims („Mode X detected bei f mit Q") aus dem aktuellen Extraktor auf realen Daten,
bis ein Gate-Typ den Holdout-Floor 0.90 besteht. Charakterisierung (f0/tau/Q ohne Signifikanz) ist
zulässig und wird in `demos/demo_3_gw150914_extraction.py` demonstriert.

---

## 2. Ausgeführte Pipeline (Live-Läufe, 2026-10-11)

Alle Befehle im Repo-Root, venv-Python, `OMP_NUM_THREADS=2`.

### 2.1 Unit-Tests

```
OMP_NUM_THREADS=2 /home/error/physics/venv/bin/python -m pytest tests/ -v --tb=short
```

**Ergebnis: 21 passed, 0 failed, 0 skipped — 81.73 s.**

Testliste (aus `--collect-only`):
- `tests/unit/test_calibration.py` (5): Cheb-Matrizen, Companion-Linearisierung Dirichlet-Box exakt, RW-Potential closed form, Tortoise-Monotonie, SSZ-Kanal fail-closed
- `tests/unit/test_leaver.py` (9): 6× Berti-Tabellen (gravitational l=2 n=0..3, scalar l=0 n=0..1, Toleranz <= 4e-15), Fundamentalmode aus grobem Seed, Units dokumentiert, unbekannte Familie abgelehnt
- `tests/unit/test_shooting_factored.py` (3): Pöschl-Teller-Root aus grobem Seed, Mismatch scharf (nicht flach), Solver-Label
- `tests/unit/test_ssz_axial_symbolic.py` (4): RW-Limes exakt, Deformationskanal ≠ 0, Potentialstruktur, Production-Entry fail-closed

### 2.2 Registry-Guard negative controls

```
OMP_NUM_THREADS=2 /home/error/physics/venv/bin/python tools/test_registry_guard_controls.py
```

**Ergebnis: exit 0 — `GUARD NEGATIVE CONTROLS: PASS`.**
- NC1 fill-while-PENDING: rc=1, REFUSED (korrekt)
- NC2 seal-while-PENDING: rc=1, REFUSED (korrekt)
- NC3 tamper (Status→TAMPERED): check meldet Abweichung; Restore + final check: `status=PENDING, sealable=false, open_gates=[B8, F.4, B6, Jost+ECS]`, rc=0

Hinweis: Der Test überschreibt während des Laufs `tools/registry_guard.py` und
`artifacts/SSZ_PREDICTION_REGISTRY_V1.json` (Registry-Neu-Init mit neuem `created_utc`,
Guard-Zyklus-Stempel entfernt) und restauriert nur teilweise. Arbeitsdateien danach per
`git restore artifacts/SSZ_PREDICTION_REGISTRY_V1.json tools/registry_guard.py` zurückgesetzt
(Design-Restore der Test-Rückstände, kein History-Eingriff); finaler `registry_guard.py check`
lief `status=PENDING`, rc=0. Log: `/root/.hermes/cache/scratch/demo-logs/registry_guard.log`.

### 2.3 Figures

```
OMP_NUM_THREADS=2 timeout 500 /home/error/physics/venv/bin/python figures/make_figures_v1.py
```

**Ergebnis: exit 0.** Erzeugt (alle Zahlen aus den drei Artefakt-JSONs gelesen,
Manifest `figures/figures_manifest.json`):
- `figures/fig1_holdout_fail.png` — r9 vs F7-V3 Minima gegen Floor 0.90 + FA gegen Ceiling
- `figures/fig2_eff_heatmap_snr12.png` — Efficiency-Heatmaps 4×4 (beide Runs, beide Detektoren)
- `figures/fig3_recovery.png` — Pencil-Recovery (f/tau/Q) unter Detektionen
- `figures/fig4_eff_vs_snr.gif` — 16 Frames, 1140×780: Efficiency vs SNR je Zelle
- `figures/fig5_tau_sweep_snr12.gif` — 8 Frames: tau-Sweep bei snr=12, beide Runs

### 2.4 Demos (je exit 0, < 2 min)

| Demo | Befehl | Kern-Output |
|---|---|---|
| 1 — Holdout-Logik | `python demos/demo_1_holdout_logic.py` | Teil A: Gate-Minima aus Artefakt-Tabellen nachgerechnet (r9 H1 0.00/L1 0.05; V3 H1 0.05/L1 0.00; beide < 0.90). Teil B (synthetisch): 12 Kalibrier-Pools à 100 Draws, Schwellen 63.4–84.7, ehrlich (Mittel 71.9) → FA 0.0123 vs best-of-N (63.4) → FA 0.0393 bei Ceiling 0.01 → In-Sample-Optimismus bricht auf neuen Daten auf. |
| 2 — Q-Grenze | `python demos/demo_2_q_boundary.py` | Vollständige Q-Tabelle beider Detektoren; FAIL-Treiber an Q-Grenze (Q=2.26/3.14) UND `L1 f180/tau8ms` Q=4.52 eff 0.80 mitten im Scope → FAIL ist kein Grenz-Artefakt. |
| 3 — GW150914-Extraktion | `python demos/demo_3_gw150914_extraction.py` | Real data (LOSC 16 kHz V2): Whitening + Bandpass 30–800 Hz, Peak im Fenster ±0.05 s, LSQ-Ringdown-Fit: H1 f0=248.0 Hz, tau=8.5 ms, Q=6.66; L1 f0=200.0 Hz, tau=4.5 ms, Q=2.84. NUR Charakterisierung, kein Claim (BLOCKED). |

Logs: `/root/.hermes/cache/scratch/demo-logs/demo_{1,2,3}_*.log`.

---

## 3. SHA-256 (Artefakte + neue Dateien, Stand nach den Läufen)

```
e27f4b37172131da77855f2d6e39b4b2c8972d70d95e651532a6b680c2ded543  artifacts/GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json
eb94d0679a69c245373407382cb7db4748eb2430d46ac8625562a4d0880d0e09  artifacts/GWOSC_V2_F7_GATE_RESULT_FULL_MATRIX_FAIL.json
dc53dfa4510e5195702b2eada1a5e76137f843c1872910f10297fc4e83bf6ad3  artifacts/GWOSC_V2_F7_GATE_SPECIFICATION_FROZEN.json
bc5903d686235fde2380e3489a8e6f38a405469f6bde9482ee9f111e1fb6ee9e  tools/run_gwosc_v2_injection_gate_v3_holdout.py
240a97e779eaa270be6e6e09deb88a2906571156ec820a53f70da0087cca07c1  figures/fig1_holdout_fail.png
bad7f98bd4fdb3ce5e76ce8b1884871b487e44b0943b68cd4e6b0516b0e11e0c  figures/fig2_eff_heatmap_snr12.png
381be61328da184172d7bde50dad36425ee476d4c1c9f35b80b32ece59769118  figures/fig3_recovery.png
2b5a2f6b050f213cc9a6bf8cd121f4cf74adf9252abc6ad3ab790ce31a530771  figures/fig4_eff_vs_snr.gif
c93a655612a48c5b08ebc650212415a0583b1b96c75ec8759c9bf7a6f451361b  figures/fig5_tau_sweep_snr12.gif
856ccf9800d599a0dface4b7c34a57e6f6b157aac40fcf285f349fd17141ed35  figures/figures_manifest.json
cc1d6e277215c5c6446ce8952beb9fcc7b89bde7ff957bbc04ae38368a2803f4  figures/make_figures_v1.py
fafbe5b421baa4fd00d19b784fe1561c4fdb5a5b9a22e217a2901ecaec93beaa  demos/demo_1_holdout_logic.py
cd6180602ee69cc6dc9be7e283d8ef95cf1b4edd2e786f0ca040dc7e7d03b41a  demos/demo_2_q_boundary.py
eec5fb1aee8e08c19dd290a24cd4759dc56116250b123f8530fd24a7cb15e765  demos/demo_3_gw150914_extraction.py
cbbb9d0b0d49c141ad67f452355da1549fd5b11f193a65ebdf3fc0f5bc3e0c00  demos/demo1_holdout_lesson.png
d4c9eea3c48e2e82294bfd555c7e98d790a5a7de8442407173d146e8dbf8648b  demos/demo2_q_boundary.png
ddbf4e99efb50cac0161b73ad61aa5046c69472af58c06fe7608a2379cc5d714  demos/demo3_gw150914_extraction.png
88d182b6e2d86b77b29b78ebaa97b277c2ceea52ddeb36b5c5b52140b5db2d02  demos/demo3_gw150914_walkthrough.gif
```

(Rohdaten `data/raw/gwosc/GW150914-v4/*_LOSC_16_V2-1126257414-4096.hdf5` sind unverändert;
deren Hashes stehen im eingefrorenen G181/182/183-Artefakt.)

---

## 4. Offene Punkte

1. **Extraktor-Defizit (Kern)**: Efficiency-Kollaps an kurzen taus (4 ms) und FA-Drift bei H1.
   Vermutung (aus Demo-1-Mechanik): Schwellen-Kalibration ist auf In-Sample-/Kalibrier-Pools
   optimistisch; eine strictly-pre-registered Threshold-Regel pro Zelle ohne Post-hoc-Auswahl
   ist der nächste deklarierte Angriffspfad. NICHT gelöst — steht nicht zur Disposition des FAILs.
2. Demo 3 extrahiert bewusst ohne p-Werte/LOD — Signifikanz-Infrastruktur ist Teil des
   blockierten Gates.
3. GIF-Verifikation dieser Umgebung war programmatisch (PIL Frame-Zählung), nicht visuell
   (Vision-Tool Fehler 400/code 1210).
4. `tools/test_registry_guard_controls.py` hinterlässt Arbeitsbaum-Rückstände (siehe 2.2) —
   ggf. in einem Folge-Commit den Test selbst restore-fest machen (hier nur dokumentiert,
   Test-Code nicht geändert).

---

## 5. Review-Leitfaden (für Peer-Reviewer)

**Kürzester Weg, den Kernbefund zu prüfen (ca. 10 min):**
1. `jq '.gate_pass, .verdict' artifacts/GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json` → `false`.
2. `jq '.gate_details.H1.efficiency_table | to_entries | map(select(.value.snr==12)) | min_by(.value.efficiency)' artifacts/GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json` → H1-Minimum 0.05.
3. `jq '.gate_details.L1.false_alarm_rate' artifacts/GWOSC_V2_F7_GATE_V3_HOLDOUT_RESULT_FAIL.json` → 0.0125 (H1) vs Ceiling 0.01.
4. Floors/Ceiling sind VOR dem Lauf gefroren: `artifacts/GWOSC_V2_F7_GATE_SPECIFICATION_FROZEN.json`
   (Feld `f7_gate_v3_holdout`), Commit `8abc48c`. Prüfen, dass der Spec-Zeitpunkt < Ergebnis-Zeitpunkt.
5. Full re-run (falls gewünscht, ~40 min): `OMP_NUM_THREADS=2 python tools/run_gwosc_v2_injection_gate_v3_holdout.py`
   — Seed 20261009 in der Spec macht den Lauf deterministisch; Abweichungen > 1/20 (1 Draw)
   pro Zelle wären ein Reopen-Grund.

**Was den r9-Nicht-Reproduktions-Befund widerlegen könnte (Fälschungsrisiken):**
- **Seed-/Segment-Bias im Holdout**: Wenn die 96–224-s-Off-Source-Segmente untypisch rau sind
  (z. B. Terrestrik in genau diesem Fenster), wäre der V3-FAIL überschätzt. Gegencheck: FA-Raten
  der Nullzellen in V3 vs r9 auf identischen Segmenten ( artefakt-intern prüfbar).
- **Threshold-Kalibration im Runner**: Falls der Runner Schwellen aus denselben Segmenten zieht,
  auf denen er tested (Leaks), wäre der FAIL sogar noch konservativ — dann wäre r9-PASS der
  eigentliche Kalibrationsfehler. Code-Review-Punkt: `tools/run_gwosc_v2_injection_gate_v3_holdout.py`
  (Segment-Auswahl vor Threshold-Fit prüfen).
- **Statistische Fluktuation**: 20 Draws/Zelle → Binomial-Standardfehler ~0.07 bei p≈0.5. Aber
  0.00/0.05 liegt >10σ unter 0.90 — Fluktuation ist KEINE Erklärung.
- **Was NICHT widerlegt**: die gemessenen Zahlen selbst (JSONs hash-gebunden, git-History intakt).

**Was den r9-„PASS im tau>=8ms-Scope" (H1 0.85/L1 0.55) gerettet hätte**: nichts im Nachhinein —
0.85/0.55 lagen auch in r9 bereits unter 0.90 (deshalb commit `7c3036c`: „declassified pending
revalidation"). Der V3-Holdout hat diese Deklassifikation voll bestätigt.

**Gates-Status-Governance**: Offene Gates (Registry `PENDING`, open: B8, F.4, B6, Jost+ECS) sperren
Seals — negative controls verifiziert (2.2). Ein Modal-Claim bräuchte: Gate-Pass + Registry-Fill
nach Katalog-Freeze + Seal — aktuell alles korrekt verweigert.

---

## 6. Abschluss-Zustand

- `git status -sb`: `## main...origin/main`; untracked: `demos/`, `figures/`; modified: `README.md`, `docs/FULL_PIPELINE_REPORT_2026-10-11.md` (neu).
- Kein Commit, kein Push (Regel).
- Backup-Punkt: `/root/deleted-backups/20261011-repo-refresh/` (vorheriger Stand).

### Addendum (nach README-Finalisierung, 2026-10-11)

`README.md` wurde nach Erstellung dieses Reports komplett neu geschrieben
(24 KB, vorher 8 KB): Headline = F7-V3 HOLDOUT FAIL (H1 0.05 / L1 0.00
vs 0.90) prominent am Anfang; alle 9 erzeugten Bilder (5 figures/ +
4 demos/) als relative Markdown-Embeds mit ausführlichen Captions und
Datenquellen; r9↔V3-Scope-Reconciliation; Peer-Review-Sektion mit
Binomial-Gegenargumenten (P(≤1/20 | p=0.90) = 1.81e-18) und
Fälschungsrisiken. Verifikation: alle 9 Bildpfade existieren vom
Repo-Root (programmatischer Check: alle `![…](…)`-Relative-Pfade in
README.md gegen das Dateisystem; reproduzierbar mit
`python -c "import re,os; [print(p, os.path.exists(p)) for p in set(re.findall(r'\\!\\[[^]]*\\]\\(([^)]+)\\)', open('README.md').read()))]"`).
Ehrlichkeits-Korrektur
gegenüber älteren Formulierungen: Freeze-Nachweis der V3-Spec über
in-File-Timestamps + v2_prereg_sha256-Kette, NICHT über Git-Commit-Daten
(diese sind gebündelt/retroaktiv: 8abc48c 18:40 nach V3-Lauf 16:40 UTC —
interner Spec-Timestamp 2026-10-08T22:49:14Z liegt korrekt davor).
