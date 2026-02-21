"""Constraint builders for PuLP optimization problems.

Each function adds constraints to a PuLP problem in place and returns
a description dict for the response.
"""

import logging
from typing import Any, Dict, List, Optional

import pulp

from src.waste.recommender import (
    ELUTION_LIMITS,
    SOLIDIFIER_RULES,
    DEFAULT_SOLIDIFIER_RULE,
    _severity_score,
)

logger = logging.getLogger(__name__)


def calc_min_solidifier(analysis: Dict[str, Any], waste_type: str) -> float:
    """Calculate minimum solidifier requirement (kg/t) from rules."""
    rules = SOLIDIFIER_RULES.get(waste_type, DEFAULT_SOLIDIFIER_RULE)
    moisture = float(analysis.get("moisture", 50))
    severity = _severity_score(analysis)
    return (
        rules["base"]
        + max(0, moisture - 60) * rules["moisture_factor"]
        + severity * rules["metal_factor"]
    )


def calc_min_suppressant(analysis: Dict[str, Any]) -> float:
    """Calculate minimum suppressant requirement (kg/t). Returns 0 if not needed."""
    severity = _severity_score(analysis)
    cr6 = float(analysis.get("Cr6", 0))
    if severity > 0.5 or cr6 > 0.04:
        return 2.0 + severity * 2.0
    return 0.0


def needs_suppressant(analysis: Dict[str, Any]) -> bool:
    """Whether the waste analysis requires a leaching suppressant."""
    return calc_min_suppressant(analysis) > 0


def add_solidifier_constraint(
    prob: pulp.LpProblem,
    sol_vars: Dict[str, pulp.LpVariable],
    min_amount: float,
    waste_weight: float,
) -> Dict[str, Any]:
    """Add constraint: total solidifier >= min_amount * waste_weight."""
    if sol_vars:
        prob += (
            pulp.lpSum(sol_vars.values()) >= min_amount * waste_weight,
            "MinSolidifier",
        )
    return {"min_solidifier_kg_per_t": round(min_amount, 1)}


def add_suppressant_constraint(
    prob: pulp.LpProblem,
    sup_vars: Dict[str, pulp.LpVariable],
    min_amount: float,
    waste_weight: float,
) -> Dict[str, Any]:
    """Add constraint: total suppressant >= min_amount * waste_weight."""
    if sup_vars and min_amount > 0:
        prob += (
            pulp.lpSum(sup_vars.values()) >= min_amount * waste_weight,
            "MinSuppressant",
        )
    return {"min_suppressant_kg_per_t": round(min_amount, 1)}


def add_budget_constraint(
    prob: pulp.LpProblem,
    cost_terms: List[pulp.LpAffineExpression],
    max_budget: float,
) -> Dict[str, Any]:
    """Add constraint: total cost <= max_budget."""
    prob += pulp.lpSum(cost_terms) <= max_budget, "Budget"
    return {"max_budget": max_budget}
