#!/usr/bin/env python3
import argparse
import json
import os

import pandas as pd
import gurobipy as gp
from gurobipy import GRB


class SCTSolver:
    def __init__(self, data_dir: str, instance_file: str):
        self.data_dir = data_dir
        self.instance_file = instance_file

        with open(self.instance_file, "r", encoding="utf-8") as f:
            self.instance = json.load(f)
        self.params = self.instance["parameters"]
        self.expected_optimal = float(self.instance["optimal_value"])

        self.num_operations = int(self.params["num_operations"])
        self.num_station_options = int(self.params["num_station_options"])
        self.num_variants = int(self.params["num_variants"])
        self.num_checkpoints = int(self.params["num_checkpoints"])
        self.checkpoint_upper_bound = float(self.params["checkpoint_upper_bound"])
        self.priority_budget = int(self.params["priority_budget"])
        self.num_policy_checks = int(self.params.get("num_policy_checks", 0))

        self.obj_staffing_weight = float(self.params["objective_staffing_weight"])
        self.obj_min_checkpoint_weight = float(self.params["objective_min_checkpoint_weight"])
        self.obj_aggregate_1_weight = float(self.params["objective_aggregate_1_weight"])
        self.obj_aggregate_2_weight = float(self.params["objective_aggregate_2_weight"])
        self.obj_discrete_routing_score_weight = float(self.params["objective_discrete_routing_score_weight"])

        self.stations = pd.read_csv(os.path.join(self.data_dir, "stations.csv"))
        self.routing = pd.read_csv(os.path.join(self.data_dir, "routing.csv"))
        self.checkpoint_weights = pd.read_csv(os.path.join(self.data_dir, "checkpoint_weights.csv"))
        self.rate_denominators = pd.read_csv(os.path.join(self.data_dir, "rate_denominators.csv"))
        self.rate_contributions = pd.read_csv(os.path.join(self.data_dir, "rate_contributions.csv"))
        self.budget_meta = pd.read_csv(os.path.join(self.data_dir, "budget_meta.csv"))
        self.budget_contributions = pd.read_csv(os.path.join(self.data_dir, "budget_contributions.csv"))
        self.policy_meta = pd.read_csv(os.path.join(self.data_dir, "policy_meta.csv"))
        self.policy_contributions = pd.read_csv(os.path.join(self.data_dir, "policy_contributions.csv"))

        self.model: gp.Model | None = None
        self.a: dict[tuple[int, int], gp.Var] = {}
        self.p: dict[tuple[int, int], gp.Var] = {}
        self.u: gp.Var | None = None
        self.r: dict[tuple[int, int], gp.Var] = {}
        self.q: dict[tuple[int, int], gp.Var] = {}
        self.m: gp.Var | None = None
        self.R1: gp.Var | None = None
        self.R2: gp.Var | None = None

        self._validate_inputs()

    def _validate_inputs(self) -> None:
        if self.stations["station_id"].nunique() != self.num_station_options:
            raise ValueError("stations.csv station_id count mismatch")
        if self.routing["operation_id"].nunique() != self.num_operations:
            raise ValueError("routing.csv operation_id count mismatch")
        if len(self.checkpoint_weights) != self.num_checkpoints:
            raise ValueError("checkpoint_weights.csv row count mismatch")
        if len(self.rate_denominators) != self.num_variants * self.num_checkpoints:
            raise ValueError("rate_denominators.csv row count mismatch")
        if len(self.budget_meta) != self.num_variants * self.num_checkpoints:
            raise ValueError("budget_meta.csv row count mismatch")
        if self.num_policy_checks <= 0:
            self.num_policy_checks = int(len(self.policy_meta))
        if len(self.policy_meta) != self.num_policy_checks:
            raise ValueError("policy_meta.csv row count mismatch")
        if self.policy_meta["requirement_id"].nunique() != len(self.policy_meta):
            raise ValueError("policy_meta.csv requirement_id must be unique")
        if not set(self.policy_contributions["requirement_id"]).issubset(set(self.policy_meta["requirement_id"])):
            raise ValueError("policy_contributions.csv refers to unknown requirement_id")
        bad = self.routing[(self.routing["priority_eligible"] == 1) & (self.routing["assignment_type_id"] != 0)]
        if len(bad) > 0:
            raise ValueError("priority_eligible must only appear on discrete routing options")

    def build(self, time_limit: float | None, mip_gap: float | None, threads: int | None, quiet: bool) -> None:
        self.model = gp.Model("sct")
        self.model.Params.OutputFlag = 0 if quiet else 1
        if time_limit is not None:
            self.model.Params.TimeLimit = float(time_limit)
        if mip_gap is not None:
            self.model.Params.MIPGap = float(mip_gap)
        if threads is not None:
            self.model.Params.Threads = int(threads)

        self._create_variables()
        self._add_constraints()
        self._set_objective()
        self.model.update()

    def _create_variables(self) -> None:
        assert self.model is not None

        for _, row in self.routing.iterrows():
            i = int(row["operation_id"])
            s = int(row["station_id"])
            if int(row["assignment_type_id"]) == 0:
                self.a[i, s] = self.model.addVar(vtype=GRB.BINARY, name=f"a[{i},{s}]")
            else:
                self.a[i, s] = self.model.addVar(lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name=f"a[{i},{s}]")
            if int(row["priority_eligible"]) == 1:
                self.p[i, s] = self.model.addVar(vtype=GRB.BINARY, name=f"p[{i},{s}]")

        self.u = self.model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="u")

        for v in range(self.num_variants):
            for k in range(self.num_checkpoints):
                self.r[v, k] = self.model.addVar(
                    lb=-GRB.INFINITY,
                    ub=self.checkpoint_upper_bound,
                    vtype=GRB.CONTINUOUS,
                    name=f"r[{v},{k}]",
                )
                self.q[v, k] = self.model.addVar(
                    lb=-GRB.INFINITY,
                    ub=self.checkpoint_upper_bound,
                    vtype=GRB.CONTINUOUS,
                    name=f"q[{v},{k}]",
                )

        self.m = self.model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="m")
        self.R1 = self.model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="R1")
        self.R2 = self.model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="R2")

    def _add_constraints(self) -> None:
        assert self.model is not None and self.u is not None and self.m is not None and self.R1 is not None and self.R2 is not None

        for i, grp in self.routing.groupby("operation_id"):
            i = int(i)
            self.model.addConstr(
                gp.quicksum(self.a[int(r["operation_id"]), int(r["station_id"])] for _, r in grp.iterrows()) == 1.0,
                name=f"op[{i}]",
            )

        st = self.stations.set_index("station_id")
        for s in range(self.num_station_options):
            base = float(st.loc[s]["base_capacity"])
            crew = float(st.loc[s]["crew_capacity_per_unit"])
            grp = self.routing[self.routing["station_id"] == s]
            expr = gp.quicksum(
                float(r["workload_units"]) * self.a[int(r["operation_id"]), int(r["station_id"])]
                for _, r in grp.iterrows()
            )
            self.model.addConstr(expr <= base + crew * self.u, name=f"cap[{s}]")

        for (i, s), pv in self.p.items():
            self.model.addConstr(pv <= self.a[i, s], name=f"pon[{i},{s}]")
        self.model.addConstr(gp.quicksum(self.p.values()) <= float(self.priority_budget), name="pbudget")

        # policy checks (additional internal rules over selected discrete choices)
        if len(self.policy_meta) > 0:
            policy_index: dict[int, list[tuple[int, int, float]]] = {}
            for _, row in self.policy_contributions.iterrows():
                rid = int(row["requirement_id"])
                policy_index.setdefault(rid, []).append(
                    (int(row["operation_id"]), int(row["station_id"]), float(row["coefficient"]))
                )
            for _, meta in self.policy_meta.iterrows():
                rid = int(meta["requirement_id"])
                rhs = float(meta["rhs"])
                sense_id = int(meta["sense_id"])
                contribs = policy_index.get(rid, [])
                expr = gp.quicksum(coef * self.a[i, s] for i, s, coef in contribs)
                if sense_id == 0:
                    self.model.addConstr(expr <= rhs, name=f"policy[{rid}]")
                else:
                    self.model.addConstr(expr >= rhs, name=f"policy[{rid}]")

        for v in range(self.num_variants):
            for k in range(self.num_checkpoints):
                self.model.addConstr(self.m <= self.r[v, k], name=f"min[{v},{k}]")

        weights = {int(row["checkpoint_id"]): float(row["weight"]) for _, row in self.checkpoint_weights.iterrows()}
        self.model.addConstr(
            self.R1 <= gp.quicksum(weights[k] * self.r[v, k] for v in range(self.num_variants) for k in range(self.num_checkpoints)),
            name="agg1",
        )
        self.model.addConstr(
            self.R2 <= gp.quicksum(weights[k] * self.q[v, k] for v in range(self.num_variants) for k in range(self.num_checkpoints)),
            name="agg2",
        )

        rate_index: dict[tuple[int, int], list[tuple[int, int, float]]] = {}
        for _, row in self.rate_contributions.iterrows():
            key = (int(row["variant_id"]), int(row["checkpoint_id"]))
            rate_index.setdefault(key, []).append(
                (int(row["operation_id"]), int(row["station_id"]), float(row["coefficient"]))
            )
        for _, meta in self.rate_denominators.iterrows():
            v = int(meta["variant_id"])
            k = int(meta["checkpoint_id"])
            denom = float(meta["denominator"])
            rhs = float(meta["rhs"])
            sense_id = int(meta["sense_id"])
            contribs = rate_index.get((v, k), [])
            lhs = gp.quicksum(coef * self.a[i, s] for i, s, coef in contribs) - denom * self.r[v, k]
            if sense_id == 0:
                self.model.addConstr(lhs <= rhs, name=f"rate[{v},{k}]")
            else:
                self.model.addConstr(lhs >= rhs, name=f"rate[{v},{k}]")

        budget_index: dict[tuple[int, int], list[tuple[int, int, float]]] = {}
        for _, row in self.budget_contributions.iterrows():
            key = (int(row["variant_id"]), int(row["checkpoint_id"]))
            budget_index.setdefault(key, []).append(
                (int(row["operation_id"]), int(row["station_id"]), float(row["coefficient"]))
            )
        for _, meta in self.budget_meta.iterrows():
            v = int(meta["variant_id"])
            k = int(meta["checkpoint_id"])
            bcoef = float(meta["budget_coefficient"])
            rhs = float(meta["rhs"])
            sense_id = int(meta["sense_id"])
            contribs = budget_index.get((v, k), [])
            expr = gp.LinExpr(bcoef * self.q[v, k])
            for i, s, coef in contribs:
                if (i, s) in self.p:
                    expr += coef * (self.a[i, s] - self.p[i, s])
                else:
                    expr += coef * self.a[i, s]
            if sense_id == 0:
                self.model.addConstr(expr <= rhs, name=f"budget[{v},{k}]")
            else:
                self.model.addConstr(expr >= rhs, name=f"budget[{v},{k}]")

    def _set_objective(self) -> None:
        assert self.model is not None and self.u is not None and self.m is not None and self.R1 is not None and self.R2 is not None

        obj = self.obj_staffing_weight * self.u
        obj -= self.obj_min_checkpoint_weight * self.m
        obj -= self.obj_aggregate_1_weight * self.R1
        obj -= self.obj_aggregate_2_weight * self.R2

        if self.obj_discrete_routing_score_weight != 0.0:
            for _, row in self.routing.iterrows():
                if int(row["assignment_type_id"]) != 0:
                    continue
                score = row["workcontent_score"]
                if pd.isna(score):
                    continue
                i = int(row["operation_id"])
                s = int(row["station_id"])
                obj -= self.obj_discrete_routing_score_weight * float(score) * self.a[i, s]

        self.model.setObjective(obj, GRB.MINIMIZE)

    def solve(self) -> None:
        assert self.model is not None
        self.model.optimize()

    def assert_optimal_value(self, tol: float = 1e-4) -> None:
        assert self.model is not None
        if self.model.Status != GRB.OPTIMAL:
            raise RuntimeError("Model is not OPTIMAL; cannot check optimal_value")
        diff = abs(float(self.model.ObjVal) - self.expected_optimal)
        if diff > tol:
            raise AssertionError(
                f"Objective mismatch: got {self.model.ObjVal:.12f}, expected {self.expected_optimal:.12f}, diff {diff:.3e}"
            )


