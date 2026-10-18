"""Reads the customer complaint, the shift lead's spreadsheet if one was uploaded, and
the shift lead's voice note if one was uploaded (CR #12).

The traveler parse is the visible "works without an MES" moment: it reports how many rows
it recovered from a messy sheet and which cells it could not trust. The voice note pushes
that story further -- not even a spreadsheet, just a shift lead talking -- and reports the
same kind of thing: what it extracted, which language it heard, and which fields it is
not sure it heard correctly.

Convention (see agent/agents/__init__.py): every blocking Gemini/embedding call in this
package runs through `asyncio.to_thread` so the event loop stays free for the SSE stream
and every other request while this agent is working. `parse_lot_traveler` is NOT
threaded: it is pure in-memory openpyxl parsing of a small shift-lead sheet (no network
call), measured at low milliseconds, so the thread-hop would cost more than it saves.
`parse_complaint` and `analyze_voice_note` are both Gemini calls and are threaded."""
import asyncio

from agent.events import bus
from agent.models import Complaint, TravelerRow, VoiceNote
from agent.tools.intake_tools import parse_complaint, parse_lot_traveler
from agent.tools.voice_tool import analyze_voice_note


async def run(inv_id: str, complaint_text: str, complaint_id: str = "",
              traveler_bytes: bytes | None = None, voice_bytes: bytes | None = None,
              voice_mime: str = "audio/wav"
              ) -> tuple[Complaint, list[TravelerRow], VoiceNote | None]:
    await bus.publish(inv_id, "intake", "step_started", "Reading the customer complaint")
    complaint = await asyncio.to_thread(parse_complaint, complaint_text, complaint_id)
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

    voice_note: VoiceNote | None = None
    if voice_bytes:
        await bus.publish(
            inv_id, "intake", "tool_call",
            "Listening to the shift lead's voice note (Gemini audio)",
            # The size, never the bytes: no upload content in an event (ENGINEERING_RULES.md rule 6).
            data={"tool": "analyze_voice_note", "args": {"size_bytes": len(voice_bytes)}})
        voice_note = await asyncio.to_thread(analyze_voice_note, voice_bytes, voice_mime)
        language = voice_note.language_name or "language not identified"
        summary = f"Voice note transcribed ({language})"
        await bus.publish(
            inv_id, "intake", "tool_result", summary,
            detail=(f"Flagged for a human to confirm: {', '.join(voice_note.low_confidence_fields)}"
                    if voice_note.low_confidence_fields
                    else "Every extracted field transcribed with confidence"),
            data={"tool": "analyze_voice_note", "summary": summary,
                  **voice_note.model_dump()})

    return complaint, rows, voice_note
