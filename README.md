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
`agent.tools.vision_tool.analyze_defect_image` against `data/images/defect_01.jpg` and
`data/images/no_defect_01.jpg` respectively and saving the typed `Defect` response. They let
`agent/tests/test_vision_tool.py` test the wiring (vision tool → Pydantic `Defect`) without
ever calling the live model. Regenerate them with:

```bash
python - <<'PY'
import pathlib
from agent.tools.vision_tool import analyze_defect_image
fx = pathlib.Path("agent/tests/fixtures")
for src, name in [("data/images/defect_01.jpg", "vision_solder_bridge.json"),
                  ("data/images/no_defect_01.jpg", "vision_clean_board.json")]:
    d = analyze_defect_image(pathlib.Path(src).read_bytes(), "image/jpeg")
    (fx / name).write_text(d.model_dump_json(indent=2))
PY
```

whenever `agent/prompts/vision.md` changes. The filenames are historical (chosen before any
image had been vision-tested) and do not describe their contents — see Known issues below.

## Known issues

- **No VisA demo image reads as a solder bridge, and the "clean board" reference image is
  not reliably read as defect-free either.** The `pcb3` VisA images are bent-lead/dislodged-
  component anomalies (see `data/images/IMAGES.md`), so `vision_solder_bridge.json` actually
  records a `contamination` response for `defect_01.jpg`, not `solder_bridge`. More
  surprisingly, repeated calls against `no_defect_01.jpg` (the dataset's own "normal" board)
  never returned `type: none` — across four calls it alternated between `misalignment` and
  `contamination`, both at 0.90+ confidence; `vision_clean_board.json` records one such call.
  This is genuine Gemini behaviour on this image, not a bug in the vision tool or prompt. The
  demo narrative and any later task that assumes a reliable "no defect found" image should
  account for this — see `.superpowers/sdd/2026-10-16-8d-copilot-prototype/task-5-report.md`
  for the full table of results across all five images.
- `pip install -e ".[dev]"` from `backend/` succeeded on Python 3.12.15, including
  `google-adk>=1.0` (resolved to 1.14.1).
