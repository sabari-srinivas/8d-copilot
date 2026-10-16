# 8D Copilot

A quality-engineering agent for an SMT electronics plant (Sree Electronics (fictional), Chennai):
a defect photo plus a customer complaint go in, and statistically tested root causes plus a
cited 8D report come out. This is a hackathon prototype; all plant, customer and defect data
is synthetic. This README is a stub — the full project documentation lands in a later task.

## Layout

```
prototype/
├── backend/            # Python: FastAPI app, agents, tools, synthetic data
│   ├── agent/
│   │   ├── agents/
│   │   ├── prompts/
│   │   ├── tools/
│   │   ├── tests/
│   │   │   └── fixtures/
│   │   ├── config.py
│   │   └── models.py
│   ├── data/
│   │   ├── docs/
│   │   ├── images/
│   │   └── out/
│   ├── infra/
│   │   └── probe_models.py
│   ├── pyproject.toml
│   └── pytest.ini
├── frontend/           # React UI (not yet created)
├── docs/
│   └── contract/       # API contract and mock JSON shared by backend and UI
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

## Fixtures

`backend/agent/tests/fixtures/vision_solder_bridge.json` and `vision_clean_board.json` are
**recorded real Gemini output**, not hand-written examples — produced by calling
`agent.tools.vision_tool.analyze_defect_image` against `data/images/defect_03.jpg` (the
golden-path solder-bridge image) and `data/images/no_defect_01.jpg` (the clean-board
image) respectively, and saving the typed `Defect` response. Both fixtures now genuinely
contain what their filenames say — see `data/images/IMAGES.md` for how that was arrived
at and how stable each read is. They let `agent/tests/test_vision_tool.py` test the wiring
(vision tool → Pydantic `Defect`) without ever calling the live model. Regenerate them
with:

```bash
python - <<'PY'
import pathlib
from agent.tools.vision_tool import analyze_defect_image
fx = pathlib.Path("agent/tests/fixtures")
for src, name in [("data/images/defect_03.jpg", "vision_solder_bridge.json"),
                  ("data/images/no_defect_01.jpg", "vision_clean_board.json")]:
    d = analyze_defect_image(pathlib.Path(src).read_bytes(), "image/jpeg")
    (fx / name).write_text(d.model_dump_json(indent=2) + "\n")
PY
```

whenever `agent/prompts/vision.md` changes — then check the regenerated `type` still
matches the filename before committing, since neither read is perfectly stable (see
Known issues).

## Known issues

- **`defect_03.jpg` is the golden-path solder-bridge image for the demo** (not
  `defect_01.jpg`, which earlier drafts of this README assumed). Under the final
  `agent/prompts/vision.md`, `defect_03.jpg` reads as `solder_bridge` (critical) in 2 of 3
  live calls and `none` in the third; `no_defect_01.jpg` reads as `none` in 3 of 4 calls
  and `misalignment` in the fourth. Both are majority-stable, not unanimous — re-run before
  a live demo if either image is called live rather than only through the recorded
  fixtures.
- **`defect_01.jpg` and `defect_02.jpg` are false negatives.** Both carry genuine,
  documented anomalies (see `data/images/IMAGES.md`) but both consistently read as `none`
  under the final prompt, across two independent rounds of prompt tightening. This was a
  deliberate trade-off: an earlier, blunter "uncertainty resolves toward none" rule made
  the clean-board image reliable but suppressed these two real defects as well; the
  current prompt distinguishes "unsure of type" from "no anomaly at all" and recovered
  `defect_04.jpg` and (mostly) `defect_03.jpg`, but not these two. Do not keep tuning the
  prompt against this without a plan — see
  `.superpowers/sdd/2026-10-16-8d-copilot-prototype/task-5-report.md` for the full
  before/after table across both prompt revisions and all five images.
- `pip install -e ".[dev]"` from `backend/` succeeded on Python 3.12.15, including
  `google-adk>=1.0` (resolved to 1.14.1).
