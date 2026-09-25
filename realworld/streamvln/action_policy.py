"""Scalar robot action policy retained for client compatibility.

No Habitat, model, or torch imports: the robot client only needs scalar budgets;
logit extraction uses tensors supplied by the inference server.
"""

import math
from typing import Optional, Sequence

ATOMIC_ACTION_NAMES = ("stop", "forward", "left", "right")
STOP_ACTION_ID = 0
DEFAULT_REPLAN_ACTION_RANGE = (4, 8)
DEFAULT_STOP_COMMIT_MAX_ACTIONS = 12
DEFAULT_UNCERTAINTY_BUDGET = 1.2


def validate_action_count(value):
    if isinstance(value, bool):
        raise ValueError("action count must be a positive integer")
    value = int(value)
    if value <= 0:
        raise ValueError("action count must be a positive integer")
    return value


def validate_uncertainty_budget(value):
    budget = float(value)
    if not math.isfinite(budget) or budget <= 0:
        raise ValueError("uncertainty-budget must be finite and positive")
    return budget


def validate_replan_action_range(action_range):
    if not isinstance(action_range, (tuple, list)) or len(action_range) != 2:
        raise ValueError("replan-action-range requires two positive integers: MIN MAX")
    minimum, maximum = map(validate_action_count, action_range)
    if minimum > maximum:
        raise ValueError("replan-action-range requires MIN <= MAX")
    return minimum, maximum


def validate_stop_commit_max_actions(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("stop-commit-max-actions must be a nonnegative integer (0 disables)")
    return value


def select_stop_commit_horizon(
    action_ids: Sequence[int],
    stop_commit_max_actions: int = DEFAULT_STOP_COMMIT_MAX_ACTIONS,
) -> Optional[int]:
    """Commit through the first STOP in the inclusive window, counting STOP itself."""
    limit = validate_stop_commit_max_actions(stop_commit_max_actions)
    for position, action_id in enumerate(action_ids[:limit], start=1):
        if action_id == STOP_ACTION_ID:
            return position
    return None


def select_uncertainty_horizon(
    action_uncertainties, budget, action_range=DEFAULT_REPLAN_ACTION_RANGE,
):
    """Longest prefix within action_range with sum(-log p(action)) <= budget.

    The lower bound is the minimum nominal K, even if it exceeds the budget.
    STOP and short predictions are subsequently handled by the action queue.
    This is model uncertainty, not a calibrated probability of execution error.
    """
    budget = validate_uncertainty_budget(budget)
    minimum, maximum = validate_replan_action_range(action_range)
    horizon, cumulative = minimum, 0.0
    for position, uncertainty in enumerate(action_uncertainties[:maximum], start=1):
        if not math.isfinite(uncertainty) or uncertainty < 0:
            raise ValueError("Action uncertainty must be finite and nonnegative")
        cumulative += uncertainty
        if cumulative > budget:
            break
        horizon = max(minimum, position)
    return horizon
