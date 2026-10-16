"""test_hypothesis — PRD 9.3. No LLM inside this file.

Comparison groups
  parameter hypothesis : defect lots vs good lots, same product, last 30 days  -> Welch t-test
  event hypothesis     : same line, lots before vs after the event date        -> Welch t-test
  categorical (operator): share of that operator in defect vs good lots        -> Fisher exact
"""
import pandas as pd
from scipy import stats

from agent.models import Direction, HypothesisResult
from agent.tools.charts import render_reflow_chart
from agent.tools.plant_data import (NUMERIC_PARAMS, get_comparison_groups,
                                    get_maintenance_events, joined)
from agent.tools.stats_verdict import classify
from data.constants import CATEGORICAL_PARAMS, MIN_EFFECT, PARAM_LABELS, PARAM_UNITS

DEFAULT_EVENT_PARAM = "reflow_peak_temp_c"


def _fmt(value: float, unit: str) -> str:
    digits = 0 if abs(value) >= 1000 else (2 if abs(value) < 1 else 1)
    return f"{value:+,.{digits}f} {unit}"


def _numeric(df_a: pd.DataFrame, df_b: pd.DataFrame, param: str, direction: Direction,
             labels: list[str], hypothesis_id: str, chart_url: str | None) -> HypothesisResult:
    a, b = df_a[param].astype(float), df_b[param].astype(float)
    _, p = stats.ttest_ind(a, b, equal_var=False)
    effect = float(a.mean() - b.mean())
    unit = PARAM_UNITS[param]
    return HypothesisResult(
        hypothesis_id=hypothesis_id,
        verdict=classify(float(p), effect, direction, MIN_EFFECT[param]),
        test="Welch t-test", p_value=round(float(p), 6),
        effect=f"{_fmt(effect, unit)} mean {PARAM_LABELS.get(param, param.replace('_', ' '))}",
        effect_value=round(effect, 3), effect_unit=unit,
        n_defect=int(len(a)), n_good=int(len(b)),
        group_labels=labels, chart_url=chart_url)


def _categorical(df: pd.DataFrame, defect_ids: list[str], good_ids: list[str], param: str,
                 direction: Direction, hypothesis_id: str) -> HypothesisResult:
    # Scoped to defect lots vs good lots (same product, last 30 days), mirroring the
    # numeric path. Unscoped would silently compare against lots outside that window
    # or a different product once either exists — inert today only because this
    # dataset has one product inside one 30-day window.
    scope = df[df.lot_id.isin(defect_ids + good_ids)]
    is_defect = scope.lot_id.isin(defect_ids)
    # The level most over-represented among the defect lots is the one being accused.
    level = scope[is_defect][param].value_counts().idxmax()
    table = pd.crosstab(scope[param] == level, is_defect)
    # Reindex so a missing cell becomes 0 rather than a KeyError.
    table = table.reindex(index=[False, True], columns=[False, True], fill_value=0)
    _, p = stats.fisher_exact(table.values)
    share_defect = float((scope[is_defect][param] == level).mean())
    share_good = float((scope[~is_defect][param] == level).mean())
    effect = share_defect - share_good
    return HypothesisResult(
        hypothesis_id=hypothesis_id,
        verdict=classify(float(p), effect, direction, MIN_EFFECT.get(param, 0.15)),
        test="Fisher exact", p_value=round(float(p), 6),
        effect=f"{effect:+.2f} share of {level} lots "
               f"({share_defect:.0%} of defect lots vs {share_good:.0%} of good lots)",
        effect_value=round(effect, 3), effect_unit="share of lots",
        n_defect=int(is_defect.sum()), n_good=int((~is_defect).sum()),
        group_labels=[f"{level} lots", "other lots"], chart_url=None)


def test_hypothesis(hypothesis_id: str, lot_id: str, parameter: str | None = None,
                    event_wo_id: str | None = None,
                    direction: Direction = "any") -> HypothesisResult:
    if not parameter and not event_wo_id:
        raise ValueError("a hypothesis needs one measurable parameter or event")
    if parameter and parameter not in PARAM_UNITS:
        raise ValueError(f"{parameter!r} is not a testable parameter. "
                         f"Choose one of: {', '.join(sorted(PARAM_UNITS))}")

    df = joined()
    groups = get_comparison_groups(lot_id)
    defect_ids = groups["defect_lots"]

    if event_wo_id:
        param = parameter if parameter in NUMERIC_PARAMS else DEFAULT_EVENT_PARAM
        wo = next((e for e in get_maintenance_events(df[df.lot_id == lot_id].line.iloc[0])
                   if e["wo_id"] == event_wo_id), None)
        if wo is None:
            raise ValueError(f"no maintenance event {event_wo_id} on this line")
        when, line = pd.Timestamp(wo["date"]), wo["line"]
        same_line = df[df.line == line]
        after, before = same_line[same_line.date > when], same_line[same_line.date <= when]
        if len(after) < 2 or len(before) < 2:
            raise ValueError(f"not enough lots either side of {event_wo_id} to test")
        chart = render_reflow_chart(defect_ids, wo["date"], f"{event_wo_id} maintenance")
        return _numeric(after, before, param, direction,
                        [f"Line {line[-1]} after {event_wo_id}",
                         f"Line {line[-1]} before {event_wo_id}"],
                        hypothesis_id, chart)

    if parameter in CATEGORICAL_PARAMS:
        return _categorical(df, defect_ids, groups["good_lots"], parameter, direction,
                            hypothesis_id)

    defect_df = df[df.lot_id.isin(defect_ids)]
    good_df = df[df.lot_id.isin(groups["good_lots"])]
    chart = render_reflow_chart(defect_ids) if parameter == DEFAULT_EVENT_PARAM else None
    return _numeric(defect_df, good_df, parameter, direction,
                    ["Defect lots", "Good lots (same product, 30 days)"],
                    hypothesis_id, chart)
