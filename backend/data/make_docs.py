"""
make_docs.py — synthetic quality-document corpus for the 8D Copilot RAG store.

ALL DOCUMENTS ARE SYNTHETIC (labelled so in their footer). They stand in for
the plant's PFMEA, control plan and two closed 8D reports. Markdown is used
instead of PDF (PRD §10.5 permits it) so chunking on "## " headings is exact:
a heading's text IS the citation ref, e.g. "## Row 14" -> "[PFMEA row 14]".

Two sections are load-bearing and referenced verbatim elsewhere in the repo:
PFMEA Row 14 (solder bridging / reflow peak temperature above profile limit)
and Control plan Item 6 (reflow profile verification after maintenance).
Their wording must not drift from data/constants.py or from the fixtures
that already cite them.

Run: python -m data.make_docs   (writes data/docs/)
"""
from pathlib import Path

from data.constants import PLANT, PRODUCT, REFLOW_PEAK_LIMIT_C

OUT = Path(__file__).parent / "docs"
OUT.mkdir(parents=True, exist_ok=True)

FOOTER = "\n*Synthetic document for demo purposes.*\n"
PROFILE_LIMIT = int(REFLOW_PEAK_LIMIT_C)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def ap_from_severity(severity: int) -> str:
    """Simplified AIAG-VDA-style action priority, driven by severity alone
    (synthetic document — not a substitute for a real AP lookup table)."""
    if severity >= 8:
        return "High"
    if severity >= 5:
        return "Medium"
    return "Low"


# ---------------------------------------------------------------------------
# PFMEA
# ---------------------------------------------------------------------------

ROW_14 = {
    "process_step": "Reflow soldering",
    "failure_mode": "Solder bridging",
    "effect": "Short circuit between adjacent pins; ECU functional failure at customer ICT",
    "severity": 8,
    "cause": "Reflow peak temperature above profile limit",
    "occurrence": 3,
    "prevention": "Profile verification after any oven maintenance",
    "detection_control": "AOI 100% + profile check per shift",
    "detection": 4,
    "ap": "High",
}

