# Control Plan — SMT Reflow Line, ECU-PCB-7

Plant: Sree Electronics (fictional), Chennai

Control plan for the surface-mount placement and reflow process, covering incoming paste through first-article release.

## Item 1

| Field | Value |
|---|---|
| Characteristic | Incoming solder paste inspection |
| Specification | Certificate of analysis within paste manufacturer limits; viscosity within supplier spec at receipt |
| Method | Visual certificate review plus a viscometer spot check |
| Frequency | Every paste lot at receipt |
| Reaction plan | quarantine the paste lot, notify supplier quality, do not release to the line until conforming |

Characteristic: Incoming solder paste inspection. Specification: Certificate of analysis within paste manufacturer limits; viscosity within supplier spec at receipt. Method: Visual certificate review plus a viscometer spot check. Frequency: Every paste lot at receipt. Reaction plan: quarantine the paste lot, notify supplier quality, do not release to the line until conforming.

## Item 2

| Field | Value |
|---|---|
| Characteristic | SPI post-print paste inspection |
| Specification | 80-120% of stencil aperture volume per standard SMT guidance |
| Method | Automated SPI 100% measurement, 3D laser |
| Frequency | Every board, inline |
| Reaction plan | stop the printer, clean or replace the stencil, re-run first article before resuming |

Characteristic: SPI post-print paste inspection. Specification: 80-120% of stencil aperture volume per standard SMT guidance. Method: Automated SPI 100% measurement, 3D laser. Frequency: Every board, inline. Reaction plan: stop the printer, clean or replace the stencil, re-run first article before resuming.

## Item 3

| Field | Value |
|---|---|
| Characteristic | Placement accuracy verification |
| Specification | Component placement within ±0.05 mm of nominal for fine-pitch components |
| Method | Placement machine vision check against the golden placement file |
| Frequency | Every board, inline, with a gauge check at setup |
| Reaction plan | halt the placement head, recalibrate the vision system, inspect boards placed since the last good calibration |

Characteristic: Placement accuracy verification. Specification: Component placement within ±0.05 mm of nominal for fine-pitch components. Method: Placement machine vision check against the golden placement file. Frequency: Every board, inline, with a gauge check at setup. Reaction plan: halt the placement head, recalibrate the vision system, inspect boards placed since the last good calibration.

## Item 4

| Field | Value |
|---|---|
| Characteristic | Paste storage and working-life control |
| Specification | Solder paste age from removal from refrigeration to last print within the manufacturer's working-life window |
| Method | Paste cart timer tag and FIFO issue log |
| Frequency | Every paste pot, continuous |
| Reaction plan | discard or return paste exceeding its working life, hold boards printed with over-age paste for SPI/AOI review |

Characteristic: Paste storage and working-life control. Specification: Solder paste age from removal from refrigeration to last print within the manufacturer's working-life window. Method: Paste cart timer tag and FIFO issue log. Frequency: Every paste pot, continuous. Reaction plan: discard or return paste exceeding its working life, hold boards printed with over-age paste for SPI/AOI review.

## Item 5

| Field | Value |
|---|---|
| Characteristic | Nitrogen purity monitoring |
| Specification | Residual oxygen below 500 ppm in the reflow zones |
| Method | Inline oxygen analyzer reading the nitrogen supply regulator |
| Frequency | Continuous, logged every shift |
| Reaction plan | hold lots reflowed while out of specification, inspect and adjust the nitrogen regulator, re-verify purity before resuming |

Characteristic: Nitrogen purity monitoring. Specification: Residual oxygen below 500 ppm in the reflow zones. Method: Inline oxygen analyzer reading the nitrogen supply regulator. Frequency: Continuous, logged every shift. Reaction plan: hold lots reflowed while out of specification, inspect and adjust the nitrogen regulator, re-verify purity before resuming.

## Item 6

| Field | Value |
|---|---|
| Characteristic | Reflow profile verification after maintenance |
| Specification | Peak temperature 235-250 °C, TAL 45-90 s, measured with a profiling board |
| Method | Profiler run on a golden board |
| Frequency | After any oven maintenance and once per shift |
| Reaction plan | hold lots produced since the last verified profile, re-profile the oven, re-qualify before release |