def main() -> None:
    ap = argparse.ArgumentParser(description="Solve SCT2 (gurobipy) from instance.json + data/*.csv")
    ap.add_argument("--data-dir", default=os.path.join("instances", "sct2", "data"))
    ap.add_argument("--instance", default=os.path.join("instances", "sct2", "instance.json"))
    ap.add_argument("--time-limit", type=float, default=None)
    ap.add_argument("--mip-gap", type=float, default=None)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--check-optimal", action="store_true")
    args = ap.parse_args()

    solver = SCTSolver(data_dir=args.data_dir, instance_file=args.instance)
    solver.build(time_limit=args.time_limit, mip_gap=args.mip_gap, threads=args.threads, quiet=args.quiet)
    solver.solve()

    m = solver.model
    assert m is not None
    if m.SolCount > 0:
        print(f"OBJ = {float(m.ObjVal):.12f}")
        if m.Status != GRB.OPTIMAL:
            print(f"BOUND = {float(m.ObjBound):.12f}")
            try:
                print(f"GAP = {float(m.MIPGap)}")
            except gp.GurobiError:
                pass
    else:
        print(f"STATUS = {m.Status}")

    if args.check_optimal:
        solver.assert_optimal_value()
        print("CHECK OK")


if __name__ == "__main__":
    main()
