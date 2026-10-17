import asyncio
import time

import pytest

from agent.agents import actions
from agent.models import (Citation, Defect, EightD, EightDSection, Hypothesis,
                          HypothesisResult, Investigation, ProposedAction)
from agent.state import MemoryStateStore


def _inv() -> Investigation:
    section = EightDSection(text="Original text [PFMEA row 14].",
                            citations=[Citation(label="PFMEA row 14", source="pfmea.md",
                                                ref="Row 14")])
    return Investigation(
        id="inv_1", complaint_id="C-2026-031", lot_id="L2611", status="draft_ready",
        defect=Defect(type="solder_bridge", severity="major", box=[0.1, 0.1, 0.2, 0.2],
                      confidence=0.86, visual_evidence="Bridge between two pads."),
        hypotheses=[Hypothesis(id="H2", category="Machine",
                               text="Reflow peak temperature drift on Line 2 after WO-388",
                               parameter="reflow_peak_temp_c", direction="higher")],
        results=[HypothesisResult(hypothesis_id="H2", verdict="supported", test="Welch t-test",
                                  p_value=0.003, effect="+8.2 °C", effect_value=8.2,
                                  effect_unit="°C", n_defect=6, n_good=58)],
        hold_lots=["L2609", "L2610", "L2611", "L2612", "L2613", "L2614"],
        eight_d=EightD(**{f"D{i}": section for i in range(1, 9)}),
        proposed_actions=[
            ProposedAction(id="A1", kind="capa", summary="CAPA"),
            ProposedAction(id="A2", kind="hold", summary="Hold",
                           payload={"lots": ["L2609", "L2610", "L2611",
                                             "L2612", "L2613", "L2614"]}),
            ProposedAction(id="A3", kind="work_order", summary="WO",
                           payload={"line": "L2", "asset": "Reflow oven",
                                    "description": "Verify and re-qualify reflow profile"}),
            ProposedAction(id="A4", kind="customer_reply", summary="Reply"),
        ])


@pytest.fixture
def store(monkeypatch):
    s = MemoryStateStore()
    monkeypatch.setattr(actions, "get_state", lambda: s)
    monkeypatch.setattr("agent.tools.memory.get_state", lambda: s)
    monkeypatch.setattr("agent.tools.memory.embed", lambda texts: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(actions, "generate_structured", lambda *a, **k: actions.Replies(
        ja="いつもお世話になっております。", en="Thank you for your continued support."))
    return s


@pytest.mark.asyncio
async def test_all_four_actions_create_records(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=[], note="")
    assert out["capa_id"].startswith("CAPA-")
    assert out["hold_id"].startswith("H-")
    assert out["work_order_id"].startswith("WO-")
    assert out["memory_id"].startswith("MEM-")
    assert out["replies"]["ja"] and out["replies"]["en"]


@pytest.mark.asyncio
async def test_a_rejected_action_is_not_created(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=["A3"], note="")
    assert out["work_order_id"] is None
    assert out["capa_id"] is not None


@pytest.mark.asyncio
async def test_edits_are_applied_and_attributed(store):
    inv = _inv()
    await actions.apply_approval(inv, approver="Priya R.",
                                 edits={"D4": "Edited by the engineer."},
                                 rejected_action_ids=[], note="checked on the line")
    saved = store.get_investigation("inv_1")
    assert saved.eight_d.D4.text == "Edited by the engineer."
    assert saved.eight_d.D1.text == "Original text [PFMEA row 14]."
    assert saved.status == "approved"
    assert saved.approver == "Priya R."


@pytest.mark.asyncio
async def test_hold_names_every_suspect_lot(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=[], note="")
    assert store.get_record("hold", out["hold_id"])["lots"] == [
        "L2609", "L2610", "L2611", "L2612", "L2613", "L2614"]


@pytest.mark.asyncio
async def test_memory_stores_the_confirmed_cause_only(store):
    await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                 rejected_action_ids=[], note="")
    entries = store.list_memory()
    assert len(entries) == 1
    assert "Reflow peak temperature drift" in entries[0].root_cause
    assert entries[0].defect_type == "solder_bridge"