PFMEA_ROWS = [
    dict(process_step="Stencil printing", failure_mode="Insufficient paste deposit",
         effect="Starved solder joint; open circuit or weak fillet found at customer board-level vibration test",
         severity=6, cause="Stencil aperture partially blocked with dried solder paste residue",
         occurrence=4, prevention="Scheduled under-stencil wipe every 10 boards and daily aperture inspection",
         detection_control="SPI 100% paste volume and area measurement", detection=3),
    dict(process_step="Reflow soldering", failure_mode="Tombstoning",
         effect="One end of a chip component lifts off the pad; open circuit at functional test",
         severity=6, cause="Paste age beyond its working window causing uneven wetting force between pad ends",
         occurrence=3, prevention="Paste working-life timer tag on the cart; FIFO issue from refrigeration",
         detection_control="AOI 100% post-reflow inspection", detection=3),
    dict(process_step="Reflow soldering", failure_mode="Voids under BGA/QFN thermal pad",
         effect="Reduced thermal and electrical contact under the package; derating or field failure",
         severity=5, cause="Entrapped flux outgassing during reflow due to low nitrogen purity",
         occurrence=3, prevention="Nitrogen purity monitoring with residual-oxygen alarm",
         detection_control="X-ray sampling of BGA/QFN lots per shift", detection=5),
    dict(process_step="Pick and place", failure_mode="Component misalignment",
         effect="Component placed off-pad; solder bridge or open joint at an adjacent pad",
         severity=5, cause="Placement machine vision calibration drift",
         occurrence=3, prevention="Daily placement accuracy verification against a gauge board",
         detection_control="AOI post-placement (pre-reflow) inspection", detection=3),
    dict(process_step="Reflow soldering", failure_mode="Cold solder joint",
         effect="Dull, grainy joint with poor mechanical strength; intermittent open under vibration",
         severity=6, cause="Reflow peak temperature below profile minimum or insufficient time above liquidus",
         occurrence=2, prevention="Profile verification after any oven maintenance",
         detection_control="AOI 100% plus periodic cross-section audit", detection=4),
    dict(process_step="Reflow soldering", failure_mode="Component shift during reflow",
         effect="Component skewed or tombstoned after reflow; open or short at an adjacent pad",
         severity=5, cause="Conveyor vibration during the reflow cool-down zone",
         occurrence=3, prevention="Conveyor speed and belt tension check per shift",
         detection_control="AOI 100% post-reflow inspection", detection=3),
    dict(process_step="Incoming board handling", failure_mode="Warped board",
         effect="Open joints at board-edge components from coplanarity loss during reflow",
         severity=6, cause="Incoming bare board exceeds the warpage specification",
         occurrence=2, prevention="Incoming board warpage check per the receiving sample plan",
         detection_control="AOI 100% plus warpage gauge spot check", detection=4),
    dict(process_step="Pick and place", failure_mode="Nozzle wear",
         effect="Component drop or tilt during placement; missing or misaligned component",
         severity=5, cause="Pick-and-place nozzle wear beyond vacuum seal tolerance",
         occurrence=3, prevention="Nozzle wear inspection and replacement schedule",
         detection_control="Placement vacuum sensor and AOI post-placement", detection=3),
    dict(process_step="Reflow soldering", failure_mode="Insufficient reflow",
         effect="Paste not fully reflowed; grainy, non-wetted joint with open-circuit risk",
         severity=6, cause="Reflow peak temperature or time above liquidus below profile minimum",
         occurrence=2, prevention="Profile verification after any oven maintenance",
         detection_control="AOI 100% + profile check per shift", detection=4),
    dict(process_step="Reflow soldering", failure_mode="Excess voiding under components",
         effect="Thermal and electrical derating; risk of cracking under thermal cycling",
         severity=5, cause="Paste flux chemistry outgassing combined with a fast preheat ramp rate",
         occurrence=3, prevention="Preheat ramp rate verification against the profile limits",
         detection_control="X-ray sampling per shift", detection=5),
    dict(process_step="Reflow soldering", failure_mode="Head-in-pillow",
         effect="BGA ball does not fully coalesce with the paste deposit; intermittent open under thermal cycling",
         severity=7, cause="BGA ball oxidation combined with board warpage at reflow peak",
         occurrence=2, prevention="BGA ball co-planarity check and nitrogen-atmosphere reflow",
         detection_control="X-ray sampling of BGA lots per shift", detection=5),
    dict(process_step="Reflow soldering", failure_mode="Solder balls",
         effect="Loose solder spheres between pads; risk of migration and short circuit",
         severity=6, cause="Excess paste volume or moisture in the paste causing spatter during reflow",
         occurrence=3, prevention="SPI paste volume control and incoming paste moisture check",
         detection_control="AOI 100% post-reflow inspection", detection=3),
    dict(process_step="Stencil printing", failure_mode="Stencil blockage",
         effect="Missing or insufficient paste deposit at the affected pads; open joint",
         severity=6, cause="Dried paste residue builds up in fine-pitch apertures between cleaning cycles",
         occurrence=3, prevention="Increased under-stencil wipe frequency for fine-pitch stencils",
         detection_control="SPI 100% paste area measurement", detection=3),
    # Row 14 inserted here by code, verbatim.
    dict(process_step="Board transport", failure_mode="Conveyor vibration",
         effect="Component shift or tombstoning on boards passing through the vibration zone",
         severity=5, cause="Worn conveyor belt or a loose board-stop sensor mount",
         occurrence=2, prevention="Conveyor preventive maintenance and belt tension check",
         detection_control="AOI 100% post-reflow inspection", detection=3),
    dict(process_step="Component storage", failure_mode="Oxidation",
         effect="Poor wetting at component leads; open or weak joint",
         severity=5, cause="Components stored beyond shelf life outside the humidity-controlled cabinet",
         occurrence=2, prevention="First-in-first-out component storage in humidity-controlled cabinets",
         detection_control="Incoming lead solderability sample test", detection=5),
    dict(process_step="Component storage", failure_mode="Moisture sensitivity",
         effect="Internal delamination or cracking of a moisture-sensitive package during reflow",
         severity=7, cause="Moisture-sensitive device exposed beyond its floor life before reflow",
         occurrence=2, prevention="MSL floor-life tracking with bake-out when the floor life is exceeded",
         detection_control="Acoustic microscopy sampling of suspect lots", detection=6),
    dict(process_step="Pick and place", failure_mode="Polarity reversal",
         effect="Reversed diode or polarized capacitor; functional failure or damage at power-on test",
         severity=8, cause="Component reel loaded in the wrong orientation at feeder changeover",
         occurrence=2, prevention="Feeder setup verification against the BOM polarity marking",
         detection_control="AOI polarity check 100% plus ICT functional test", detection=2),
    dict(process_step="Pick and place", failure_mode="Missing component",
         effect="Open circuit; functional failure at ICT",
         severity=7, cause="Feeder jam or an empty reel not detected before the placement cycle",
         occurrence=2, prevention="Feeder low-count alarm and first-article inspection after changeover",
         detection_control="AOI 100% post-placement plus ICT", detection=2),
    dict(process_step="AOI inspection", failure_mode="AOI false call",
         effect="Defective board shipped as good, or a good board scrapped on a false reject",
         severity=6, cause="AOI algorithm threshold drift after a software or lighting change",
         occurrence=2, prevention="AOI programming validation against known-good and known-defect reference boards",
         detection_control="Weekly AOI gauge R&R with a reference board set", detection=4),
]


