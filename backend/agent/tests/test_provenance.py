from agent.models import (Citation, Complaint, EightD, EightDSection, HypothesisResult,
                          Investigation)
from agent.tools.provenance import allowed_numbers, check_numbers, grounded_facts
from data.constants import DRIFT_LOT_IDS, GOLDEN_LOT, REFLOW_PEAK_LIMIT_C, WO388_DATE, WO388_ID


def _eight_d(d4_text: str) -> EightD:
    blank = EightDSection(text="Nothing numeric here.", citations=[])
    return EightD(D1=blank, D2=blank, D3=blank,
                  D4=EightDSection(text=d4_text, citations=[
                      Citation(label="PFMEA row 14", source="pfmea.md", ref="Row 14")]),
                  D5=blank, D6=blank, D7=blank, D8=blank)


def _inv() -> Investigation:
    return Investigation(id="inv_1", lot_id="L2611", results=[HypothesisResult(
        hypothesis_id="H2", verdict="supported", test="Welch t-test", p_value=0.003,
        effect="+8.2 °C mean reflow peak temp", effect_value=8.2, effect_unit="°C",
        n_defect=6, n_good=58)])


def _complaint() -> Complaint:
    """The real C-2026-031 figures the intake agent extracts."""
    return Complaint(complaint_id="C-2026-031", customer="Hoshino Denso (fictional)",
                     product="ECU-PCB-7", lot_id=GOLDEN_LOT, defect="solder_bridge",
                     qty_affected=14, qty_shipped=500, due_in_working_days=10,
                     received="2026-10-15", eight_d_due="2026-10-29",
                     text="Solder bridging found on ECU-PCB-7, lot 2611, 14 of 500 units "
                          "at our incoming/ICT. Please contain immediately and send 8D "
                          "within 10 working days.")


def test_numbers_from_tool_results_pass():
    inv = _inv()
    text = ("Peak temperature rose by 8.2 °C on Line 2 (Welch t-test, p = 0.003, "
            "6 defect lots vs 58 good lots) [Chart: reflow peak temp by lot].")
    assert check_numbers(_eight_d(text), allowed_numbers(inv)) == []


def test_an_invented_number_is_reported():
    inv = _inv()
    text = "Peak temperature rose by 12.7 °C [Chart: reflow peak temp by lot]."
    violations = check_numbers(_eight_d(text), allowed_numbers(inv))
    assert any("12.7" in v for v in violations)
    assert any("D4" in v for v in violations)


def test_citation_labels_and_lot_ids_are_allowed():
    inv = _inv()
    text = "Lots L2609 to L2614 are on hold [PFMEA row 14] [Control plan item 6]."
    assert check_numbers(_eight_d(text), allowed_numbers(inv) | {"2609", "2614", "14", "6"}) == []


def test_allowed_set_includes_p_value_effect_and_group_sizes():
    allowed = allowed_numbers(_inv())
    assert {"0.003", "8.2", "6", "58"} <= allowed


# --- the widened allowed set (task-9 review findings) ------------------------------


def test_every_hold_lot_id_is_allowed():
    """D3 names the exact lots on hold, so every one of their ids must be citable."""
    inv = _inv()
    inv.hold_lots = list(DRIFT_LOT_IDS)
    allowed = allowed_numbers(inv)
    assert {lot.lstrip("L") for lot in DRIFT_LOT_IDS} <= allowed


def test_the_profile_limit_comes_from_constants():
    allowed = allowed_numbers(_inv())
    assert f"{REFLOW_PEAK_LIMIT_C:g}" in allowed
    assert str(REFLOW_PEAK_LIMIT_C) in allowed


def test_the_complaints_own_figures_are_allowed():
    allowed = allowed_numbers(_inv(), complaint=_complaint())
    assert {"14", "500", "10"} <= allowed


def test_the_maintenance_record_date_and_post_check_are_allowed():
    """D4 explains the escape: the profile check after WO-388 was left pending."""
    inv = _inv()
    allowed = allowed_numbers(inv)
    assert WO388_ID.removeprefix("WO-") in allowed
    assert set(WO388_DATE.split("-")) <= allowed


def test_the_per_lot_peaks_and_window_statistics_are_allowed():
    """The writer is handed these so it can ground 'five of the six lots exceeded the
    limit' without claiming the complained-about lot was one of them."""
    inv = _inv()
    inv.hold_lots = list(DRIFT_LOT_IDS)
    facts = grounded_facts(inv)
    peaks = {row["lot_id"]: row["reflow_peak_temp_c"] for row in facts["lots"]}
    assert set(DRIFT_LOT_IDS) <= set(peaks)
    over = facts["peak_limit_breaches"]
    assert (over["n_over_limit"], over["n_lots"]) == (5, 6)
    assert GOLDEN_LOT not in over["lot_ids"], "L2611 is below the limit — it must not be listed"

    allowed = allowed_numbers(inv)
    assert {str(peak) for peak in peaks.values()} <= allowed
    assert str(facts["process_window"]["reflow_peak_temp_c"]["mean"]) in allowed


def test_a_sentence_grounded_in_the_widened_facts_passes_clean():
    inv = _inv()
    inv.hold_lots = list(DRIFT_LOT_IDS)
    text = ("14 of 500 units were affected and an 8D is due within 10 working days. "
            "Lots L2609 to L2614 are on hold. Five of the six lots in the affected window "
            "exceeded the 250 °C profile limit; lot L2611's own peak was 248.7 °C, below "
            "the limit, but its time above liquidus was 83 s. The profile check after "
            "WO-388 on 2026-10-08 was left pending [PFMEA row 14].")
    assert check_numbers(_eight_d(text), allowed_numbers(inv, complaint=_complaint())) == []


def test_an_unknown_lot_does_not_break_the_check():
    """A lot that is not in the plant data must degrade to the narrow set, not raise."""
    inv = Investigation(id="inv_1", lot_id="L9999")
    assert "12" in allowed_numbers(inv)


def test_a_number_hidden_in_a_later_section_is_still_caught():
    inv = _inv()
    blank = EightDSection(text="Nothing numeric here.")
    eight_d = EightD(D1=blank, D2=blank, D3=blank, D4=blank, D5=blank, D6=blank,
                     D7=EightDSection(text="Scrap cost was 41900 rupees."), D8=blank)
    violations = check_numbers(eight_d, allowed_numbers(inv))
    assert violations == ["D7: 41900 is not in any tool result"]