Characteristic: Reflow profile verification after maintenance. Specification: Peak temperature 235-250 °C, TAL 45-90 s, measured with a profiling board. Method: Profiler run on a golden board. Frequency: After any oven maintenance and once per shift. Reaction plan: hold lots produced since the last verified profile, re-profile the oven, re-qualify before release.

## Item 7

| Field | Value |
|---|---|
| Characteristic | AOI post-reflow inspection |
| Specification | Zero bridges, opens, tombstones or missing components per the released inspection criteria |
| Method | Automated optical inspection, 100% coverage |
| Frequency | Every board, inline |
| Reaction plan | pull the board for manual verification and rework; if the defect rate trends upward, hold the lot and notify quality engineering |

Characteristic: AOI post-reflow inspection. Specification: Zero bridges, opens, tombstones or missing components per the released inspection criteria. Method: Automated optical inspection, 100% coverage. Frequency: Every board, inline. Reaction plan: pull the board for manual verification and rework; if the defect rate trends upward, hold the lot and notify quality engineering.

## Item 8

| Field | Value |
|---|---|
| Characteristic | ICT / functional electrical test |
| Specification | Pass per the ECU-PCB-7 test specification |
| Method | In-circuit test fixture plus functional test bench |
| Frequency | 100% of boards |
| Reaction plan | quarantine the failing board, root-cause the failure mode, hold the lot if the failure rate exceeds the alert limit |

Characteristic: ICT / functional electrical test. Specification: Pass per the ECU-PCB-7 test specification. Method: In-circuit test fixture plus functional test bench. Frequency: 100% of boards. Reaction plan: quarantine the failing board, root-cause the failure mode, hold the lot if the failure rate exceeds the alert limit.

## Item 9

| Field | Value |
|---|---|
| Characteristic | Stencil cleaning (under-stencil wipe) |
| Specification | No visible paste residue buildup in the apertures |
| Method | Automatic under-stencil wipe cycle, vacuum plus dry wipe |
| Frequency | Every N print cycles per the stencil program |
| Reaction plan | stop printing, manually clean the stencil, re-run SPI on the first boards after cleaning |

Characteristic: Stencil cleaning (under-stencil wipe). Specification: No visible paste residue buildup in the apertures. Method: Automatic under-stencil wipe cycle, vacuum plus dry wipe. Frequency: Every N print cycles per the stencil program. Reaction plan: stop printing, manually clean the stencil, re-run SPI on the first boards after cleaning.

## Item 10

| Field | Value |
|---|---|
| Characteristic | Squeegee pressure and speed setting |
| Specification | Pressure and speed within the qualified process window for the stencil program |
| Method | Printer setpoint verification against the approved process sheet |
| Frequency | At setup and once per shift |
| Reaction plan | correct the setpoint, re-run SPI on the next boards, hold prior boards for paste volume review if the setpoint had drifted |

Characteristic: Squeegee pressure and speed setting. Specification: Pressure and speed within the qualified process window for the stencil program. Method: Printer setpoint verification against the approved process sheet. Frequency: At setup and once per shift. Reaction plan: correct the setpoint, re-run SPI on the next boards, hold prior boards for paste volume review if the setpoint had drifted.

## Item 11

| Field | Value |
|---|---|
| Characteristic | Conveyor speed verification |
| Specification | Within the qualified process window for the released reflow profile |
| Method | Conveyor speed readout check against the profile recipe |
| Frequency | At setup and once per shift |
| Reaction plan | correct the conveyor speed, re-run a profile check, hold boards reflowed at the incorrect speed |

Characteristic: Conveyor speed verification. Specification: Within the qualified process window for the released reflow profile. Method: Conveyor speed readout check against the profile recipe. Frequency: At setup and once per shift. Reaction plan: correct the conveyor speed, re-run a profile check, hold boards reflowed at the incorrect speed.

## Item 12

| Field | Value |
|---|---|
| Characteristic | First-article inspection after setup change |
| Specification | Conforms to drawing, AOI and ICT criteria before the lot is released |
| Method | First-article visual, dimensional and electrical check |
| Frequency | First board after every setup change |
| Reaction plan | hold the lot until the first article passes, re-run setup verification if it fails |

Characteristic: First-article inspection after setup change. Specification: Conforms to drawing, AOI and ICT criteria before the lot is released. Method: First-article visual, dimensional and electrical check. Frequency: First board after every setup change. Reaction plan: hold the lot until the first article passes, re-run setup verification if it fails.

*Synthetic document for demo purposes.*
