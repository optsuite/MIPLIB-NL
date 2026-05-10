import argparse
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import gurobipy as gp
import pandas as pd
from gurobipy import GRB


@dataclass(frozen=True)
class InstanceParams:
    unserved_energy_penalty: float
    optimal_value: Optional[float]


def _read_instance_params(instance_json_path: str) -> InstanceParams:
    with open(instance_json_path, "r", encoding="utf-8") as f:
        inst = json.load(f)
    params = inst.get("parameters", {})
    optimal_value = inst.get("optimal_value")
    return InstanceParams(
        unserved_energy_penalty=float(params["unserved_energy_penalty"]),
        optimal_value=float(optimal_value) if optimal_value is not None else None,
    )


def _load_mode_unavailability(unavailability_path: str) -> set[Tuple[str, int, int]]:
    if not os.path.exists(unavailability_path):
        return set()
    df = pd.read_csv(unavailability_path)
    unavailable: set[Tuple[str, int, int]] = set()
    for _, r in df.iterrows():
        u = str(r["unit_id"])
        md = int(r["mode_id"])
        t0 = int(r["start_time_id"])
        t1 = int(r["end_time_id"])
        for t in range(t0, t1 + 1):
            unavailable.add((u, md, t))
    return unavailable


def _load_event_cost_windows(cost_windows_path: str) -> Dict[Tuple[str, str, int], float]:
    if not os.path.exists(cost_windows_path):
        return {}
    df = pd.read_csv(cost_windows_path)
    out: Dict[Tuple[str, str, int], float] = {}
    for _, r in df.iterrows():
        u = str(r["unit_id"])
        et = str(r["event_type"]).strip().upper()
        t0 = int(r["start_time_id"])
        t1 = int(r["end_time_id"])
        c = float(r["event_cost"])
        if et not in {"START", "STOP"}:
            raise ValueError(f"Unsupported event_type={et!r} in {cost_windows_path}")
        for t in range(t0, t1 + 1):
            out[(et, u, t)] = c
    return out


