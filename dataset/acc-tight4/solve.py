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

    periods = [int(r["period_id"]) for r in _read_csv_dicts(data_dir / "periods.csv")]
    channels = [int(r["channel_id"]) for r in _read_csv_dicts(data_dir / "channels.csv")]

    headline_quota = {
        int(r["channel_id"]): int(r["headline_quota"])
        for r in _read_csv_dicts(data_dir / "headline_quota.csv")
    }
    support_quota = {
        int(r["period_id"]): int(r["support_quota"])
        for r in _read_csv_dicts(data_dir / "support_quota.csv")
    }

    promo_rows = _read_csv_dicts(data_dir / "promo_requirements.csv")
    promo_pairs = [(int(r["sender_channel_id"]), int(r["target_channel_id"])) for r in promo_rows]
    required_promo = {
        (int(r["sender_channel_id"]), int(r["target_channel_id"])): int(r["required_count"])
        for r in promo_rows
    }

    parity_rows = _read_csv_dicts(data_dir / "parity_quota.csv")
    parity_quota: dict[tuple[int, str], int] = {}
    for r in parity_rows:
        parity_quota[(int(r["channel_id"]), r["action_family"])] = int(r["required_count"])

    link_pairs = [
        (int(r["src_period_id"]), int(r["dst_period_id"]))
        for r in _read_csv_dicts(data_dir / "time_link_pairs.csv")
    ]

    penalty = {
        (int(r["period_id"]), int(r["channel_id"])): float(r["penalty_weight"])
        for r in _read_csv_dicts(data_dir / "penalized_headline.csv")
    }
    cadence_rules = _read_csv_dicts(data_dir / "cadence_rules.csv")

    outgoing_targets: dict[int, list[int]] = {j: [] for j in channels}
    incoming_senders: dict[int, list[int]] = {u: [] for u in channels}
    for sender, target in promo_pairs:
        outgoing_targets[sender].append(target)
        incoming_senders[target].append(sender)

    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model(f"acc_tight4_{instance_dir.name}")
    model.Params.OutputFlag = 0
    model.ModelSense = GRB.MINIMIZE

    A = model.addVars(periods, channels, vtype=GRB.INTEGER, lb=0.0, ub=1.0, name="headline")
    B = model.addVars(periods, channels, vtype=GRB.INTEGER, lb=0.0, ub=1.0, name="host")
    P = model.addVars(periods, promo_pairs, vtype=GRB.INTEGER, lb=0.0, ub=1.0, name="promo")

    model.setObjective(
        gp.quicksum(penalty.get((t, j), 0.0) * A[t, j] for t in periods for j in channels)
    )

    for t in periods:
        model.addConstr(gp.quicksum(A[t, j] for j in channels) == 1.0)

    for j in channels:
        model.addConstr(gp.quicksum(A[t, j] for t in periods) == float(headline_quota[j]))

    for t in periods:
        model.addConstr(gp.quicksum(B[t, j] for j in channels) == float(support_quota[t]))

    for t in periods:
        for j in channels:
            model.addConstr(
                A[t, j] + B[t, j] + gp.quicksum(P[t, j, u] for u in outgoing_targets[j]) == 1.0
            )

    for t in periods:
        for (j, u) in promo_pairs:
            model.addConstr(B[t, u] - P[t, j, u] >= 0.0)

    for (j, u) in promo_pairs:
        model.addConstr(gp.quicksum(P[t, j, u] for t in periods) == float(required_promo[(j, u)]))

    for t in periods:
        for u in channels:
            model.addConstr(gp.quicksum(P[t, j, u] for j in incoming_senders[u]) <= 1.0)

    even_periods = [t for t in periods if t % 2 == 0]
    for j in channels:
        model.addConstr(gp.quicksum(A[t, j] for t in even_periods) == float(parity_quota[(j, "headline")]))
        model.addConstr(gp.quicksum(B[t, j] for t in even_periods) == float(parity_quota[(j, "host")]))

    for src_t, dst_t in link_pairs:
        for j in channels:
            model.addConstr(A[src_t, j] <= A[dst_t, j])
        for sender in channels:
            for target in outgoing_targets[sender]:
                model.addConstr(P[src_t, sender, target] <= P[dst_t, target, sender])

    for r in cadence_rules:
        target = r["target"]
        sense = r["sense"]
        j = int(r["channel_id"])
        start = int(r["start_period"])
        step = int(r["step"])
        length = int(r["length"])
        rhs = float(r["rhs"])

        idxs = [start + step * s for s in range(length)]
        if any(t not in periods for t in idxs):
            raise SystemExit(f"Invalid cadence rule window: {r}")

        if target == "B":
            expr = gp.quicksum(B[t, j] for t in idxs)
        elif target == "AB":
            expr = gp.quicksum(A[t, j] + B[t, j] for t in idxs)
        elif target == "Csum":
            expr = gp.quicksum(P[t, j, u] for t in idxs for u in outgoing_targets[j])
        else:
            raise SystemExit(f"Unknown target: {target}")

        if sense == "LE":
            model.addConstr(expr <= rhs)
        elif sense == "GE":
            model.addConstr(expr >= rhs)
        else:
            raise SystemExit(f"Unknown sense: {sense}")

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