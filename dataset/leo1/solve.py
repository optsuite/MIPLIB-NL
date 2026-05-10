"""
leo1 solver (current data/*.csv format, gurobipy)

Reads:
- data/options.csv
- data/requirements.csv
- data/option_requirement.csv
- data/resources.csv
- data/resource_usage.csv

Builds model:
min   Σ cost(option) * y_option
s.t.  For each requirement: Σ y_option <= K
      For each resource: Σ contribution(resource, option) * y_option >= minimum_required(resource)
      y_option ∈ {0,1}
Where K comes from instance.json's parameters.max_choices_per_group (default 1).
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Tuple

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception as e:  # pragma: no cover
    raise SystemExit(f"Unable to import gurobipy: {type(e).__name__}: {e}")


def _read_csv_dict(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_data(data_dir: Path) -> Tuple[Dict[int, float], Dict[int, int], Dict[int, float], List[Tuple[int, int, int]]]:
    options = _read_csv_dict(data_dir / "options.csv")
    requirements = _read_csv_dict(data_dir / "requirements.csv")
    option_requirement = _read_csv_dict(data_dir / "option_requirement.csv")
    resources = _read_csv_dict(data_dir / "resources.csv")
    resource_usage = _read_csv_dict(data_dir / "resource_usage.csv")

    costs = {int(r["option_id"]): float(r["unit_cost"]) for r in options}
    req_ids = {int(r["requirement_id"]) for r in requirements}
    opt_to_req = {int(r["option_id"]): int(r["requirement_id"]) for r in option_requirement}
    rhs = {int(r["resource_id"]): float(r["minimum_required"]) for r in resources}
    usage = [(int(r["resource_id"]), int(r["option_id"]), int(float(r["contribution"]))) for r in resource_usage]

    # Basic validation: reference validity
    nopt = len(costs)
    if set(costs.keys()) != set(range(1, nopt + 1)):
        raise ValueError("option_id in options.csv must be consecutive integers starting from 1.")
    if set(opt_to_req.keys()) != set(costs.keys()):
        raise ValueError("option_requirement.csv must cover exactly all option_ids (exactly one row per option).")
    if not req_ids:
        raise ValueError("requirements.csv is empty.")
    if any(gid not in req_ids for gid in opt_to_req.values()):
        raise ValueError("Non-existent requirement_id found in option_requirement.csv.")
    if not rhs:
        raise ValueError("resources.csv is empty.")
    if any((rid not in rhs) for rid, _, _ in usage):
        raise ValueError("Non-existent resource_id found in resource_usage.csv.")
    if any((oid not in costs) for _, oid, _ in usage):
        raise ValueError("Non-existent option_id found in resource_usage.csv.")

    return costs, opt_to_req, rhs, usage


def solve(
    *,
    data_dir: Path,
    k_per_group: int,
    time_limit_sec: int | None,
    mip_gap: float | None,
    threads: int | None,
) -> Tuple[int, float | None]:
    costs, opt_to_req, rhs, usage = load_data(data_dir)

    # build adjacency for constraints
    options_by_req: DefaultDict[int, List[int]] = defaultdict(list)
    for oid, gid in opt_to_req.items():
        options_by_req[gid].append(oid)

    usage_by_res: DefaultDict[int, List[Tuple[int, int]]] = defaultdict(list)
    for rid, oid, a in usage:
        usage_by_res[rid].append((oid, a))

    model = gp.Model("leo1_action_selection")
    model.ModelSense = GRB.MINIMIZE

    if time_limit_sec is not None:
        model.Params.TimeLimit = time_limit_sec
    if mip_gap is not None:
        model.Params.MIPGap = mip_gap
    if threads is not None:
        model.Params.Threads = threads

    y = {oid: model.addVar(vtype=GRB.BINARY, name=f"choose_{oid}") for oid in costs.keys()}

    model.setObjective(gp.quicksum(costs[oid] * y[oid] for oid in costs.keys()))

    for gid, opts in options_by_req.items():
        model.addConstr(gp.quicksum(y[oid] for oid in opts) <= k_per_group, name=f"menu_{gid}")

    for rid, min_req in rhs.items():
        terms = usage_by_res.get(rid, [])
        model.addConstr(gp.quicksum(a * y[oid] for oid, a in terms) >= float(min_req), name=f"target_{rid}")

    model.optimize()

    status = int(model.Status)
    obj = float(model.ObjVal) if model.SolCount and model.SolCount > 0 else None
    return status, obj


def main():
    ap = argparse.ArgumentParser(description="Solve leo1 with gurobipy using the current CSV schema.")
    ap.add_argument("data_dir", nargs="?", default="data", help="Data directory under instances/leo1/ (default: data)")
    ap.add_argument("--K", type=int, default=None, help="Override max choices per group (defaults to instance.json)")
    ap.add_argument("--time-limit", type=int, default=300)
    ap.add_argument("--mip-gap", type=float, default=None)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--check", action="store_true", help="Compare objective with instance.json optimal_value")
    args = ap.parse_args()

    instance_dir = Path(__file__).resolve().parent
    data_dir = (instance_dir / args.data_dir).resolve()

    inst = json.load((instance_dir / "instance.json").open("r", encoding="utf-8"))
    k = int(args.K) if args.K is not None else int(inst["parameters"].get("max_choices_per_group", 1))

    status, obj = solve(
        data_dir=data_dir,
        k_per_group=k,
        time_limit_sec=args.time_limit if args.time_limit and args.time_limit > 0 else None,
        mip_gap=args.mip_gap,
        threads=args.threads,
    )

    print(f"status: {status}")
    print(f"objective: {obj}")

    if args.check:
        target = float(inst.get("optimal_value"))
        tol = 1e-4
        ok = obj is not None and abs(float(obj) - target) <= tol
        print(f"optimal_value (instance.json): {target}")
        print(f"match (tol={tol}): {ok}")
        if not ok:
            raise SystemExit(2)


if __name__ == "__main__":
    main()