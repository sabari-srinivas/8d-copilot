"""Every model that crosses a boundary. Field names here ARE the API contract."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

# Words a structured-output model sometimes writes as text in place of an actual
# null/absent value for a non-Optional string field (the JSON Schema for `str` has
# no way to express "no value", so the model falls back to writing the word).
_NULLISH_TEXT = {"null", "none", "n/a", "na", "-", "unknown"}

DefectType = Literal["solder_bridge", "missing_component", "misalignment",
                     "scratch", "contamination", "other", "none"]
Severity = Literal["critical", "major", "minor", "none"]
Verdict = Literal["supported", "rejected", "inconclusive"]
Direction = Literal["higher", "lower", "any"]
SixM = Literal["Machine", "Method", "Material", "Man", "Measurement", "Environment"]
Status = Literal["running", "draft_ready", "approved", "insufficient_evidence", "failed"]
ActionKind = Literal["capa", "hold", "work_order", "customer_reply"]
AgentName = Literal["intake", "vision", "investigator", "evidence", "writer", "system"]
EventType = Literal["step_started", "tool_call", "tool_result", "memory_hit", "hypothesis",
                    "hypothesis_result", "citation", "draft_ready", "done", "error",
                    "capa_effectiveness"]
# Did a past CAPA actually reduce the defect rate (agent/tools/capa_check.py)? A plain
# significance test has only three answers (Verdict above); "did this fix work" has an
# honest fourth one a single test cannot express -- it worked, then stopped.
CapaVerdict = Literal["worked", "never_worked", "regressed", "insufficient_data"]


class Complaint(BaseModel):
    complaint_id: str
    customer: str
    product: str
    lot_id: str
    defect: str
    qty_affected: int | None = None
    qty_shipped: int | None = None
    received: str = ""
    eight_d_due: str = ""
    status: Literal["open", "closed"] = "open"
    text: str = ""
    due_in_working_days: int | None = None

    @field_validator("received", "eight_d_due", mode="before")
    @classmethod
    def _blank_out_nullish_text(cls, v):
        """A structured-output model may send JSON null or the word "null" (etc.)
        for a date it doesn't have. Either way, downstream code (the inbox
        countdown, GET /complaints) must see an empty string, never a string
        that `date.fromisoformat` chokes on."""
        if v is None:
            return ""
        if isinstance(v, str) and v.strip().lower() in _NULLISH_TEXT:
            return ""
        return v


class Defect(BaseModel):
    type: DefectType
    severity: Severity
    box: list[float] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)
    visual_evidence: str

    @model_validator(mode="after")
    def _box_in_unit_square(self):
        if any(v < 0.0 or v > 1.0 for v in self.box):
            raise ValueError("box values must be 0-1 fractions")
        return self


class Hypothesis(BaseModel):
    """Proposed by the LLM. Carries NO verdict and NO numbers — those come from the stats tool."""
    id: str
    category: SixM
    text: str
    parameter: str | None = None
    event_wo_id: str | None = None
    direction: Direction = "any"

    @model_validator(mode="after")
    def _needs_something_measurable(self):
        if not self.parameter and not self.event_wo_id:
            raise ValueError("a hypothesis needs one measurable parameter or event")
        return self


class HypothesisResult(BaseModel):
    """Produced ONLY by agent/tools/stats_test.py."""
    hypothesis_id: str
    verdict: Verdict
    test: str
    p_value: float
    effect: str
    effect_value: float
    effect_unit: str
    n_defect: int
    n_good: int
    group_labels: list[str] = Field(default_factory=list)
    chart_url: str | None = None


class CapaEffectiveness(BaseModel):
    """Produced ONLY by agent/tools/capa_check.py. Same reporting shape as
    HypothesisResult (test/p_value/effect/effect_value/effect_unit/group
    sizes/group_labels/chart_url), computed by the same rule
    (agent/tools/stats_verdict.classify), plus the CAPA-specific context and the
    three-window (before / immediately-after / recent) breakdown documented in
    capa_check.py's module docstring.

    `p_value`/`effect_value`/`effect` carry whichever comparison decided `verdict`:
    before-vs-immediate for `never_worked`, before-vs-recent for `worked` and
    `regressed`. `p_immediate`/`p_recent` are always both present (when not
    `insufficient_data`) so nothing is hidden behind the headline number.
    """
    capa_id: str
    defect_type: str
    line: str
    implemented_on: str
    verdict: CapaVerdict
    test: str = "Welch t-test"
    p_value: float | None = None
    effect: str = ""
    effect_value: float | None = None
    effect_unit: str = "defect rate"
    n_before: int = 0
    n_immediate: int = 0
    n_recent: int = 0
    group_labels: list[str] = Field(default_factory=list)
    before_rate: float | None = None
    immediate_rate: float | None = None
    recent_rate: float | None = None
    p_immediate: float | None = None
    p_recent: float | None = None
    chart_url: str | None = None


class Citation(BaseModel):
    label: str
    source: str
    ref: str
    quote: str = ""


class EightDSection(BaseModel):
    text: str
    citations: list[Citation] = Field(default_factory=list)


class EightD(BaseModel):
    D1: EightDSection
    D2: EightDSection
    D3: EightDSection
    D4: EightDSection
    D5: EightDSection
    D6: EightDSection
    D7: EightDSection
    D8: EightDSection


class ProposedAction(BaseModel):
    id: str
    kind: ActionKind
    summary: str
    payload: dict = Field(default_factory=dict)


class MemoryEntry(BaseModel):
    id: str
    defect_type: str
    root_cause: str
    parameter: str = ""
    line: str = ""
    capa_id: str = ""
    lot_id: str = ""
    investigation_id: str = ""
    created: str = ""


class TravelerRow(BaseModel):
    lot_id: str
    date: str = ""
    shift: str = ""
    operator_id: str = ""
    reflow_peak_temp_c: float | None = None
    time_above_liquidus_s: float | None = None
    aoi_bridges: int | None = None
    remarks: str = ""
    low_confidence_fields: list[str] = Field(default_factory=list)


class Passage(BaseModel):
    source: str
    ref: str
    quote: str
    score: float = 0.0


class Investigation(BaseModel):
    id: str
    status: Status = "running"
    complaint_id: str = ""
    lot_id: str = ""
    created: str = ""
    photo_url: str = ""
    defect: Defect | None = None
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    results: list[HypothesisResult] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    traveler_rows: list[TravelerRow] = Field(default_factory=list)
    hold_lots: list[str] = Field(default_factory=list)
    eight_d: EightD | None = None
    proposed_actions: list[ProposedAction] = Field(default_factory=list)
    memory_hits: list[MemoryEntry] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    approver: str = ""
    chart_url: str | None = None


class Event(BaseModel):
    """One SSE envelope on GET /investigations/{id}/events — see docs/contract/README.md."""
    seq: int
    ts: str
    agent: AgentName
    type: EventType
    title: str
    detail: str = ""
    data: dict = Field(default_factory=dict)
