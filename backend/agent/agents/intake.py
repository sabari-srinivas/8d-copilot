"""Reads the customer complaint, and the shift lead's spreadsheet if one was uploaded.

The traveler parse is the visible "works without an MES" moment: it reports how many rows
it recovered from a messy sheet and which cells it could not trust.
"""
from agent.events import bus
from agent.models import Complaint, TravelerRow
from agent.tools.intake_tools import parse_complaint, parse_lot_traveler


async def run(inv_id: str, complaint_text: str, complaint_id: str = "",
              traveler_bytes: bytes | None = None) -> tuple[Complaint, list[TravelerRow]]:
    await bus.publish(inv_id, "intake", "step_started", "Reading the customer complaint")
    complaint = parse_complaint(complaint_text, complaint_id)
    quantity = (f"{complaint.qty_affected} of {complaint.qty_shipped} units"
                if complaint.qty_affected and complaint.qty_shipped
                else f"{complaint.qty_affected} units" if complaint.qty_affected
                else "quantity not stated")
    summary = (f"{complaint.customer} · {complaint.product} · "
               f"lot {complaint.lot_id} · {quantity}")
    await bus.publish(
        inv_id, "intake", "tool_result", summary,
        detail=f"{complaint.defect} reported, 8D due {complaint.eight_d_due or 'not stated'}",
        data={"tool": "parse_complaint", "summary": summary, **complaint.model_dump()})

    rows: list[TravelerRow] = []
    if traveler_bytes:
        await bus.publish(inv_id, "intake", "tool_call",
                          "Reading the shift lead's lot traveler",
                          # The size, never the bytes: no upload content in an event.
                          data={"tool": "parse_lot_traveler",
                                "args": {"size_bytes": len(traveler_bytes)}})
        rows = parse_lot_traveler(traveler_bytes)
        low = sorted({field for row in rows for field in row.low_confidence_fields})
        recovered = f"{len(rows)} lot rows recovered from the spreadsheet"
        await bus.publish(
            inv_id, "intake", "tool_result", recovered,
            detail=(f"Could not read with confidence: {', '.join(low)} — "
                    f"flagged for a human to confirm" if low
                    else "Every mapped cell parsed cleanly"),
            data={"tool": "parse_lot_traveler", "summary": recovered,
                  "n_rows": len(rows), "low_confidence_fields": low})
    return complaint, rows
