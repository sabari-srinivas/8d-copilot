"""Looks at the defect photo. The only agent that sees image bytes, and it never
publishes them — only the typed read the vision tool returns.

Convention (see agent/agents/__init__.py): every blocking Gemini/embedding call in this
package runs through `asyncio.to_thread` so the event loop stays free for the SSE stream
and every other request while this agent is working. The tool functions themselves stay
synchronous — only the `await` sites here change."""
import asyncio

from agent.events import bus
from agent.models import Defect
from agent.tools.vision_tool import analyze_defect_image


async def run(inv_id: str, image_bytes: bytes, mime_type: str) -> Defect:
    await bus.publish(inv_id, "vision", "step_started", "Looking at the defect photo")
    defect = await asyncio.to_thread(analyze_defect_image, image_bytes, mime_type)
    summary = (f"{defect.type.replace('_', ' ').capitalize()} · "
               f"{defect.severity.capitalize()} · {defect.confidence:.0%}")
    # The Defect fields stay flat in `data` — the UI reads `data.box` to draw the overlay
    # (docs/contract/mock_events.json seq 5). No image bytes here or anywhere.
    await bus.publish(inv_id, "vision", "tool_result", summary,
                      detail=defect.visual_evidence,
                      data={"tool": "analyze_defect_image", "summary": summary,
                            **defect.model_dump()})
    return defect
