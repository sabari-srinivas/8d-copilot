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
AgentName = Literal["intake", "vision", "investigator", "evidence", "writer", "reviser",
                    "system"]
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
    # PRD opening line, made literal: "the 8D gets sent back". A rejection is a
    # customer's response to an 8D Priya's team ALREADY submitted, not a fresh defect
    # report -- the UI and agent/orchestrator.py both branch on this flag rather than
    # inferring it from free text, since whether a complaint is a rejection is a fact
    # about the complaint record, not something an LLM should have to guess twice.
    is_rejection: bool = False
    # The customer's stated reason for sending the 8D back, e.g. "root cause stated
    # as operator error; not acceptable". Empty for an ordinary new-defect complaint.
    objection: str = ""
    # The full D1-D8 text of the 8D that was submitted and rejected, in the same shape
    # as EightD (dict, not the EightD type itself, so parse_complaint's LLM schema
    # stays a plain JSON object here rather than forcing the model to reproduce eight
    # nested sections on every complaint parse -- agent/agents/reviser.py validates
    # it into an EightD when it actually needs one). None for an ordinary complaint.
    original_eight_d: dict | None = None

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


class VoiceNote(BaseModel):
    """Produced by agent/tools/voice_tool.py from an uploaded shift-lead recording
    (CR #12). Schema is built around what the investigator can use as evidence, not
    around what is easy to transcribe -- `transcript` alone is a toy; `lot_or_line`,
    `observations` and `maintenance_mentions` are what a human can actually act on.
    Gemini handles audio natively (Tamil `ta-IN` and Hindi `hi-IN` alongside English),
    so a note need not be in English -- `language`/`language_name` report what was
    heard, and `translation` always carries an English rendering regardless."""
    language: str = ""            # e.g. "ta-IN", "hi-IN", "en-IN" -- as the model names it
    language_name: str = ""       # human-readable, e.g. "Tamil"
    transcript: str = ""          # verbatim, in the language/script actually spoken
    translation: str = ""         # English. Equal to `transcript` when already English.
    lot_or_line: str = ""         # whatever lot or line reference was said, as said
    observations: list[str] = Field(default_factory=list)
    maintenance_mentions: list[str] = Field(default_factory=list)
    # Half-heard or inferred fields a human must confirm before relying on them -- same
    # convention as TravelerRow.low_confidence_fields. A half-heard lot number must be
    # flagged here, not silently guessed (CR #12).
    low_confidence_fields: list[str] = Field(default_factory=list)

    @field_validator("language", "language_name", "transcript", "translation",
                      "lot_or_line", mode="before")
    @classmethod
    def _blank_out_nullish_text(cls, v):
        if v is None:
            return ""
        if isinstance(v, str) and v.strip().lower() in _NULLISH_TEXT:
            return ""
        return v


class CapaRecord(BaseModel):
    """One row of `GET /api/capas` -- a corrective action created by a live approval
    (agent/agents/actions.py's apply_approval) or the seeded historical CAPA-0098
    (agent/tools/capa_check.seed_historical_capa). `defect_type`/`line`/`memory_id`
    are filled in from the quality-memory entry this CAPA produced (matched by
    `capa_id`, same linkage agent/tools/memory.save_quality_memory writes) -- a CAPA
    record itself carries no defect_type/line of its own. `effectiveness` is populated
    (agent/tools/dashboard.list_capas_with_effectiveness) only when both are known;
    computed by the SAME rule as every other verdict in this product
    (agent/tools/capa_check.verify_capa_effectiveness), never guessed."""
    id: str
    investigation_id: str = ""
    complaint_id: str = ""
    lot_id: str = ""
    root_cause: str = ""
    owner: str = ""
    opened: str = ""
    status: str = "open"
    summary: str = ""
    approver: str = ""
    note: str = ""
    defect_type: str = ""
    line: str = ""
    memory_id: str = ""
    effectiveness: CapaEffectiveness | None = None


class FirstPassYield(BaseModel):
    units: int
    defects: int
    pct: float


class OpenEightDs(BaseModel):
    count: int
    soonest_due_working_days: int | None = None


class CapaDashboardSummary(BaseModel):
    """CAPA-effectiveness, rolled up for the dashboard tile -- PRD's own cynical
    question made literal: not "how many CAPAs are open" alone, but "of the ones we
    can actually judge, how many came back". `recurrence_rate` is `None` until at
    least one CAPA has a determinate verdict (not `insufficient_data`) -- never a
    fabricated 0%."""
    open: int
    recurrence_rate: float | None = None
    n_evaluated: int = 0


class DefectRateByLinePoint(BaseModel):
    lot_id: str
    date: str
    rate_pct: float


class DefectRateByLine(BaseModel):
    """The dashboard's hero chart: defect rate by lot, Line 1 vs Line 2, with a
    marker at the work order that planted the drift (data/constants.WO388_ID).
    `rate_pct` and the two averages are already *100 (a percentage), not a fraction."""
    line1: list[DefectRateByLinePoint] = Field(default_factory=list)
    line2: list[DefectRateByLinePoint] = Field(default_factory=list)
    line1_avg_pct: float
    line2_avg_pct: float
    marker_date: str
    marker_label: str


class DefectPareto(BaseModel):
    solder_bridge: int
    other: int


class SpcPoint(BaseModel):
    lot_id: str
    date: str
    value: float


class SpcReflowPeak(BaseModel):
    limit_c: float
    points: list[SpcPoint] = Field(default_factory=list)


class DashboardCharts(BaseModel):
    defect_rate_by_line: DefectRateByLine
    defect_pareto: DefectPareto
    spc_reflow_peak: SpcReflowPeak


class DashboardSummary(BaseModel):
    """`GET /api/dashboard/summary` -- every number on it computed live from the same
    plant/state data every other endpoint reads (agent/tools/dashboard.py), never
    hard-coded: this dataset's numbers are planted facts of data/generate_plant.py's
    synthetic scenario, not constants, and must stay live if the seed ever changes."""
    first_pass_yield: FirstPassYield
    open_eight_ds: OpenEightDs
    capas: CapaDashboardSummary
    lots_on_hold: int
    charts: DashboardCharts


class PlantLot(BaseModel):
    """One row of `GET /api/plant/lots` -- lots.csv joined to process.csv (the same
    join agent/tools/plant_data.joined() performs), the full per-lot receipts behind
    the dashboard's yield/Pareto/SPC tiles. Deliberately includes `operator_id` and
    `shift` (this is raw plant data, the same columns a real MES would show) but the
    Plant screen must never render an aggregate "defects by operator/shift" view --
    the product's own rule that operator error is never a root cause (ENGINEERING_RULES.md)."""
    lot_id: str
    line: str
    shift: str
    date: str
    product: str
    qty: int
    paste_lot: str
    stencil_id: str
    operator_id: str
    defects_solder_bridge: int
    defects_other: int
    bridge_rate: float
    ship_status: str
    reflow_peak_temp_c: float
    time_above_liquidus_s: float
    preheat_ramp_c_per_s: float
    soak_time_s: float
    conveyor_speed_cm_min: float
    paste_age_h: float
    room_humidity_pct: float
    stencil_print_count: float
    squeegee_pressure_kg: float


class MaintenanceEvent(BaseModel):
    wo_id: str
    line: str
    date: str
    asset: str
    description: str
    status: str
    post_check: str


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
    # CR #12: the shift lead's voice note, if one was uploaded. None when no voice_note
    # was attached to POST /investigations -- the UI must treat absence as "not
    # provided", not as an empty/failed extraction.
    voice_note: VoiceNote | None = None
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
