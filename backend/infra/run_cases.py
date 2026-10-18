"""Seven-case hardening harness (task 15c).

Drives the real FastAPI app in-process (fastapi.testclient.TestClient, backed by
httpx) through agent.main.app, exactly the surface a real client hits, with the
local backends from .env (PLANT_BACKEND=csv, STATE_BACKEND=memory, FILES_BACKEND=
local, DOCS_BACKEND=local). REPLAY_CASE must be unset — this makes real model
calls. No model name is hard-coded here; agent/tools/llm.py is the only place
that constructs a genai.Client, from env.

PRD gate: at least 6 of 7 cases must PASS or be SKIPPED for quota. A 429 that
survives llm.py's own retries is a quota refusal, not a code failure, and must
not fail the gate. A timeout is a genuine hang and DOES fail the gate.

Usage (from backend/, venv active, REPLAY_CASE unset):
    python infra/run_cases.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from agent.config import get_settings  # noqa: E402
from agent.tools.plant_data import NUMERIC_PARAMS  # noqa: E402
from agent.tools.stats_test import DEFAULT_EVENT_PARAM  # noqa: E402

IMAGES = BACKEND_DIR / "data" / "images"
OUT_JSON = BACKEND_DIR / "data" / "out" / "run_cases.json"

# Spacing between cases: 7 golden paths is ~35 model calls against a Vertex quota
# that has returned 429 repeatedly on this project. 20s between case *starts* gives
# the token/request-per-minute budget room to recover between the ~5-call bursts
# each case makes (vision + intake + investigator + evidence + writer).
INTER_CASE_DELAY_S = 20.0
POLL_INTERVAL_S = 2.0
# A slow run has taken 90s end to end; triple that for margin before calling it a
# hang rather than just slow.
CASE_TIMEOUT_S = 270.0

TERMINAL_STATUSES = {"draft_ready", "insufficient_evidence", "approved", "failed"}

# llm.py's TransientAPIError message is literally "giving up after N attempts:
# status <code>" (see agent/tools/llm.py:_call_with_retry). That string survives
# into Investigation.missing_data via orchestrator.run_investigation's except
# block (format_error_message), which is the only place this harness looks for
# it — never guessed from timing or exception type.
_STATUS_CODE_RE = re.compile(r"status (\d+)")


@dataclass
class Case:
    name: str
    lot: str
    image: str
    complaint_id: str
    complaint_text: str
    expect_status: set[str]
    need_supported_param: str | None = None   # e.g. "reflow_peak_temp_c"
    min_rejected: int | None = 1              # None = no rejected-count requirement


CASES: list[Case] = [
    Case("golden", "L2611", "defect_03.jpg", "C-2026-031",
        "Solder bridging found on ECU-PCB-7, lot 2611, 14 of 500 units at our "
        "incoming/ICT. Please contain immediately and send 8D within 10 working days.",
        expect_status={"draft_ready"}, need_supported_param="reflow_peak_temp_c",
        min_rejected=1),
    Case("drift lot", "L2612", "defect_03.jpg", "",
        "Solder bridging reported on ECU-PCB-7, lot 2612. Please investigate and "
        "provide 8D.",
        expect_status={"draft_ready"}, min_rejected=1),
    Case("drift lot", "L2614", "defect_03.jpg", "",
        "Solder bridging reported on ECU-PCB-7, lot 2614. Please investigate and "
        "provide 8D.",
        expect_status={"draft_ready"}, min_rejected=1),
    Case("good lot", "L2590", "defect_03.jpg", "",
        "Solder bridging reported on ECU-PCB-7, lot 2590. Please investigate and "
        "provide 8D.",
        expect_status={"draft_ready", "insufficient_evidence"}, min_rejected=1),
    Case("good lot", "L2601", "defect_03.jpg", "",
        "Solder bridging reported on ECU-PCB-7, lot 2601. Please investigate and "
        "provide 8D.",
        expect_status={"draft_ready", "insufficient_evidence"}, min_rejected=1),
    Case("line 1 lot", "L2605", "defect_03.jpg", "",
        "Solder bridging reported on ECU-PCB-7, lot 2605. Please investigate and "
        "provide 8D.",
        expect_status={"draft_ready", "insufficient_evidence"}, min_rejected=1),
    Case("no defect", "L2611", "no_defect_01.jpg", "",
        "Routine incoming inspection photo for ECU-PCB-7, lot 2611.",
        expect_status={"insufficient_evidence"}, min_rejected=None),
]


@dataclass
class CaseResult:
    case: Case
    outcome: str = "FAIL"       # PASS / FAIL / SKIP
    status_reached: str = ""
    verdict_counts: dict = field(default_factory=dict)
    elapsed_s: float = 0.0
    reason: str = ""


def _quota_status_code(message: str) -> int | None:
    match = _STATUS_CODE_RE.search(message or "")
    return int(match.group(1)) if match else None


def _effective_param(hyp: dict) -> str | None:
    """The parameter a hypothesis actually gets tested against (agent/tools/stats_test.py
    test_hypothesis): an event-based hypothesis (event_wo_id set, parameter usually None)
    is tested against DEFAULT_EVENT_PARAM unless its own `parameter` is itself numeric —
    Hypothesis.parameter alone is NOT a reliable way to ask "was reflow temperature
    tested", which is why this mirrors that routing rather than reading the field raw."""
    if hyp.get("event_wo_id"):
        p = hyp.get("parameter")
        return p if p in NUMERIC_PARAMS else DEFAULT_EVENT_PARAM
    return hyp.get("parameter")


