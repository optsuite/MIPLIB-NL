from __future__ import annotations

import csv
import json
from pathlib import Path


def _read_csv_dicts(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    instance_dir = Path(__file__).resolve().parent
    data_dir = instance_dir / "data"

    options = _read_csv_dicts(data_dir / "options.csv")
    option_ids = [int(r["option_id"]) for r in options]
    objective_penalty = {int(r["option_id"]): float(r["objective_penalty"]) for r in options}

    groups = [int(r["group_id"]) for r in _read_csv_dicts(data_dir / "choice_groups.csv")]
    group_members = _read_csv_dicts(data_dir / "choice_group_members.csv")

    members_by_group: dict[int, list[int]] = {g: [] for g in groups}
    for r in group_members:
        members_by_group[int(r["group_id"])].append(int(r["option_id"]))

    edges = _read_csv_dicts(data_dir / "implication_edges.csv")
    implications = [(int(r["from_option_id"]), int(r["to_option_id"])) for r in edges]

    cap_groups = _read_csv_dicts(data_dir / "cap_groups.csv")
    cap_meta = {int(r["cap_group_id"]): (r["sense"], float(r["rhs"])) for r in cap_groups}
    cap_members = _read_csv_dicts(data_dir / "cap_group_members.csv")
    members_by_cap: dict[int, list[int]] = {cid: [] for cid in cap_meta}
    for r in cap_members:
        members_by_cap[int(r["cap_group_id"])].append(int(r["option_id"]))

    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model(f"acc_tight5_{instance_dir.name}")
    model.Params.OutputFlag = 0
    model.ModelSense = GRB.MINIMIZE

    x = model.addVars(option_ids, vtype=GRB.INTEGER, lb=0.0, ub=1.0, name="x")

    model.setObjective(gp.quicksum(objective_penalty[i] * x[i] for i in option_ids))

    for g in groups:
        model.addConstr(gp.quicksum(x[i] for i in members_by_group[g]) == 1.0)

    for p, q in implications:
        model.addConstr(x[q] - x[p] >= 0.0)

    for cid, (sense, rhs) in cap_meta.items():
        expr = gp.quicksum(x[i] for i in members_by_cap[cid])
        if sense == "LE":
            model.addConstr(expr <= rhs)
        elif sense == "GE":
            model.addConstr(expr >= rhs)
        elif sense == "EQ":
            model.addConstr(expr == rhs)
        else:
            raise SystemExit(f"Unknown cap-group sense: {sense}")

    model.optimize()
    if model.Status != GRB.OPTIMAL:
        raise SystemExit(f"Not optimal, status={model.Status}")

    value = float(model.ObjVal)
    print(f"Optimal objective value (minimize penalty): {value:.6f}")

    inst_path = instance_dir / "instance.json"
    if inst_path.exists():
        inst = json.loads(inst_path.read_text(encoding="utf-8"))
        if "optimal_value" in inst and inst["optimal_value"] != "":
            expected = float(inst["optimal_value"])
            diff = abs(value - expected)
            if diff <= 1e-6:
                print(f"Consistent with optimal_value in instance.json (diff {diff:.6g})")
            else:
                raise SystemExit(
                    f"Inconsistent with optimal_value in instance.json: {value:.6f} vs {expected:.6f} (diff {diff:.6g})"
                )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())