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

**Update, post vision-prompt tuning (Task 5):** these images HAVE now been vision-tested
against the live model through `agent.tools.vision_tool.analyze_defect_image`, using the
final `agent/prompts/vision.md` (tightened to list what is NOT a defect — flux residue,
dust, glare, normal tolerance — and to distinguish "unsure of type" from "no anomaly at
all"). **`defect_03.jpg` is the golden-path solder-bridge image** — the demo's "solder
bridge on lot L2611" narrative should use this file, not `defect_01.jpg` as earlier drafts
of this note assumed. `no_defect_01.jpg` is the clean-board image. Neither read is
perfectly stable across repeated calls; see the table and the stability note below before
leaning on either in a live demo.

| File | Dataset / class / split | Original filename | Licence | Source URL | Why chosen | Gemini reads it as (final prompt) |
|---|---|---|---|---|---|---|
| `defect_01.jpg` | VisA `pcb3`, test, anomalous | `004.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Clearest anomaly in the sampled set: the IR LED and IR receiver are both dislodged and rotated out of their footprints — an unambiguous, high-confidence "something is wrong here" image for the vision smoke test. | `none` (a false negative — the dislodged-component anomaly described above is real but the model is not reliably catching it; see Open items) |
| `defect_02.jpg` | VisA `pcb3`, test, anomalous | `002.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Bent header pin crossing diagonally over the board — a lead/placement defect distinct in shape from `defect_01`, useful for checking the model doesn't just key on one visual pattern. | `none` (also a false negative, same caveat as `defect_01.jpg`) |
| `defect_03.jpg` | VisA `pcb3`, test, anomalous | `003.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | A second bent-lead variant (LED leg bent flat across the board) — another distinct defect silhouette for coverage. | **`solder_bridge`, critical** in 2 of 3 live calls under the final prompt (1 call read `none`). This is the **golden-path defect image** and the source of `agent/tests/fixtures/vision_solder_bridge.json`. The model's own description names a header pin solder bridge, not the LED-leg bend this image was originally picked for — a real, if differently-located, bridge-shaped anomaly. |
| `defect_04.jpg` | VisA `pcb3`, test, anomalous | `000.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Header pins splayed outward at an abnormal angle — milder, more subtle defect than the other three, useful as a harder case. | `misalignment` (major/minor), consistent across both post-tightening test rounds — the one defect image that reads stably as "a defect" under the final prompt. |
| `no_defect_01.jpg` | VisA `pcb3`, test, normal | `0011.JPG` | CC BY 4.0 | https://huggingface.co/datasets/BrachioLab/visa/resolve/main/data/pcb3.test-00000-of-00001.parquet | Same board family, no anomaly — clean-board counterpart for the `insufficient_evidence` / "no defect visible" edge case. | **`none`** in 3 of 4 live calls under the final prompt (1 call read `misalignment`). This is the **clean-board image** and the source of `agent/tests/fixtures/vision_clean_board.json`. Mostly reliable, not perfectly stable. |

Full test methodology, every call's raw output, and the two prompt revisions that got
here are recorded in
the build report.

## Open items for the team

- **`defect_01.jpg` and `defect_02.jpg` are false negatives under the final prompt.**
  Both carry genuine, documented anomalies (a dislodged/rotated component pair; a bent
  header pin) but both read as `none` consistently across two independent prompt
  revisions. Tightening the "what counts as a defect" language fixed the clean-board false
  positives but did not make the model reliably see these two real anomalies; this looks
  like a limitation of the model on unfamiliar board photography rather than a prompt
  wording problem at this point. Do not keep tuning the prompt against this without a plan
  — a real photographed defect (per PRD §10.4's fallback) may be the more reliable path if
  these two specific anomaly types are needed for the demo.
- **Neither the golden-path nor the clean-board read is 100% stable.** `defect_03.jpg`
  returned `solder_bridge` in 2 of 3 calls (one `none`); `no_defect_01.jpg` returned `none`
  in 3 of 4 calls (one `misalignment`). Budget for this if either image is used live in a
  demo rather than only through the recorded fixtures — a re-run immediately before a live
  demo is worth doing.
- If the team prefers different anomaly classes (e.g. a more dramatic
  short/bridge-like defect), the other VisA PCB subsets (`pcb1`, `pcb2`,
  `pcb4`) are available from the same Hugging Face mirror at the same
  per-split granularity (28-250 MB each) without needing the full 8-9 GB
  archive.

*Synthetic/third-party demo images — not Sree Electronics (fictional) hardware. Used here under VisA's CC BY 4.0 licence for defect-detection vision testing only.*