def _is_quota_refusal(missing_data: list[str]) -> bool:
    for line in missing_data or []:
        if "TransientAPIError" not in line:
            continue
        code = _quota_status_code(line)
        if code == 429:
            return True
    return False


def run_case(client: TestClient, case: Case) -> CaseResult:
    result = CaseResult(case=case)
    t0 = time.monotonic()
    image_path = IMAGES / case.image
    try:
        resp = client.post(
            "/api/investigations",
            files={"image": (case.image, image_path.read_bytes(), "image/jpeg")},
            data={"complaint_id": case.complaint_id, "lot_id": case.lot,
                  "complaint_text": case.complaint_text})
        resp.raise_for_status()
        inv_id = resp.json()["id"]
    except Exception as exc:
        result.elapsed_s = round(time.monotonic() - t0, 1)
        result.reason = f"could not start investigation: {exc.__class__.__name__}: {exc}"
        result.outcome = "FAIL"
        return result

    inv = None
    while time.monotonic() - t0 < CASE_TIMEOUT_S:
        r = client.get(f"/api/investigations/{inv_id}")
        if r.status_code == 200:
            inv = r.json()
            if inv["status"] in TERMINAL_STATUSES:
                break
        time.sleep(POLL_INTERVAL_S)
    result.elapsed_s = round(time.monotonic() - t0, 1)

    if inv is None or inv["status"] not in TERMINAL_STATUSES:
        result.status_reached = inv["status"] if inv else "unknown"
        result.outcome = "FAIL"
        result.reason = f"timed out after {CASE_TIMEOUT_S:.0f}s waiting for a terminal status"
        return result

    result.status_reached = inv["status"]
    verdicts: dict[str, int] = {}
    for r_ in inv.get("results", []):
        verdicts[r_["verdict"]] = verdicts.get(r_["verdict"], 0) + 1
    result.verdict_counts = verdicts

    if inv["status"] == "failed":
        if _is_quota_refusal(inv.get("missing_data", [])):
            result.outcome = "SKIP"
            result.reason = f"quota refusal (429): {inv['missing_data'][-1]}"
        else:
            result.outcome = "FAIL"
            msg = inv["missing_data"][-1] if inv.get("missing_data") else "no message"
            result.reason = f"investigation failed: {msg}"
        return result

    if inv["status"] not in case.expect_status:
        result.outcome = "FAIL"
        result.reason = (f"expected status in {sorted(case.expect_status)}, "
                         f"got {inv['status']!r}")
        return result

    if case.min_rejected is not None:
        rejected = verdicts.get("rejected", 0)
        if rejected < case.min_rejected:
            result.outcome = "FAIL"
            result.reason = f"expected >= {case.min_rejected} rejected verdicts, got {rejected}"
            return result

    if case.need_supported_param:
        hyps = {h["id"]: h for h in inv.get("hypotheses", [])}
        supported_ids = {r_["hypothesis_id"] for r_ in inv.get("results", [])
                        if r_["verdict"] == "supported"}
        has_param = any(_effective_param(hyps[hid]) == case.need_supported_param
                        for hid in supported_ids if hid in hyps)
        if not has_param:
            result.outcome = "FAIL"
            result.reason = (f"no supported hypothesis on parameter "
                             f"{case.need_supported_param!r}")
            return result

    result.outcome = "PASS"
    return result