def render_pfmea_row(number: int, row: dict) -> str:
    row = {**row, "ap": row.get("ap") or ap_from_severity(row["severity"])}
    note = (
        f"Mechanism: {row['failure_mode']} at {row['process_step']} is caused by "
        f"{row['cause']}. Effect: {row['effect']}. Prevention control: "
        f"{row['prevention']}. Detection control: {row['detection_control']}."
    )
    return (
        f"## Row {number}\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Process step | {row['process_step']} |\n"
        f"| Failure mode | {row['failure_mode']} |\n"
        f"| Effect | {row['effect']} |\n"
        f"| Severity | {row['severity']} |\n"
        f"| Cause | {row['cause']} |\n"
        f"| Occurrence | {row['occurrence']} |\n"
        f"| Prevention control | {row['prevention']} |\n"
        f"| Detection control | {row['detection_control']} |\n"
        f"| Detection | {row['detection']} |\n"
        f"| Action priority | {row['ap']} |\n\n"
        f"{note}\n"
    )


def make_pfmea() -> str:
    rows = PFMEA_ROWS[:13] + [ROW_14] + PFMEA_ROWS[13:]
    assert len(rows) == 20, f"expected 20 PFMEA rows, got {len(rows)}"
    sections = [render_pfmea_row(i + 1, r) for i, r in enumerate(rows)]
    header = (
        f"# PFMEA — SMT Reflow Line, {PRODUCT}\n\n"
        f"Plant: {PLANT}\n\n"
        "Process FMEA for the surface-mount reflow process (AIAG-VDA 2019 style). "
        "Twenty failure modes covering stencil printing, placement, reflow soldering, "
        "component storage and automated inspection.\n\n"
    )
    return header + "\n".join(sections) + FOOTER


# ---------------------------------------------------------------------------
# Control plan
# ---------------------------------------------------------------------------

ITEM_6 = {
    "characteristic": "Reflow profile verification after maintenance",
    "specification": f"Peak temperature 235-{PROFILE_LIMIT} °C, TAL 45-90 s, measured with a profiling board",
    "method": "Profiler run on a golden board",
    "frequency": "After any oven maintenance and once per shift",
    "reaction_plan": "hold lots produced since the last verified profile, re-profile the oven, re-qualify before release",
}