@pytest.mark.asyncio
async def test_rejecting_capa_creates_no_capa_record(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=["A1"], note="")
    assert out["capa_id"] is None
    # The counters are reset before every test (conftest._reset_id_counters), so the
    # first capa id that WOULD have been issued is deterministic. Using the public
    # get_record accessor (not the store's private _records dict) keeps this test valid
    # against either StateStore backend.
    assert store.get_record("capa", "CAPA-0142") is None


@pytest.mark.asyncio
async def test_rejecting_hold_creates_no_hold_record(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=["A2"], note="")
    assert out["hold_id"] is None
    assert store.get_record("hold", "H-77") is None


@pytest.mark.asyncio
async def test_rejecting_customer_reply_creates_no_reply(store):
    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=["A4"], note="")
    assert out["replies"] is None
    # A null `replies` means either "excluded at review" or "attempted and failed" --
    # rejected_action_ids is how a caller tells the two apart. See also
    # test_a_failed_customer_reply_still_returns_the_other_results below, which hits
    # the OTHER path to a null `replies` and must produce an empty list here instead.
    assert out["rejected_action_ids"] == ["A4"]


@pytest.mark.asyncio
async def test_approving_twice_is_rejected(store):
    inv = _inv()
    await actions.apply_approval(inv, approver="Priya R.", edits={},
                                 rejected_action_ids=[], note="")
    with pytest.raises(ValueError, match="already approved"):
        await actions.apply_approval(store.get_investigation("inv_1"), approver="Priya R.",
                                     edits={}, rejected_action_ids=[], note="")


@pytest.mark.asyncio
async def test_a_failed_customer_reply_still_returns_the_other_results(store, monkeypatch):
    def _raise(*a, **k):
        raise RuntimeError("model unavailable")
    monkeypatch.setattr(actions, "generate_structured", _raise)

    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=[], note="")
    assert out["replies"] is None
    # Nothing was excluded here -- the reply was attempted and the model call raised.
    # This is the case test_rejecting_customer_reply_creates_no_reply above must stay
    # distinguishable from: same null `replies`, empty rejected_action_ids instead.
    assert out["rejected_action_ids"] == []
    assert out["capa_id"] is not None
    assert out["hold_id"] is not None
    assert out["work_order_id"] is not None
    assert out["memory_id"] is not None
    assert store.get_investigation("inv_1").status == "approved"


@pytest.mark.asyncio
async def test_a_failed_memory_save_still_returns_the_other_results(store, monkeypatch):
    def _raise(*a, **k):
        raise RuntimeError("embedding service unavailable")
    monkeypatch.setattr(actions, "save_quality_memory", _raise)

    out = await actions.apply_approval(_inv(), approver="Priya R.", edits={},
                                       rejected_action_ids=[], note="")
    assert out["memory_id"] is None
    assert out["capa_id"] is not None
    assert out["hold_id"] is not None
    assert out["work_order_id"] is not None
    assert out["replies"] is not None


@pytest.mark.asyncio
async def test_a_failure_after_claiming_still_blocks_a_second_approval_without_duplicates(
        store, monkeypatch):
    """Reproduces the reviewer's exact scenario: force the memory save to raise after the
    CAPA and hold have already been created, then confirm a retry on the same
    investigation raises (rather than issuing a second CAPA/hold) because the
    investigation was already claimed as "approved" before those records were made."""
    def _raise(*a, **k):
        raise RuntimeError("embedding service unavailable")
    monkeypatch.setattr(actions, "save_quality_memory", _raise)

    inv = _inv()
    out = await actions.apply_approval(inv, approver="Priya R.", edits={},
                                       rejected_action_ids=[], note="")
    assert out["memory_id"] is None
    assert out["capa_id"] == "CAPA-0142"
    assert out["hold_id"] == "H-77"

    with pytest.raises(ValueError, match="already approved"):
        await actions.apply_approval(store.get_investigation("inv_1"), approver="Priya R.",
                                     edits={}, rejected_action_ids=[], note="")

    # No second CAPA or hold was created by the retry attempt.
    assert store.get_record("capa", "CAPA-0143") is None
    assert store.get_record("hold", "H-78") is None


