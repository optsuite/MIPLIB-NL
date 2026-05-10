"""
Drayage Dispatch Planning - Reference Solver

This solver reads CSV data from instances/drayage-100-23/data, uses Gurobi to reconstruct and solve the model.

Data patterns follow instance.json and drayage-100-23.md:
- One-to-one pairing between orders and chassis (N×M full pairing optional, unlisted cost = baseline cost).
- Timestamp variables are bounded by time_bounds.csv.
- Rule tables use default senses and constants given in problem_structure.csv.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import pandas as pd
import gurobipy as gp
from gurobipy import GRB


@dataclass(frozen=True)
class Defaults:
    baseline_assignment_cost: float
    pair_time_link_default_sense: str
    pair_time_link_big_m: float
    chassis_time_default_sense: str
    chassis_time_default_rhs: float


def _read_problem_structure(path: str) -> Tuple[int, int, int, Defaults]:
    df = pd.read_csv(path)
    kv: Dict[str, str] = {
        str(row["parameter"]): str(row["value"]) for _, row in df.iterrows()
    }

    n = int(kv["N"])
    m = int(kv["M"])
    num_time_vars = int(kv["num_time_vars"])

    defaults = Defaults(
        baseline_assignment_cost=float(kv["baseline_assignment_cost"]),
        pair_time_link_default_sense=str(kv["pair_time_link_default_sense"]),
        pair_time_link_big_m=float(kv["pair_time_link_big_m"]),
        chassis_time_default_sense=str(kv["chassis_time_default_sense"]),
        chassis_time_default_rhs=float(kv["chassis_time_default_rhs"]),
    )
    return n, m, num_time_vars, defaults


def _sense_to_gurobi(sense: str) -> str:
    sense = str(sense).strip().upper()
    if sense == "G":
        return GRB.GREATER_EQUAL
    if sense == "L":
        return GRB.LESS_EQUAL
    if sense == "E":
        return GRB.EQUAL
    raise ValueError(f"Unsupported sense code: {sense!r} (expected 'G','L','E')")


def _add_sense_constr(model: gp.Model, lhs: gp.LinExpr, sense: str, rhs: float, name: str) -> None:
    if sense == GRB.GREATER_EQUAL:
        model.addConstr(lhs >= rhs, name=name)
        return
    if sense == GRB.LESS_EQUAL:
        model.addConstr(lhs <= rhs, name=name)
        return
    if sense == GRB.EQUAL:
        model.addConstr(lhs == rhs, name=name)
        return
    raise ValueError(f"Unsupported Gurobi sense: {sense!r}")


def solve(data_dir: str, time_limit_sec: int, mip_gap: float, output_flag: int) -> Dict:
    problem_structure_path = os.path.join(data_dir, "problem_structure.csv")
    n, m, num_time_vars, defaults = _read_problem_structure(problem_structure_path)

    assignment_costs_df = pd.read_csv(os.path.join(data_dir, "assignment_costs.csv"))
    time_bounds_df = pd.read_csv(os.path.join(data_dir, "time_bounds.csv"))
    pair_rules_df = pd.read_csv(os.path.join(data_dir, "pair_time_link_rules.csv"))
    chassis_rules_df = pd.read_csv(os.path.join(data_dir, "chassis_time_rules.csv"))
    order_groups_df = pd.read_csv(os.path.join(data_dir, "order_groups.csv"))

    orders: List[int] = list(range(n))
    chassis: List[int] = list(range(m))

    # 0-based time ids; prefer explicit bounds file
    time_ids = sorted(time_bounds_df["time_id"].astype(int).unique().tolist())
    if len(time_ids) == 0:
        time_ids = list(range(num_time_vars))

    time_bounds: Dict[int, Tuple[float, float]] = {}
    for row in time_bounds_df.itertuples(index=False):
        time_id = int(row.time_id)
        time_bounds[time_id] = (float(row.lower_bound), float(row.upper_bound))

    # default order group: all order_id listed in order_groups.csv
    group_orders = sorted(order_groups_df["order_id"].astype(int).unique().tolist())

    # sparse explicit costs; missing => baseline
    explicit_cost: Dict[Tuple[int, int], float] = {}
    for row in assignment_costs_df.itertuples(index=False):
        explicit_cost[(int(row.order_id), int(row.chassis_id))] = float(row.cost)

    model = gp.Model("drayage_dispatch")
    model.Params.OutputFlag = int(output_flag)
    model.Params.TimeLimit = int(time_limit_sec)
    model.Params.MIPGap = float(mip_gap)

    x: Dict[Tuple[int, int], gp.Var] = {}
    for order_id in orders:
        for chassis_id in chassis:
            x[(order_id, chassis_id)] = model.addVar(
                vtype=GRB.BINARY, name=f"assign[{order_id},{chassis_id}]"
            )

    t: Dict[int, gp.Var] = {}
    for time_id in time_ids:
        lower, upper = time_bounds.get(time_id, (-GRB.INFINITY, GRB.INFINITY))
        t[time_id] = model.addVar(
            lb=lower, ub=upper, vtype=GRB.CONTINUOUS, name=f"time[{time_id}]"
        )

    # Objective: baseline is constant offset; only explicit entries need to be added
    obj = gp.LinExpr()
    for (order_id, chassis_id), cost in explicit_cost.items():
        if cost == defaults.baseline_assignment_cost:
            continue
        obj.addTerms(cost - defaults.baseline_assignment_cost, x[(order_id, chassis_id)])
    model.setObjective(obj, GRB.MINIMIZE)

    # One-to-one pairing
    for order_id in orders:
        model.addConstr(
            gp.quicksum(x[(order_id, chassis_id)] for chassis_id in chassis) == 1,
            name=f"cover_order[{order_id}]",
        )
    for chassis_id in chassis:
        model.addConstr(
            gp.quicksum(x[(order_id, chassis_id)] for order_id in orders) == 1,
            name=f"use_chassis[{chassis_id}]",
        )

    # Pair-time link rules (sense and big-M are defaults from problem_structure)
    pair_sense = _sense_to_gurobi(defaults.pair_time_link_default_sense)
    big_m = defaults.pair_time_link_big_m
    for idx, row in enumerate(pair_rules_df.itertuples(index=False)):
        constraint_id = f"pair_time_rule[{idx}]"
        rhs = float(row.rhs)
        order_id = int(row.order_id)
        fixed_chassis = int(order_id)  # primary chassis option is the one sharing the same identifier
        alternative_chassis = int(row.chassis_alternative)
        time_from = int(row.time_from)
        time_to = int(row.time_to)
        fixed_coef = float(row.fixed_choice_coefficient)

        expr = (
            (t[time_to] - t[time_from])
            + fixed_coef * x[(order_id, fixed_chassis)]
            - big_m * x[(order_id, alternative_chassis)]
        )
        _add_sense_constr(model, expr, pair_sense, rhs, constraint_id)

    # Chassis-time rules (sense and rhs are defaults from problem_structure)
    chassis_sense = _sense_to_gurobi(defaults.chassis_time_default_sense)
    chassis_rhs = defaults.chassis_time_default_rhs
    for idx, row in enumerate(chassis_rules_df.itertuples(index=False)):
        constraint_id = f"chassis_time_rule[{idx}]"
        chassis_id = int(row.chassis_id)
        time_id = int(row.time_id)
        coef = float(row.assignment_coefficient)

        expr = t[time_id] + coef * gp.quicksum(
            x[(order_id, chassis_id)] for order_id in group_orders
        )
        _add_sense_constr(model, expr, chassis_sense, chassis_rhs, constraint_id)

    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, str(model.Status))

    result: Dict = {
        "status": status,
        "objective_value": None,
        "assignments": {},
        "time": {},
    }
    if model.SolCount > 0:
        # Add back baseline constant to report full objective as-if every chosen pair had baseline
        baseline_offset = defaults.baseline_assignment_cost * n
        result["objective_value"] = float(model.ObjVal + baseline_offset)

        for (order_id, chassis_id), var in x.items():
            if var.X > 0.5:
                result["assignments"][f"{order_id}->{chassis_id}"] = 1
        for time_id, var in t.items():
            result["time"][str(time_id)] = float(var.X)

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", default=os.path.join(os.path.dirname(__file__), "data"))
    parser.add_argument("--time_limit_sec", type=int, default=300)
    parser.add_argument("--mip_gap", type=float, default=1e-4)
    parser.add_argument("--output_flag", type=int, default=1)
    args = parser.parse_args()

    result = solve(args.data_dir, args.time_limit_sec, args.mip_gap, args.output_flag)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()