CONTROL_PLAN_ITEMS = [
    dict(characteristic="Incoming solder paste inspection",
         specification="Certificate of analysis within paste manufacturer limits; viscosity within supplier spec at receipt",
         method="Visual certificate review plus a viscometer spot check",
         frequency="Every paste lot at receipt",
         reaction_plan="quarantine the paste lot, notify supplier quality, do not release to the line until conforming"),
    dict(characteristic="SPI post-print paste inspection",
         specification="80-120% of stencil aperture volume per standard SMT guidance",
         method="Automated SPI 100% measurement, 3D laser",
         frequency="Every board, inline",
         reaction_plan="stop the printer, clean or replace the stencil, re-run first article before resuming"),
    dict(characteristic="Placement accuracy verification",
         specification="Component placement within ±0.05 mm of nominal for fine-pitch components",
         method="Placement machine vision check against the golden placement file",
         frequency="Every board, inline, with a gauge check at setup",
         reaction_plan="halt the placement head, recalibrate the vision system, inspect boards placed since the last good calibration"),
    dict(characteristic="Paste storage and working-life control",
         specification="Solder paste age from removal from refrigeration to last print within the manufacturer's working-life window",
         method="Paste cart timer tag and FIFO issue log",
         frequency="Every paste pot, continuous",
         reaction_plan="discard or return paste exceeding its working life, hold boards printed with over-age paste for SPI/AOI review"),
    dict(characteristic="Nitrogen purity monitoring",
         specification="Residual oxygen below 500 ppm in the reflow zones",
         method="Inline oxygen analyzer reading the nitrogen supply regulator",
         frequency="Continuous, logged every shift",
         reaction_plan="hold lots reflowed while out of specification, inspect and adjust the nitrogen regulator, re-verify purity before resuming"),
    # Item 6 inserted here by code, verbatim.
    dict(characteristic="AOI post-reflow inspection",
         specification="Zero bridges, opens, tombstones or missing components per the released inspection criteria",
         method="Automated optical inspection, 100% coverage",
         frequency="Every board, inline",
         reaction_plan="pull the board for manual verification and rework; if the defect rate trends upward, hold the lot and notify quality engineering"),
    dict(characteristic="ICT / functional electrical test",
         specification=f"Pass per the {PRODUCT} test specification",
         method="In-circuit test fixture plus functional test bench",
         frequency="100% of boards",
         reaction_plan="quarantine the failing board, root-cause the failure mode, hold the lot if the failure rate exceeds the alert limit"),
    dict(characteristic="Stencil cleaning (under-stencil wipe)",
         specification="No visible paste residue buildup in the apertures",
         method="Automatic under-stencil wipe cycle, vacuum plus dry wipe",
         frequency="Every N print cycles per the stencil program",
         reaction_plan="stop printing, manually clean the stencil, re-run SPI on the first boards after cleaning"),
    dict(characteristic="Squeegee pressure and speed setting",
         specification="Pressure and speed within the qualified process window for the stencil program",
         method="Printer setpoint verification against the approved process sheet",
         frequency="At setup and once per shift",
         reaction_plan="correct the setpoint, re-run SPI on the next boards, hold prior boards for paste volume review if the setpoint had drifted"),
    dict(characteristic="Conveyor speed verification",
         specification="Within the qualified process window for the released reflow profile",
         method="Conveyor speed readout check against the profile recipe",
         frequency="At setup and once per shift",
         reaction_plan="correct the conveyor speed, re-run a profile check, hold boards reflowed at the incorrect speed"),
    dict(characteristic="First-article inspection after setup change",
         specification="Conforms to drawing, AOI and ICT criteria before the lot is released",
         method="First-article visual, dimensional and electrical check",
         frequency="First board after every setup change",
         reaction_plan="hold the lot until the first article passes, re-run setup verification if it fails"),
]


