"""verify_capa_effectiveness -- did a confirmed corrective action actually reduce the
defect rate? PRD: a quality system is judged by recurrence, not by how many CAPAs it
opens and closes -- "the root cause becomes operator error, the 8D gets sent back, and
the same defect returns next quarter." Nobody checks whether the CAPA that closed the
LAST occurrence actually worked. This file does, with no LLM involved: every verdict
here comes from the SAME rule as every other verdict in this product
(agent/tools/stats_verdict.classify) -- a second, bespoke statistical rule would be
exactly the kind of inconsistency that erodes trust in the first one.

Three-window split, chosen so a drop that FADED is told apart from one that HELD:
  before      lots up to and including `implemented_on`
  immediate   the first half of the lots after `implemented_on`, chronologically
  recent      the second half (the odd lot out, if the after-period has an odd count,
              goes to `recent` -- a bit more evidence on whether the improvement held
              matters more here than a bit more confidence that it started)

Welch t-test on the per-lot defect rate, direction="lower" (an effective CAPA makes the
rate go DOWN -- a rate that rose is never "worked", however significant the p-value),
same classify() thresholds as every hypothesis test. `min_effect` reuses
DEFECT_RATE_THRESHOLD (data/constants.py): the same number the rest of the product
already uses to call a lot "defective", so a CAPA is not held to some new, invented
magnitude of improvement -- it must move the average rate by at least as much as the
threshold that already defines a bad lot.

Decision tree:
  len(before) < MIN_GROUP or len(immediate) < MIN_GROUP or len(recent) < MIN_GROUP
      -> insufficient_data (never guess with too little evidence on one side)
  classify(immediate vs before, "lower") != "supported"
      -> never_worked (no significant, meaningful drop right after the fix -- including
         the case where the rate significantly ROSE: classify() rejects a rise under
         direction="lower" however small the p-value, and a rise is certainly not a
         working CAPA)
  classify(immediate vs before, "lower") == "supported"
  and classify(recent vs before, "lower") == "supported"
      -> worked (dropped, and stayed down)
  classify(immediate vs before, "lower") == "supported"
  and classify(recent vs before, "lower") != "supported"
      -> regressed (dropped, then climbed back toward baseline)
"""
import pandas as pd
from scipy import stats

from agent.models import CapaEffectiveness, CapaVerdict
from agent.tools.plant_data import get_capa_defect_series
from agent.tools.stats_verdict import classify
from data.constants import DEFECT_RATE_THRESHOLD

MIN_GROUP = 3                       # fewest lots required in EACH of before/immediate/recent
MIN_EFFECT = DEFECT_RATE_THRESHOLD  # see module docstring: not a new, invented magnitude


def _welch(after: pd.Series, before: pd.Series) -> tuple[float, float]:
    _, p = stats.ttest_ind(after.astype(float), before.astype(float), equal_var=False)
    return float(p), float(after.mean() - before.mean())


def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def verify_capa_effectiveness(capa_id: str, defect_type: str, line: str,
                              implemented_on: str) -> CapaEffectiveness:
    when = pd.Timestamp(implemented_on)
    series = get_capa_defect_series(capa_id, line, defect_type)
    before = series[series.date <= when]
    after = series[series.date > when].sort_values("date")
    half = len(after) // 2
    immediate = after.iloc[:len(after) - half]
    recent = after.iloc[len(after) - half:]

    n_before, n_immediate, n_recent = len(before), len(immediate), len(recent)
    group_labels = [f"Before {capa_id} (implemented {implemented_on})",
                    f"Immediately after {capa_id}", f"Recent, after {capa_id}"]

    if n_before < MIN_GROUP or n_immediate < MIN_GROUP or n_recent < MIN_GROUP:
        return CapaEffectiveness(
            capa_id=capa_id, defect_type=defect_type, line=line,
            implemented_on=implemented_on, verdict="insufficient_data",
            effect=(f"only {n_before} lot(s) before, {n_immediate} immediately after and "
                   f"{n_recent} recent lot(s) of {capa_id} on {line} -- too few to test"),
            n_before=n_before, n_immediate=n_immediate, n_recent=n_recent,
            group_labels=group_labels)

    before_rate = float(before["rate"].mean())
    immediate_rate = float(immediate["rate"].mean())
    recent_rate = float(recent["rate"].mean())
    p_immediate, effect_immediate = _welch(immediate["rate"], before["rate"])
    p_recent, effect_recent = _welch(recent["rate"], before["rate"])
    verdict_immediate = classify(p_immediate, effect_immediate, "lower", MIN_EFFECT)
    verdict_recent = classify(p_recent, effect_recent, "lower", MIN_EFFECT)

    verdict: CapaVerdict
    if verdict_immediate != "supported":
        verdict = "never_worked"
        p_value, effect_value = p_immediate, effect_immediate
        effect = (f"{_pct(immediate_rate)} right after {capa_id}, barely moved from "
                 f"{_pct(before_rate)} before it (p={p_immediate:.4f}) -- signed off, "
                 f"never actually fixed")
    elif verdict_recent == "supported":
        verdict = "worked"
        p_value, effect_value = p_recent, effect_recent
        effect = (f"{_pct(before_rate)} before {capa_id} -> {_pct(recent_rate)} recently "
                 f"(p={p_recent:.4f}), still down")
    else:
        verdict = "regressed"
        p_value, effect_value = p_recent, effect_recent
        effect = (f"{_pct(before_rate)} before {capa_id} -> {_pct(immediate_rate)} right "
                 f"after, back up to {_pct(recent_rate)} recently (p={p_recent:.4f} vs "
                 f"before) -- it worked, then stopped")

    return CapaEffectiveness(
        capa_id=capa_id, defect_type=defect_type, line=line, implemented_on=implemented_on,
        verdict=verdict, p_value=round(p_value, 6), effect=effect,
        effect_value=round(effect_value, 4), n_before=n_before, n_immediate=n_immediate,
        n_recent=n_recent, group_labels=group_labels, before_rate=round(before_rate, 4),
        immediate_rate=round(immediate_rate, 4), recent_rate=round(recent_rate, 4),
        p_immediate=round(p_immediate, 6), p_recent=round(p_recent, 6))
