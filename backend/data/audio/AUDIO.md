# Demo voice notes — provenance

Both files below are **synthesised speech**, not a recording of a real person —
there was no shift-lead voice note in the repo and no time to source or record one, so
these were generated with macOS's built-in `say` text-to-speech, exactly as CR #12
suggested ("`say` can synthesise speech to an audio file, which is honest for a demo
fixture as long as you label it as synthesised"). **They are demo fixtures for
`agent/tools/voice_tool.py`, not real plant audio.**

Both describe the same planted scenario already in `data/constants.py`: solder bridging
recurring on Line 2, and an oven that has been "odd" since a vendor visit on Wednesday —
i.e. a shift lead's floor-level echo of the WO-388 reflow-oven work the rest of the demo
data is built around. CR #12's point is literal here: this is not even a spreadsheet,
just someone talking.

| File | Voice | Language | Text | How made |
|---|---|---|---|---|
| `shift_lead_line2_en.wav` | Samantha (macOS default en-US voice) | English | "Bridging again on line two. Oven's been odd since the vendor came in on Wednesday." | `say -v Samantha -o shift_lead_line2_en.aiff "…"`, then `afconvert -f WAVE -d LEI16@22050` to 16-bit PCM WAV, mono, 22050 Hz, ~4.3 s. |
| `shift_lead_line2_ta.wav` | Vani (macOS `ta_IN` voice) | Tamil | "லைன் 2-ல் மீண்டும் பிரிட்ஜிங். வெண்டர் புதன்கிழமை வந்த பிறகு ஓவன் சரியில்லை." (the same remark, in Tamil) | Same `say` + `afconvert` pipeline, voice `Vani`. |

Both are plain 16-bit PCM `audio/wav`, chosen because it's one of Gemini's natively
supported audio MIME types and needs no further transcoding for `voice_tool.py`.

**Live-call note (Task 12 build):** only the English file was sent to the live model —
Vertex quota was tight enough that the task spec called for exactly one live call. The
Tamil file exercises the Tamil/Hindi path in the unit tests only (hermetic, via a
monkeypatched `generate_structured`), not against the live model. See
`.superpowers/sdd/2026-10-16-8d-copilot-prototype/voice-intake-report.md` for the live
call's verbatim transcript/extraction and the fixture it produced
(`backend/agent/tests/fixtures/voice_note_clean.json`).

*Synthesised demo audio — not a real shift lead, not a real recording.*