def render_control_plan_item(number: int, item: dict) -> str:
    note = (
        f"Characteristic: {item['characteristic']}. Specification: {item['specification']}. "
        f"Method: {item['method']}. Frequency: {item['frequency']}. "
        f"Reaction plan: {item['reaction_plan']}."
    )
    return (
        f"## Item {number}\n\n"
        "| Field | Value |\n"
        "|---|---|\n"
        f"| Characteristic | {item['characteristic']} |\n"
        f"| Specification | {item['specification']} |\n"
        f"| Method | {item['method']} |\n"
        f"| Frequency | {item['frequency']} |\n"
        f"| Reaction plan | {item['reaction_plan']} |\n\n"
        f"{note}\n"
    )


def make_control_plan() -> str:
    items = CONTROL_PLAN_ITEMS[:5] + [ITEM_6] + CONTROL_PLAN_ITEMS[5:]
    assert len(items) == 12, f"expected 12 control plan items, got {len(items)}"
    sections = [render_control_plan_item(i + 1, it) for i, it in enumerate(items)]
    header = (
        f"# Control Plan — SMT Reflow Line, {PRODUCT}\n\n"
        f"Plant: {PLANT}\n\n"
        "Control plan for the surface-mount placement and reflow process, "
        "covering incoming paste through first-article release.\n\n"
    )
    return header + "\n".join(sections) + FOOTER


# ---------------------------------------------------------------------------
# Past 8D #1 — tombstoning
# ---------------------------------------------------------------------------

def make_past_8d_tombstoning() -> str:
    customer = "Hoshino Denso (fictional)"
    lot = "L2389"
    complaint = "C-2026-024"
    capa = "CAPA-0098"
    sections = {
        "D1": (
            "**Team.** SMT process engineer (lead), quality engineer, production shift "
            "supervisor, and a supplier quality representative from the solder paste supplier. "
            "The team had process ownership of stencil printing, reflow and incoming paste control."
        ),
        "D2": (
            f"**Problem description.** {customer} raised complaint {complaint} on 2026-07-02, "
            f"reporting tombstoning on 0402 chip resistors on {PRODUCT}, lot {lot}. Twelve of 500 "
            "boards showed one end of the resistor lifted off the pad at positions R23 and R47, "
            "found during the customer's incoming inspection."
        ),
        "D3": (
            f"**Containment.** The remaining boards in lot {lot} and the two adjacent lots were "
            "pulled and 100% re-inspected under magnification. Stock already shipped to "
            f"{customer} was sorted at incoming. Tombstoned boards were reworked where the "
            "resistor could be re-seated and re-reflowed by hand; boards with pad lift were scrapped."
        ),
        "D4": (
            "**Root cause.** The solder paste pot used to print the affected boards had been out "
            "of refrigeration for roughly 26 hours before the last boards in the pot were printed, "
            "beyond the paste manufacturer's stated working-life window. The paste had begun to "
            "dry and lose tack, so one end of the 0402 resistor reflowed and wetted before the "
            "other; the imbalance in surface-tension pull lifted the lighter end off the pad. "
            "The root cause was paste age beyond its working window, not an operator action: the "
            "paste cart had no visible timer or hold tag, so there was no way for anyone on the "
            "line to see that the pot was already past its working life."
        ),
        "D5": (
            "**Permanent corrective action.** A paste cart timer tag was introduced: every paste "
            "pot is tagged with the time it leaves refrigeration and a hard stop time by which it "
            "must be off the line. Paste is issued first-in-first-out from the fridge, and SPI is "
            "configured to flag a volume trend consistent with aging paste."
        ),
        "D6": (
            "**Verification of effectiveness.** Tombstoning escapes on 0402 passives dropped from "
            "a running average of roughly 1 in 2,000 boards to zero over the four weeks following "
            "the timer-tag rollout, tracked against AOI tombstoning counts by week."
        ),
        "D7": (
            "**Prevent recurrence.** PFMEA Row 2 (tombstoning) and Control plan Item 4 (paste "
            "storage and working-life control) were updated to reference the paste cart timer tag "
            "and the hard stop time as the prevention control."
        ),
        "D8": (
            f"**Closure.** Corrective actions verified effective and closed under {capa}. The 8D "
            f"was approved and sent to {customer} against complaint {complaint}."
        ),
    }
    header = (
        f"# Past 8D — Tombstoning on 0402 Resistors ({capa})\n\n"
        f"Plant: {PLANT}\n\n"
        f"Product: {PRODUCT} | Customer: {customer} | Complaint: {complaint} | Lot: {lot}\n\n"
    )
    body = "\n\n".join(f"## {d}\n\n{text}" for d, text in sections.items())
    return header + body + "\n" + FOOTER


