"""
Fixed-Charge Network Flow Solver (beasleyC1, gurobipy)

Reads data/*.csv, uses gurobipy to build and solve MILP, to verify data usability
and consistency with optimal_value in instance.json.

Model (essential structure aligned with beasleyC*.mps):
- Variables: x_a >= 0 (arc flow), y_a in {0,1} (whether arc is open)
- Objective: min sum fixed_cost_a * y_a
- Constraints:
  - For each arc: x_a <= capacity_per_arc * y_a
  - For each node: sum_out x - sum_in x == flow_balance(node)
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Cannot import gurobipy: {type(e).__name__}: {e}")


@dataclass(frozen=True)
class Arc:
    arc_id: str
    start_node: str
    end_node: str


def _read_kv_csv(path: Path) -> Dict[str, float]:
    out: Dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[row["parameter"]] = float(row["value"])
    return out


def _read_arcs(path: Path) -> List[Arc]:
    arcs: List[Arc] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            arcs.append(Arc(row["arc_id"], row["start_node"], row["end_node"]))
    return arcs


def _read_costs(path: Path) -> Tuple[Dict[str, float], Dict[str, str], Dict[str, str]]:
    fixed_cost: Dict[str, float] = {}
    x_name: Dict[str, str] = {}
    y_name: Dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            arc_id = row["arc_id"]
            fixed_cost[arc_id] = float(row["fixed_cost"])
            x_name[arc_id] = row.get("x_var", f"flow_{arc_id}")
            y_name[arc_id] = row.get("y_var", f"open_{arc_id}")
    return fixed_cost, x_name, y_name


def _read_flow_balance(path: Path) -> Dict[str, float]:
    fb: Dict[str, float] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fb[row["node_id"]] = float(row["flow_balance"])
    return fb


def solve(data_dir: Path, *, time_limit_sec: int | None, mip_gap: float | None, threads: int | None):
    params = _read_kv_csv(data_dir / "parameter.csv")
    arcs = _read_arcs(data_dir / "arcs.csv")
    fixed_cost, x_name, y_name = _read_costs(data_dir / "costs.csv")
    flow_balance = _read_flow_balance(data_dir / "flow_balance.csv")

    capacity = float(params["capacity_per_arc"])
    if abs(sum(flow_balance.values())) > 1e-9:
        raise ValueError("Sum of flow_balance is not 0, model will be infeasible.")

    nodes = sorted(flow_balance.keys())
    out_arcs: Dict[str, List[str]] = {n: [] for n in nodes}
    in_arcs: Dict[str, List[str]] = {n: [] for n in nodes}
    for a in arcs:
        if a.start_node in out_arcs:
            out_arcs[a.start_node].append(a.arc_id)
        if a.end_node in in_arcs:
            in_arcs[a.end_node].append(a.arc_id)

    m = gp.Model("FixedChargeNetworkFlow")
    m.ModelSense = GRB.MINIMIZE

    if time_limit_sec is not None:
        m.Params.TimeLimit = time_limit_sec
    if mip_gap is not None:
        m.Params.MIPGap = mip_gap
    if threads is not None:
        m.Params.Threads = threads

    x = {
        a.arc_id: m.addVar(lb=0.0, ub=capacity, vtype=GRB.CONTINUOUS, name=x_name[a.arc_id])
        for a in arcs
    }
    y = {a.arc_id: m.addVar(vtype=GRB.BINARY, name=y_name[a.arc_id]) for a in arcs}

    m.setObjective(gp.quicksum(fixed_cost[a.arc_id] * y[a.arc_id] for a in arcs))

    for a in arcs:
        m.addConstr(x[a.arc_id] <= capacity * y[a.arc_id], name=f"cap_{a.arc_id}")

    for n in nodes:
        m.addConstr(
            gp.quicksum(x[aid] for aid in out_arcs[n]) - gp.quicksum(x[aid] for aid in in_arcs[n])
            == flow_balance[n],
            name=f"balance_{n}",
        )

    m.optimize()

    status = int(m.Status)
    obj = float(m.ObjVal) if status in (GRB.OPTIMAL, GRB.SUBOPTIMAL) else None
    return status, obj


def main():
    ap = argparse.ArgumentParser(description="Solve beasleyC1 using gurobipy from data/*.csv.")
    ap.add_argument("data_dir", nargs="?", default="data", help="Data directory (default: data)")
    ap.add_argument("--time-limit", type=int, default=300)
    ap.add_argument("--mip-gap", type=float, default=None)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--check", action="store_true", help="Compare objective with instance.json optimal_value")
    args = ap.parse_args()

    instance_dir = Path(__file__).resolve().parent
    data_dir = (instance_dir / args.data_dir).resolve()

    status, obj = solve(
        data_dir,
        time_limit_sec=args.time_limit if args.time_limit and args.time_limit > 0 else None,
        mip_gap=args.mip_gap,
        threads=args.threads,
    )
    print(f"status: {status}")
    print(f"objective: {obj}")

    if args.check:
        inst = json.load((instance_dir / "instance.json").open("r", encoding="utf-8"))
        target = inst.get("optimal_value", None)
        if target is None:
            raise SystemExit("No optimal_value in instance.json, cannot compare.")
        tol = 1e-6
        ok = obj is not None and abs(float(obj) - float(target)) <= tol
        print(f"optimal_value (instance.json): {target}")
        print(f"match (tol={tol}): {ok}")
        if not ok:
            raise SystemExit(2)


if __name__ == "__main__":
    main()