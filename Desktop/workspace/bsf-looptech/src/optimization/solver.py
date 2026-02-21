"""PuLP-based cost optimization solver for waste treatment formulations.

Minimizes total material cost subject to:
- Minimum solidifier requirement (from rules + severity)
- Minimum suppressant requirement (if metals exceed limits)
- Material addition rate ranges (from DB)
- Optional budget constraint
"""

import logging
import time
from typing import Any, Dict, List, Optional

import pulp

from src.ml.schemas import CostBreakdown, OptimizationRequest, OptimizationResponse
from src.optimization.constraints import (
    add_budget_constraint,
    add_solidifier_constraint,
    add_suppressant_constraint,
    calc_min_solidifier,
    calc_min_suppressant,
    needs_suppressant,
)

logger = logging.getLogger(__name__)

# Default costs (JPY/kg) when DB records have no unit_cost
DEFAULT_SOLIDIFIER_COST = 15.0
DEFAULT_SUPPRESSANT_COST = 50.0


def _safe_name(name: str) -> str:
    """Make a PuLP-safe variable name from Japanese material names."""
    return "".join(c if c.isalnum() or c == "_" else "" for c in name)


class FormulationOptimizer:
    """Linear programming optimizer for waste treatment formulations."""

    def optimize(
        self,
        request: OptimizationRequest,
        solidifiers: List[Dict[str, Any]],
        suppressants: List[Dict[str, Any]],
    ) -> OptimizationResponse:
        """Find minimum-cost formulation satisfying treatment constraints."""
        start = time.time()
        reasoning: List[str] = []

        # Calculate requirements
        min_sol = calc_min_solidifier(request.analysis, request.waste_type)
        min_sup = calc_min_suppressant(request.analysis)
        need_sup = needs_suppressant(request.analysis)

        reasoning.append(f"最低固化材量: {min_sol:.1f} kg/t")
        if need_sup:
            reasoning.append(f"最低溶出抑制剤量: {min_sup:.1f} kg/t")

        # Provide defaults if no candidates
        if not solidifiers:
            solidifiers = [{
                "name": "普通ポルトランドセメント",
                "unit_cost": DEFAULT_SOLIDIFIER_COST,
                "min_addition_rate": 50,
                "max_addition_rate": 500,
                "unit": "kg",
            }]
        if not suppressants and need_sup:
            suppressants = [{
                "name": "キレート剤A",
                "unit_cost": DEFAULT_SUPPRESSANT_COST,
                "min_addition_rate": 0.5,
                "max_addition_rate": 20,
                "unit": "kg",
            }]

        # Build LP problem
        prob = pulp.LpProblem("FormulationCost", pulp.LpMinimize)

        # Decision variables: amount of each material (total kg)
        sol_vars: Dict[str, pulp.LpVariable] = {}
        for s in solidifiers:
            lo = (s.get("min_addition_rate") or 0) * request.waste_weight
            hi = (s.get("max_addition_rate") or 500) * request.waste_weight
            sol_vars[s["name"]] = pulp.LpVariable(
                f"sol_{_safe_name(s['name'])}", lowBound=lo, upBound=hi,
            )

        sup_vars: Dict[str, pulp.LpVariable] = {}
        for s in suppressants:
            lo = 0  # suppressant can be zero if not needed
            hi = (s.get("max_addition_rate") or 20) * request.waste_weight
            sup_vars[s["name"]] = pulp.LpVariable(
                f"sup_{_safe_name(s['name'])}", lowBound=lo, upBound=hi,
            )

        # Objective: minimize total cost
        cost_terms = []
        for s in solidifiers:
            uc = s.get("unit_cost") or DEFAULT_SOLIDIFIER_COST
            cost_terms.append(uc * sol_vars[s["name"]])
        for s in suppressants:
            uc = s.get("unit_cost") or DEFAULT_SUPPRESSANT_COST
            cost_terms.append(uc * sup_vars[s["name"]])

        if not cost_terms:
            elapsed = (time.time() - start) * 1000
            return OptimizationResponse(
                status="error",
                reasoning=["候補材料がありません"],
                solver_time_ms=round(elapsed, 1),
            )

        prob += pulp.lpSum(cost_terms), "TotalCost"

        # Add constraints
        constraints_info: Dict[str, Any] = {}
        constraints_info.update(
            add_solidifier_constraint(prob, sol_vars, min_sol, request.waste_weight)
        )
        if need_sup:
            constraints_info.update(
                add_suppressant_constraint(prob, sup_vars, min_sup, request.waste_weight)
            )
        if request.max_budget:
            constraints_info.update(
                add_budget_constraint(prob, cost_terms, request.max_budget)
            )

        # Solve
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        elapsed = (time.time() - start) * 1000

        if prob.status != pulp.constants.LpStatusOptimal:
            reasoning.append("最適解が見つかりませんでした")
            if request.max_budget:
                reasoning.append(
                    f"予算制約 ¥{request.max_budget:,.0f} が厳しい可能性があります"
                )
            return OptimizationResponse(
                status="infeasible",
                reasoning=reasoning,
                constraints_satisfied=constraints_info,
                solver_time_ms=round(elapsed, 1),
            )

        # Build result
        recommendation: Dict[str, Any] = {}
        cost_breakdown: List[CostBreakdown] = []
        total_cost = 0.0

        for s in solidifiers:
            val = sol_vars[s["name"]].varValue or 0
            if val > 0.01:
                uc = s.get("unit_cost") or DEFAULT_SOLIDIFIER_COST
                cost = uc * val
                total_cost += cost
                recommendation["solidifierType"] = s["name"]
                recommendation["solidifierAmount"] = round(val / request.waste_weight, 1)
                recommendation["solidifierUnit"] = "kg/t"
                cost_breakdown.append(CostBreakdown(
                    material_name=s["name"],
                    material_type="solidifier",
                    amount=round(val, 1),
                    unit=s.get("unit", "kg"),
                    unit_cost=uc,
                    total_cost=round(cost, 0),
                ))

        for s in suppressants:
            val = sup_vars[s["name"]].varValue or 0
            if val > 0.01:
                uc = s.get("unit_cost") or DEFAULT_SUPPRESSANT_COST
                cost = uc * val
                total_cost += cost
                recommendation["suppressorType"] = s["name"]
                recommendation["suppressorAmount"] = round(val / request.waste_weight, 1)
                recommendation["suppressorUnit"] = "kg/t"
                cost_breakdown.append(CostBreakdown(
                    material_name=s["name"],
                    material_type="suppressant",
                    amount=round(val, 1),
                    unit=s.get("unit", "kg"),
                    unit_cost=uc,
                    total_cost=round(cost, 0),
                ))

        reasoning.append(f"最適解: 総コスト ¥{total_cost:,.0f}")
        reasoning.append(f"ソルバー時間: {elapsed:.1f}ms")

        if request.max_budget:
            constraints_info["within_budget"] = total_cost <= request.max_budget

        return OptimizationResponse(
            status="optimal",
            recommendation=recommendation,
            total_cost=round(total_cost, 0),
            cost_breakdown=cost_breakdown,
            constraints_satisfied=constraints_info,
            solver_time_ms=round(elapsed, 1),
            reasoning=reasoning,
        )