def build_and_solve(
    data_dir: str,
    instance_json_path: str,
    time_limit_s: float,
    mip_gap: Optional[float],
    output_flag: bool,
) -> Tuple[int, Optional[float], Optional[float], Optional[float]]:
    params = _read_instance_params(instance_json_path)

    units = pd.read_csv(os.path.join(data_dir, "units.csv"))["unit_id"].astype(str).tolist()
    mode_specs = pd.read_csv(os.path.join(data_dir, "mode_specs.csv"))
    # mode_costs are placeholders, actual costs in der_production_costs.csv
    
    unit_modes = mode_specs # Just use specs for structure
    
    requirements = pd.read_csv(os.path.join(data_dir, "system_requirements.csv"))
    policy_rules = pd.read_csv(os.path.join(data_dir, "policy_rules.csv"), low_memory=False)
    policy_terms = pd.read_csv(os.path.join(data_dir, "policy_rule_terms.csv"), low_memory=False)
    
    prod_costs_path = os.path.join(data_dir, "der_production_costs.csv")
    prod_costs_df = pd.read_csv(prod_costs_path) if os.path.exists(prod_costs_path) else None

    unavailable = _load_mode_unavailability(os.path.join(data_dir, "mode_unavailability_windows.csv"))
    event_cost = _load_event_cost_windows(os.path.join(data_dir, "start_stop_event_cost_windows.csv"))

    times = requirements["time_id"].astype(int).tolist()
    T = max(times)

    modes_by_unit: Dict[str, List[int]] = {}
    mode_min: Dict[Tuple[str, int], float] = {}
    mode_max: Dict[Tuple[str, int], float] = {}
    
    for _, r in unit_modes.iterrows():
        u = str(r["unit_id"])
        md = int(r["mode_id"])
        modes_by_unit.setdefault(u, []).append(md)
        mode_min[(u, md)] = float(r["min_output"])
        mode_max[(u, md)] = float(r["max_output"])

    avail_modes_by_unit_time: Dict[Tuple[str, int], List[int]] = {}
    for u in units:
        for t in times:
            avail_modes_by_unit_time[(u, t)] = [
                md for md in modes_by_unit.get(u, []) if (u, md, t) not in unavailable
            ]

    max_available_mode_output_by_unit_time: Dict[Tuple[str, int], float] = {}
    for u in units:
        for t in times:
            avail = avail_modes_by_unit_time[(u, t)]
            max_available_mode_output_by_unit_time[(u, t)] = (
                max(mode_max[(u, md)] for md in avail) if avail else 0.0
            )

    m = gp.Model("uccase12-hard")
    m.setParam("OutputFlag", 1 if output_flag else 0)
    m.setParam("TimeLimit", float(time_limit_s))
    if mip_gap is not None:
        m.setParam("MIPGap", float(mip_gap))

    online: Dict[Tuple[str, int], gp.Var] = {}
    mode_on: Dict[Tuple[str, int, int], gp.Var] = {}
    gen: Dict[Tuple[str, int, int], gp.Var] = {}
    op_cost: Dict[Tuple[str, int, int], gp.Var] = {} # Operating cost for (u, t, m)

    for u in units:
        for t in times:
            online[(u, t)] = m.addVar(vtype=GRB.BINARY, name=f"online[{u},{t}]")
            for md in avail_modes_by_unit_time[(u, t)]:
                mode_on[(u, t, md)] = m.addVar(vtype=GRB.BINARY, name=f"mode_on[{u},{t},{md}]")
                gen[(u, t, md)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"gen[{u},{t},{md}]")
                op_cost[(u, t, md)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"op_cost[{u},{t},{md}]")

    start: Dict[Tuple[str, int], gp.Var] = {}
    stop: Dict[Tuple[str, int], gp.Var] = {}
    startup_cost: Dict[Tuple[str, int], gp.Var] = {}
    start_stage: Dict[Tuple[str, int, int], gp.Var] = {}
    stop_stage: Dict[Tuple[str, int, int], gp.Var] = {}
    unserved: Dict[Tuple[int, int], gp.Var] = {}

    def var_for_term(tt: str, r: pd.Series) -> gp.Var:
        term_type = tt.upper()
        if term_type == "ONLINE":
            return online[(str(r["unit_id"]), int(r["time_id"]))]
        if term_type == "MODE_ON":
            return mode_on[(str(r["unit_id"]), int(r["time_id"]), int(r["mode_id"]))]
        if term_type == "GEN":
            return gen[(str(r["unit_id"]), int(r["time_id"]), int(r["mode_id"]))]
        if term_type == "START":
            u = str(r["unit_id"])
            t = int(r["time_id"])
            if (u, t) not in start:
                start[(u, t)] = m.addVar(vtype=GRB.BINARY, name=f"start[{u},{t}]")
            return start[(u, t)]
        if term_type == "STOP":
            u = str(r["unit_id"])
            t = int(r["time_id"])
            if (u, t) not in stop:
                stop[(u, t)] = m.addVar(vtype=GRB.BINARY, name=f"stop[{u},{t}]")
            return stop[(u, t)]
        if term_type == "STARTUP_COST":
            u = str(r["unit_id"])
            t = int(r["time_id"])
            if (u, t) not in startup_cost:
                startup_cost[(u, t)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"startup_cost[{u},{t}]")
            return startup_cost[(u, t)]
        if term_type == "START_STAGE":
            u = str(r["unit_id"])
            t = int(r["time_id"])
            k = int(r["stage_id"])
            if (u, t, k) not in start_stage:
                start_stage[(u, t, k)] = m.addVar(vtype=GRB.BINARY, name=f"start_stage[{u},{t},{k}]")
            return start_stage[(u, t, k)]
        if term_type == "STOP_STAGE":
            u = str(r["unit_id"])
            t = int(r["time_id"])
            k = int(r["stage_id"])
            if (u, t, k) not in stop_stage:
                stop_stage[(u, t, k)] = m.addVar(vtype=GRB.BINARY, name=f"stop_stage[{u},{t},{k}]")
            return stop_stage[(u, t, k)]
        if term_type == "UNSERVED":
            a = int(r["area_id"])
            t = int(r["time_id"])
            if (a, t) not in unserved:
                unserved[(a, t)] = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"unserved[{a},{t}]")
            return unserved[(a, t)]
        raise ValueError(f"Unsupported term_type={term_type!r}")

    m.update()

    for u in units:
        for t in times:
            m.addConstr(
                gp.quicksum(mode_on[(u, t, md)] for md in avail_modes_by_unit_time[(u, t)]) == online[(u, t)],
                name=f"mode_choice_link[{u},{t}]",
            )
            for md in avail_modes_by_unit_time[(u, t)]:
                m.addConstr(gen[(u, t, md)] >= mode_min[(u, md)] * mode_on[(u, t, md)])
                m.addConstr(gen[(u, t, md)] <= mode_max[(u, md)] * mode_on[(u, t, md)])

    # Piecewise linear costs
    if prod_costs_df is not None:
        for _, r in prod_costs_df.iterrows():
            u = str(r["unit_id"])
            md = int(r["mode_id"])
            t = int(r["time_id"])
            slope = float(r["slope"])
            intercept = float(r["intercept"])
            
            if (u, t, md) in op_cost:
                # cost >= slope * gen + intercept * mode_on
                m.addConstr(op_cost[(u, t, md)] >= slope * gen[(u, t, md)] + intercept * mode_on[(u, t, md)])

    terms_by_rule: Dict[str, pd.DataFrame] = {k: g for k, g in policy_terms.groupby("rule_id")}

    for _, rr in policy_rules.iterrows():
        rule_id = str(rr["rule_id"])
        sense = str(rr["sense"]).strip()
        rhs = float(rr["rhs"])
        expr = gp.LinExpr()

        term_df = terms_by_rule.get(rule_id)
        explicit_online_coefs: Dict[str, float] = {}
        
        if term_df is not None:
            for _, tr in term_df.iterrows():
                coef = float(tr["coef"])
                tt = str(tr["term_type"]).upper()
                if tt == "ONLINE" and pd.notna(rr.get("online_capacity_source")):
                    explicit_online_coefs[str(tr["unit_id"])] = coef
                    continue 
                
                if abs(coef) < 1e-15:
                    continue
                expr.add(var_for_term(tt, tr), coef)

        gen_scope = rr.get("gen_scope")
        if isinstance(gen_scope, str) and gen_scope.strip():
            if gen_scope.strip() != "ALL_DISPATCHABLE_MODES_AT_TIME":
                raise ValueError(f"Unsupported gen_scope={gen_scope!r}")
            t = int(rr["time_id"])
            gc = float(rr["gen_coef"])
            for u in units:
                for md in avail_modes_by_unit_time[(u, t)]:
                    expr.add(gen[(u, t, md)], gc)

        online_capacity_source = rr.get("online_capacity_source")
        if isinstance(online_capacity_source, str) and online_capacity_source.strip():
            if online_capacity_source.strip() != "MAX_MODE_OUTPUT":
                raise ValueError(f"Unsupported online_capacity_source={online_capacity_source!r}")
            t = int(rr["time_id"])
            for u in units:
                cap = max_available_mode_output_by_unit_time[(u, t)]
                coef = explicit_online_coefs.get(u, 1.0)
                expr.add(online[(u, t)], coef * cap)

        if sense == "<=":
            m.addConstr(expr <= rhs, name=rule_id)
        elif sense == ">=":
            m.addConstr(expr >= rhs, name=rule_id)
        elif sense == "=":
            m.addConstr(expr == rhs, name=rule_id)
        else:
            raise ValueError(f"Unsupported sense={sense!r}")

    obj = gp.LinExpr()
    # Add operating costs
    for v in op_cost.values():
        obj.add(v, 1.0)
        
    for v in startup_cost.values():
        obj.add(v, 1.0)
    for (a, t), v in unserved.items():
        obj.add(v, params.unserved_energy_penalty)
    for (u, t), v in start.items():
        obj.add(v, event_cost.get(("START", u, t), 0.0))
    for (u, t), v in stop.items():
        obj.add(v, event_cost.get(("STOP", u, t), 0.0))

    m.setObjective(obj, GRB.MINIMIZE)
    m.optimize()

    status = int(m.Status)
    obj_val = float(m.ObjVal) if m.SolCount > 0 else None
    obj_bound = float(m.ObjBound) if m.SolCount > 0 else None
    gap = float(m.MIPGap) if m.SolCount > 0 and hasattr(m, "MIPGap") else None
    return status, obj_val, obj_bound, gap


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(__file__), "data"))
    ap.add_argument("--instance-json", default=os.path.join(os.path.dirname(__file__), "instance.json"))
    ap.add_argument("--time-limit", type=float, default=200.0)
    ap.add_argument("--mipgap", type=float, default=1e-6)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    params = _read_instance_params(args.instance_json)
    status, obj, bound, gap = build_and_solve(
        data_dir=args.data_dir,
        instance_json_path=args.instance_json,
        time_limit_s=args.time_limit,
        mip_gap=args.mipgap,
        output_flag=not args.quiet,
    )

    print(f"status={status}")
    if obj is None:
        print("no incumbent solution")
        return
    print(f"objective={obj:.6f}")
    if bound is not None and gap is not None:
        print(f"best_bound={bound:.6f} gap={gap:.6%}")
    if params.optimal_value is not None and status == GRB.OPTIMAL:
        diff = abs(obj - params.optimal_value)
        ok = diff <= 1e-3
        print(f"optimal_value={params.optimal_value:.6f} abs_diff={diff:.6g} ok={ok}")


if __name__ == "__main__":
    main()
