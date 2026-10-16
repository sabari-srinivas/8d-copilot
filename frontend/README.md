# 8D Copilot — frontend

React + TypeScript + Vite. Six screens: Inbox, New investigation, the live trace
(`/inv/:id`), Evidence, Review, Done. `docs/contract/README.md` (one level up) is the
authoritative API contract — this app is built against it.

## Running against the live backend

```bash
cd backend && source .venv/bin/activate && uvicorn agent.main:app --port 8000
```

```bash
cd frontend
printf 'VITE_API_URL=http://localhost:8000\nVITE_USE_MOCKS=false\n' > .env.local
npm install
npm run dev
```

`.env.local` is gitignored (`*.local`) — every machine sets its own. `VITE_API_URL` is
also the prefix every component must put in front of a `photo_url`/`chart_url` coming
back from the API: those are paths relative to the backend's own origin
(`/api/files/...`), and in dev the frontend and the API run on different ports, so a
bare `<img src>` 404s without it. See `resolveApiUrl` in `src/api/client.ts` — every
place a URL from the API reaches an `src`/`href` goes through it.

## Running against the committed mocks

```bash
cd frontend
cp .env.example .env.local   # VITE_USE_MOCKS=true
npm run dev
```

`VITE_USE_MOCKS=true` replays `docs/contract/mock_events.json` (one event every
600 ms) and serves `docs/contract/mock_investigation.json` for every `GET
/investigations/{id}` — no backend required. Useful for UI work in isolation; it
cannot catch anything that only the live API exposes (see below).

## Golden-path images (live backend only)

`backend/data/images/defect_03.jpg` is the one upload that reliably reads as
`solder_bridge` (not 100% stable — Gemini vision, not a fixture). `defect_01.jpg` and
`defect_02.jpg` are documented false negatives (`none`). `no_defect_01.jpg` is the
edge case: it should end in `insufficient_evidence` with the Approve button hidden.

## Commands

```bash
npm run dev      # Vite dev server
npm run test     # vitest
npm run build    # tsc -b && vite build
npm run lint     # oxlint
```

## Notes on the live API

- The investigation id is generated server-side by `POST /investigations` — always
  navigate using the id the response returns, never one the client made up.
- `draft_ready` is published by the writer before the orchestrator has necessarily
  finished writing the full state behind it (see `agent/orchestrator.py`), so
  `Evidence` and `Review` fetch through `getInvestigationReady` (`src/api/client.ts`)
  rather than `getInvestigation` directly — it refetches a few times if the draft the
  event promised hasn't landed yet, keyed off the SSE stream's own status rather than
  mount alone.
- SSE reconnects replay the investigation's full history; `useInvestigationStream`'s
  `seen` set (keyed on `seq`) drops anything already rendered, so a reconnect never
  double-renders an event.
