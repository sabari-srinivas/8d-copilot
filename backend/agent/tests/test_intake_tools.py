from datetime import date
from pathlib import Path

import pytest

from agent.models import Complaint
from agent.tools import intake_tools as it
from data.constants import GOLDEN_BRIDGES, GOLDEN_LOT, PRODUCT

XLSX = Path(__file__).resolve().parents[2] / "data" / "out" / "lot_traveler_line2_wk41.xlsx"


def test_working_days_skip_weekends():
    # Fri 16 Oct 2026 -> Mon 19 Oct 2026 is one working day.
    assert it.working_days_between(date(2026, 10, 16), date(2026, 10, 19)) == 1
    assert it.working_days_between(date(2026, 10, 16), date(2026, 10, 29)) == 9
    assert it.working_days_between(date(2026, 10, 29), date(2026, 10, 16)) == -9


def test_complaint_parsing_pulls_the_fields(monkeypatch):
    monkeypatch.setattr(it, "generate_structured", lambda *a, **k: Complaint(
        complaint_id="", customer="Hoshino Denso (fictional)", product=PRODUCT,
        lot_id=GOLDEN_LOT, defect="solder_bridge", qty_affected=GOLDEN_BRIDGES, qty_shipped=500,
        eight_d_due="2026-10-29"))
    c = it.parse_complaint(f"Solder bridging found on {PRODUCT}, lot 2611, "
                           f"{GOLDEN_BRIDGES} of 500 units...",
                           complaint_id="C-2026-031")
    assert c.complaint_id == "C-2026-031"
    assert c.lot_id == GOLDEN_LOT
    assert c.qty_affected == GOLDEN_BRIDGES


def test_traveler_finds_the_header_below_the_title_rows():
    rows = it.parse_lot_traveler(XLSX.read_bytes())
    assert len(rows) >= 6
    assert all(r.lot_id.startswith("L") for r in rows)


def test_traveler_normalises_short_lot_numbers_and_dd_mm_dates():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    assert GOLDEN_LOT in rows
    assert rows[GOLDEN_LOT].date.startswith("2026-")


def test_same_as_prev_becomes_null_and_is_flagged_low_confidence():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    r = rows["L2613"]
    assert r.reflow_peak_temp_c is None
    assert "reflow_peak_temp_c" in r.low_confidence_fields


def test_free_text_remarks_survive():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    assert "U7" in rows[GOLDEN_LOT].remarks


def test_traveler_bridge_counts_match_the_plant_record():
    rows = {r.lot_id: r for r in it.parse_lot_traveler(XLSX.read_bytes())}
    assert rows[GOLDEN_LOT].aoi_bridges == GOLDEN_BRIDGES


def test_a_file_that_is_not_a_spreadsheet_raises():
    with pytest.raises(ValueError, match="could not read"):
        it.parse_lot_traveler(b"this is not xlsx")


def test_complaints_list_carries_the_countdown():
    complaints = it.list_complaints()
    golden = next(c for c in complaints if c.complaint_id == "C-2026-031")
    assert golden.customer == "Hoshino Denso (fictional)"
    assert golden.due_in_working_days is not None
