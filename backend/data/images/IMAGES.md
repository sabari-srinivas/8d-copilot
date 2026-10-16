# Demo images — provenance

All images below are from the **VisA (Visual Anomaly) dataset**, Zou et al.,
*"SPot-the-Difference Self-Supervised Pre-training for Anomaly Detection and
Segmentation"*, ECCV 2022 — licensed **CC BY 4.0** (confirmed on the AWS Open
Data registry listing, https://registry.opendata.aws/visa/, and on the
original repo, https://github.com/amazon-science/spot-diff). None of these
boards are Sree Electronics (fictional) hardware; they illustrate the vision
pipeline only, not the planted ECU-PCB-7 scenario.

**How these were fetched:** the full VisA archive is a single ~8-9 GB tar on
S3 with no server-side partial extraction, so a full download was out of
scope for this task's timebox. Instead, images were pulled from the
`BrachioLab/visa` Hugging Face mirror
(https://huggingface.co/datasets/BrachioLab/visa), which re-publishes the
same CC BY 4.0 VisA data as per-class Parquet files. Only the `pcb3.test`
split (28 MB, 201 images: 101 normal + 100 anomalous) was downloaded —
no other class or split was fetched.

**Subset used:** VisA class `pcb3` (test split) — a small IR obstacle-avoidance
sensor PCB. Source file:
`https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet`

**Important — none of these are a solder bridge.** The anomalies in `pcb3`
are a mix of bent/displaced leads and dislodged components, not solder
bridging specifically. Per PRD §10.4, when no VisA image reliably reads as a
solder bridge, the fallback is a team photo of a real board — that has not
been taken yet. These four images are usable for exercising the general
defect-detection path (and the "defect present, type uncertain" case) and
for the no-defect edge case, but they should **not** be the board the demo
narrates as "the solder bridge on lot L2611." See Open items below.

| File | Dataset / class / split | Original filename | Licence | Source URL | Why chosen |
|---|---|---|---|---|---|
| `defect_01.jpg` | VisA `pcb3`, test, anomalous | `004.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Clearest anomaly in the sampled set: the IR LED and IR receiver are both dislodged and rotated out of their footprints — an unambiguous, high-confidence "something is wrong here" image for the vision smoke test. |
| `defect_02.jpg` | VisA `pcb3`, test, anomalous | `002.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Bent header pin crossing diagonally over the board — a lead/placement defect distinct in shape from `defect_01`, useful for checking the model doesn't just key on one visual pattern. |
| `defect_03.jpg` | VisA `pcb3`, test, anomalous | `003.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | A second bent-lead variant (LED leg bent flat across the board) — another distinct defect silhouette for coverage. |
| `defect_04.jpg` | VisA `pcb3`, test, anomalous | `000.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Header pins splayed outward at an abnormal angle — milder, more subtle defect than the other three, useful as a harder case. |
| `no_defect_01.jpg` | VisA `pcb3`, test, normal | `0011.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Same board family, no anomaly — clean-board counterpart for the `insufficient_evidence` / "no defect visible" edge case. |

## Gemini reads it as

**Not done.** Brief Step 6 (pre-testing each candidate against the §9.4
vision prompt in Google AI Studio, two runs each, recording the answer) is a
manual browser task and was explicitly out of scope for this agent run per
the task instructions. **None of these five images has been vision-verified.**
Before they are wired into any vision code path, someone needs to:
1. Paste the §9.4 vision prompt into Google AI Studio with each image.
2. Run each twice and record the returned defect type / severity / box.
3. Keep only images whose answer is stable across both runs; add a
   "Gemini reads it as" column here with the result.
4. Decide whether `misalignment` / `missing_component` reads (the honest
   expected answer for these four) are acceptable for the demo, or whether a
   real photographed solder bridge is needed instead — see below.

## Open items for the team

- **No confirmed solder-bridge image.** Per PRD §10.4's stated fallback: if
  Gemini pre-testing confirms these VisA images don't read as a solder
  bridge, photograph a real board on the bench and substitute it, noting the
  substitution here and in the README.
- If the team prefers different anomaly classes (e.g. a more dramatic
  short/bridge-like defect), the other VisA PCB subsets (`pcb1`, `pcb2`,
  `pcb4`) are available from the same Hugging Face mirror at the same
  per-split granularity (28-250 MB each) without needing the full 8-9 GB
  archive.

*Synthetic/third-party demo images — not Sree Electronics (fictional) hardware. Used here under VisA's CC BY 4.0 licence for defect-detection vision testing only.*