# ---------------------------------------------------------------------------
# Past 8D #2 — voids under QFN
# ---------------------------------------------------------------------------

def make_past_8d_voids() -> str:
    capa = "CAPA-0111"
    lot = "L2457"
    sections = {
        "D1": (
            "**Team.** SMT process engineer (lead), quality engineer, reflow equipment "
            "technician, and the facilities technician responsible for the nitrogen generation "
            "and distribution system."
        ),
        "D2": (
            f"**Problem description.** A routine X-ray audit on {PRODUCT} lot {lot} found void "
            "area under the QFN thermal pad exceeding the acceptance limit on 9 of 30 sampled "
            "boards, flagged before the lot shipped."
        ),
        "D3": (
            f"**Containment.** Lot {lot} and the three lots produced on the same reflow oven "
            "since the last verified nitrogen purity check were held. Each held lot was 100% "
            "X-rayed under the QFN thermal pad; boards exceeding the void area limit were scrapped, "
            "boards within limit were released."
        ),
        "D4": (
            "**Root cause.** The reflow oven's nitrogen supply regulator had drifted out of "
            "calibration, allowing residual oxygen in the reflow zones to rise above the 500 ppm "
            "specification. The resulting increase in oxidation of the paste flux and the QFN "
            "thermal pad surface slowed and delayed flux outgassing during reflow, trapping more "
            "gas under the thermal pad as the solder solidified and producing void area beyond the "
            "acceptance limit. The root cause was nitrogen supply regulator drift, not an operator "
            "action: the regulator had no alarm, so the drift was invisible until the X-ray audit "
            "caught it."
        ),
        "D5": (
            "**Permanent corrective action.** An inline oxygen analyzer with a low-purity alarm "
            "was installed on the nitrogen feed to the reflow oven, interlocked to stop the "
            "conveyor if residual oxygen rises above 500 ppm. A preventive calibration schedule for "
            "the nitrogen regulator was added to the maintenance plan."
        ),
        "D6": (
            "**Verification of effectiveness.** Void area under QFN thermal pads on weekly X-ray "
            "sampling returned to the historical baseline within two weeks of the analyzer and "
            "alarm going live, with no exceedances in the eight weeks tracked afterward."
        ),
        "D7": (
            "**Prevent recurrence.** PFMEA Row 3 (voids under BGA/QFN thermal pad) and Control "
            "plan Item 5 (nitrogen purity monitoring) were updated to reference the inline oxygen "
            "analyzer and low-purity alarm as the detection and prevention controls."
        ),
        "D8": (
            f"**Closure.** Corrective actions verified effective and closed under {capa}."
        ),
    }
    header = (
        f"# Past 8D — Voids Under QFN Thermal Pad ({capa})\n\n"
        f"Plant: {PLANT}\n\n"
        f"Product: {PRODUCT} | Lot: {lot} | Discovered via internal X-ray audit\n\n"
    )
    body = "\n\n".join(f"## {d}\n\n{text}" for d, text in sections.items())
    return header + body + "\n" + FOOTER


if __name__ == "__main__":
    (OUT / "pfmea.md").write_text(make_pfmea())
    (OUT / "control_plan.md").write_text(make_control_plan())
    (OUT / "past_8d_tombstoning.md").write_text(make_past_8d_tombstoning())
    (OUT / "past_8d_voids.md").write_text(make_past_8d_voids())
    print(f"wrote 4 quality documents to {OUT}")
