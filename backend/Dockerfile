# 8D Copilot API — Cloud Run image.
#
# `pip install -e .` (editable), not a regular `pip install .`, is deliberate: every
# tool module (plant_data.py, storage.py, doc_search.py, replay.py) locates its data
# files via `Path(__file__).resolve().parents[N] / "data" / ...` — i.e. by walking up
# from the installed package's own file, assuming `data/` sits beside `agent/` in the
# same source tree. A non-editable install copies the `agent` package into
# site-packages while leaving `data/` wherever COPY put it, breaking that assumption.
# An editable install points imports straight back at /app/agent and /app/data,
# exactly mirroring how `backend/.venv` already works in local dev.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY agent ./agent
COPY data ./data

RUN pip install --no-cache-dir -e .

# Cloud Run must find data/out/replay/golden.json inside the image: replay mode
# (REPLAY_CASE=golden) is the demo's insurance against a Vertex quota refusal, and a
# recording nobody shipped is useless. data/out/ is otherwise excluded by
# .dockerignore (hand-verification junk: photos, charts, run_cases.json) — this
# fails the build loudly instead of deploying a service that can't replay.
RUN test -f data/out/replay/golden.json || \
    (echo "FATAL: data/out/replay/golden.json missing from the build context — check .dockerignore" >&2 && exit 1)

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn agent.main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 300"]
