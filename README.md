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

## Known issues

None. `pip install -e ".[dev]"` from `backend/` succeeded on Python 3.12.15, including
`google-adk>=1.0` (resolved to 1.14.1).
