"""The verdict rule. PRD 9.3, direction-aware. No LLM inside, no numbers invented.

supported    p < 0.01 AND effect in the hypothesised direction AND |effect| >= min_effect
rejected     p > 0.1  OR  effect in the opposite direction
inconclusive otherwise
"""
from agent.models import Direction, Verdict

P_SUPPORTED = 0.01
P_REJECTED = 0.10


def classify(p_value: float, effect: float, direction: Direction, min_effect: float) -> Verdict:
    if direction == "higher" and effect < 0:
        return "rejected"
    if direction == "lower" and effect > 0:
        return "rejected"
    if p_value > P_REJECTED:
        return "rejected"
    if p_value < P_SUPPORTED and abs(effect) >= min_effect:
        return "supported"
    return "inconclusive"