def _print_table(results: list[CaseResult]) -> None:
    header = f"{'#':<3}{'case':<12}{'lot':<8}{'result':<6}{'status':<22}{'verdicts':<28}{'secs':>6}"
    print(header)
    print("-" * len(header))
    for i, res in enumerate(results, 1):
        verdicts_str = ", ".join(f"{k}:{v}" for k, v in sorted(res.verdict_counts.items())) or "-"
        print(f"{i:<3}{res.case.name:<12}{res.case.lot:<8}{res.outcome:<6}"
             f"{res.status_reached:<22}{verdicts_str:<28}{res.elapsed_s:>6.1f}")
        if res.reason:
            print(f"      -> {res.reason}")


def main() -> int:
    settings = get_settings()
    if settings.replay_case:
        print(f"REPLAY_CASE={settings.replay_case!r} is set — unset it before running "
             "the harness for real. Replaying would make every case pass meaninglessly.",
             file=sys.stderr)
        return 2

    from agent import main as app_main

    print(f"model: {settings.require_model()}")
    print(f"backends: plant={settings.plant_backend} state={settings.state_backend} "
         f"docs={settings.docs_backend} files={settings.files_backend}")
    print(f"inter-case delay: {INTER_CASE_DELAY_S:.0f}s · per-case timeout: "
         f"{CASE_TIMEOUT_S:.0f}s · poll interval: {POLL_INTERVAL_S:.0f}s")
    print()

    results: list[CaseResult] = []
    with TestClient(app_main.app) as client:
        for i, case in enumerate(CASES):
            print(f"--- case {i + 1}/{len(CASES)}: {case.name} ({case.lot}, {case.image}) ---")
            res = run_case(client, case)
            print(f"  -> {res.outcome} (status={res.status_reached}, "
                 f"{res.elapsed_s:.1f}s)" + (f" — {res.reason}" if res.reason else ""))
            results.append(res)
            if i < len(CASES) - 1:
                time.sleep(INTER_CASE_DELAY_S)

    print()
    _print_table(results)

    passed = sum(1 for r in results if r.outcome == "PASS")
    skipped = sum(1 for r in results if r.outcome == "SKIP")
    failed = sum(1 for r in results if r.outcome == "FAIL")
    gate_count = passed + skipped
    print()
    print(f"passed={passed} skipped={skipped} failed={failed} "
         f"(gate counts passed+skipped={gate_count}/7, need >=6)")

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        # No "model" field here on purpose (ENGINEERING_RULES.md rule 3 / test_llm.py's
        # no-hard-coded-model-id guard, which scans .json too): the model actually used
        # is already printed to stdout above (`print(f"model: ...")`) for whoever runs
        # the harness, and that printed report is exactly where an ephemeral run-time
        # fact like this belongs -- not baked into a file committed under backend/.
        "inter_case_delay_s": INTER_CASE_DELAY_S,
        "case_timeout_s": CASE_TIMEOUT_S,
        "passed": passed, "skipped": skipped, "failed": failed,
        "gate_passed": gate_count >= 6,
        "cases": [
            {"name": r.case.name, "lot": r.case.lot, "image": r.case.image,
             "outcome": r.outcome, "status_reached": r.status_reached,
             "verdict_counts": r.verdict_counts, "elapsed_s": r.elapsed_s,
             "reason": r.reason}
            for r in results
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {OUT_JSON}")

    return 0 if gate_count >= 6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