class RacyStore(MemoryStateStore):
    """Adds a deliberate delay to get_investigation/save_investigation — long enough
    that two nearly-simultaneous apply_approval calls can genuinely interleave inside
    the claim-check-then-write window, the way two real STATE_BACKEND=firestore round
    trips (measured at 0.1-0.6s each in the task 14 report) would. Plain
    MemoryStateStore calls return instantly, which would make a concurrency test here
    depend on being unlucky with thread scheduling rather than reliably exercising the
    race."""
    def get_investigation(self, inv_id):
        time.sleep(0.05)
        return super().get_investigation(inv_id)

    def save_investigation(self, inv):
        time.sleep(0.05)
        return super().save_investigation(inv)


@pytest.fixture
def racy_store(monkeypatch):
    s = RacyStore()
    monkeypatch.setattr(actions, "get_state", lambda: s)
    monkeypatch.setattr("agent.tools.memory.get_state", lambda: s)
    monkeypatch.setattr("agent.tools.memory.embed", lambda texts: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(actions, "generate_structured", lambda *a, **k: actions.Replies(
        ja="いつもお世話になっております。", en="Thank you for your continued support."))
    return s


@pytest.mark.asyncio
async def test_two_concurrent_approvals_create_exactly_one_set_of_records(racy_store):
    """Task 14 review, round 2: threading state.save_investigation/create_record put
    real `await` points in a path that previously had none at all, reopening the
    duplicate-CAPA race under genuine concurrency — not the sequential retry
    `test_approving_twice_is_rejected` and `test_a_failure_after_claiming_...` above
    already cover, where the second call fully awaits the first before ever starting.

    Two /approve calls for the same inv_id, issued together via asyncio.gather so they
    genuinely overlap (as two near-simultaneous HTTP requests would), must settle on
    exactly one winner and exactly one of each record — not two CAPAs for one defect.

    Each "request" gets its OWN independent Investigation object (two separate `_inv()`
    calls), not two references to the one `MemoryStateStore.get_investigation` returns
    (which hands back the literal stored object, not a copy): two real HTTP requests
    each deserialize their own copy from the state store, and a test that let both
    coroutines share one Python object would have one coroutine's `inv.status =
    "approved"` mutation instantly visible to the other through that shared reference,
    masking the race this test exists to catch behind an aliasing accident instead of
    the real fix."""
    racy_store.save_investigation(_inv())  # both "requests" read an already-stored inv,
                                           # as they would via main.py's GET first

    results = await asyncio.gather(
        actions.apply_approval(_inv(), approver="Priya R.",
                               edits={}, rejected_action_ids=[], note=""),
        actions.apply_approval(_inv(), approver="Vik S.",
                               edits={}, rejected_action_ids=[], note=""),
        return_exceptions=True)

    successes = [r for r in results if not isinstance(r, BaseException)]
    failures = [r for r in results if isinstance(r, BaseException)]
    assert len(successes) == 1, f"expected exactly one winner, got: {results}"
    assert len(failures) == 1 and isinstance(failures[0], ValueError), \
        f"expected exactly one ValueError loser, got: {results}"
    assert "already approved" in str(failures[0])

    # Exactly one of each record exists — not two CAPAs/holds/work orders for one
    # investigation. CAPA-0143/H-78/WO-413 are the ids a second, un-prevented creation
    # would have taken (agent.state's id counters are sequential per kind).
    assert racy_store.get_record("capa", "CAPA-0142") is not None
    assert racy_store.get_record("capa", "CAPA-0143") is None
    assert racy_store.get_record("hold", "H-77") is not None
    assert racy_store.get_record("hold", "H-78") is None
    assert racy_store.get_record("work_order", "WO-412") is not None
    assert racy_store.get_record("work_order", "WO-413") is None
