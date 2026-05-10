"""
bab1 solver (based on "clean data reconstruction")

Features:
- Reads `files` field in `instance.json` to locate `data/*.csv`
- Reconstructs an optimization model essentially equivalent to bab1.mps using Gurobi and solves it
- Can perform consistency check based on known optimal value: optimal objective for this instance is -218764.88525

Usage:
  python instances/bab1/solver.py instances/bab1
  python instances/bab1/solver.py instances/bab1 --check_opt -218764.88525
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

import gurobipy as gp
from gurobipy import GRB


@dataclass(frozen=True)
class SolveResult:
    status: int
    obj_val: Optional[float]


class Bab1Solver:
    def __init__(self, instance_dir: str) -> None:
        self.instance_dir = instance_dir
        self.config_path = os.path.join(instance_dir, "instance.json")
        self.config: Dict = {}

        self.model = gp.Model("bab1")
        self.x: Dict[str, gp.Var] = {}
        self._data: Dict[str, pd.DataFrame] = {}

    def _load_config(self) -> None:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"instance.json not found: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

    def _csv_path(self, key: str) -> str:
        files = self.config.get("files", {})
        if key not in files:
            raise KeyError(f"instance.json.files missing {key}")
        rel_path = files[key]["path"]
        return os.path.join(self.instance_dir, rel_path)

    def load_data(self) -> None:
        self._load_config()

        required = [
            "decisions",
            "link_pairs",
            "balance_groups",
            "balance_members",
            "conflict_groups",
            "conflict_members",
            "coverage_groups",
            "coverage_members",
            "cardinality_caps",
            "cardinality_cap_members",
            "mix_targets",
            "mix_flags",
            "generic_linear_constraints",
            "generic_linear_terms",
        ]

        optional = [
            "source_mapping",
        ]

        for k in required:
            self._data[k] = pd.read_csv(self._csv_path(k))
        for k in optional:
            try:
                p = self._csv_path(k)
            except KeyError:
                continue
            if os.path.exists(p):
                self._data[k] = pd.read_csv(p)

    def build_model(self) -> None:
        d = self._data
        if "decisions" not in d:
            raise RuntimeError("Please call load_data() first")

        decisions = d["decisions"]
        decision_ids = decisions["decision_id"].astype(str).tolist()
        cost = dict(zip(decision_ids, decisions["cost"].astype(float).tolist()))

        self.x = self.model.addVars(decision_ids, vtype=GRB.BINARY, name="x")
        self.model.setObjective(gp.quicksum(cost[i] * self.x[i] for i in decision_ids), GRB.MINIMIZE)

        # 1) link pairs: x_a = x_b
        for _, r in d["link_pairs"].iterrows():
            a = str(r["a_decision_id"])
            b = str(r["b_decision_id"])
            self.model.addConstr(self.x[a] == self.x[b], name=f"link[{a},{b}]")

        # 2) balance groups: sum(pos) - sum(neg) = 0
        members = d["balance_members"]
        g_to_pos: Dict[str, List[str]] = defaultdict(list)
        g_to_neg: Dict[str, List[str]] = defaultdict(list)
        for _, r in members.iterrows():
            gid = str(r["balance_group_id"])
            did = str(r["decision_id"])
            side = str(r["side"])
            if side == "pos":
                g_to_pos[gid].append(did)
            elif side == "neg":
                g_to_neg[gid].append(did)
            else:
                raise ValueError(f"Unknown side: {side}")
        for gid in d["balance_groups"]["balance_group_id"].astype(str).tolist():
            expr = gp.quicksum(self.x[i] for i in g_to_pos.get(gid, [])) - gp.quicksum(self.x[i] for i in g_to_neg.get(gid, []))
            self.model.addConstr(expr == 0, name=f"bal[{gid}]")

        # 3) conflicts: sum <= 1
        c_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["conflict_members"].iterrows():
            c_to_members[str(r["conflict_group_id"])].append(str(r["decision_id"]))
        for cid in d["conflict_groups"]["conflict_group_id"].astype(str).tolist():
            self.model.addConstr(gp.quicksum(self.x[m] for m in c_to_members.get(cid, [])) <= 1, name=f"conf[{cid}]")

        # 4) coverage: sum >= min_selected
        cov_min = dict(zip(d["coverage_groups"]["coverage_group_id"].astype(str), d["coverage_groups"]["min_selected"].astype(float)))
        g_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["coverage_members"].iterrows():
            g_to_members[str(r["coverage_group_id"])].append(str(r["decision_id"]))
        for gid, k in cov_min.items():
            self.model.addConstr(gp.quicksum(self.x[m] for m in g_to_members.get(gid, [])) >= float(k), name=f"cov[{gid}]")

        # 5) caps: sum <= max_selected
        cap_k = dict(zip(d["cardinality_caps"]["cap_group_id"].astype(str), d["cardinality_caps"]["max_selected"].astype(float)))
        k_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["cardinality_cap_members"].iterrows():
            k_to_members[str(r["cap_group_id"])].append(str(r["decision_id"]))
        for kid, k in cap_k.items():
            self.model.addConstr(gp.quicksum(self.x[m] for m in k_to_members.get(kid, [])) <= float(k), name=f"cap[{kid}]")

        # 6) mix: sum (flag - p) x <= 0
        p_by_dim = dict(zip(d["mix_targets"]["mix_dimension_id"].astype(str), d["mix_targets"]["max_share"].astype(float)))
        dim_to_flags: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for _, r in d["mix_flags"].iterrows():
            dim_to_flags[str(r["mix_dimension_id"])].append((str(r["decision_id"]), int(r["flag"])))
        for dim, flags in dim_to_flags.items():
            p = float(p_by_dim[dim])
            expr = gp.quicksum((flag - p) * self.x[did] for did, flag in flags)
            self.model.addConstr(expr <= 0.0, name=f"mix[{dim}]")

        # 7) generic linear constraints (small remainder)
        gen = d["generic_linear_constraints"]
        gen_terms = d["generic_linear_terms"]
        cid_to_terms: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        for _, r in gen_terms.iterrows():
            cid_to_terms[str(r["constraint_id"])].append((str(r["decision_id"]), float(r["coef"])))
        for _, r in gen.iterrows():
            cid = str(r["constraint_id"])
            sense = str(r["sense"])
            rhs = float(r["rhs"])
            expr = gp.quicksum(coef * self.x[did] for did, coef in cid_to_terms.get(cid, []))
            if sense == "<=":
                self.model.addConstr(expr <= rhs, name=f"gen[{cid}]")
            elif sense == "=":
                self.model.addConstr(expr == rhs, name=f"gen[{cid}]")
            elif sense == ">=":
                self.model.addConstr(expr >= rhs, name=f"gen[{cid}]")
            else:
                raise ValueError(f"Unknown generic sense: {sense}")

        self.model.update()

    def solve(
        self,
        time_limit_sec: Optional[float] = None,
        mip_gap: Optional[float] = None,
        threads: Optional[int] = None,
        verbose: bool = True,
    ) -> SolveResult:
        if not verbose:
            self.model.Params.OutputFlag = 0
        if time_limit_sec is not None:
            self.model.Params.TimeLimit = float(time_limit_sec)
        if mip_gap is not None:
            self.model.Params.MIPGap = float(mip_gap)
        if threads is not None:
            self.model.Params.Threads = int(threads)

        self.model.optimize()

        if self.model.Status in (GRB.OPTIMAL, GRB.SUBOPTIMAL) and self.model.SolCount > 0:
            return SolveResult(status=self.model.Status, obj_val=float(self.model.ObjVal))
        if self.model.Status == GRB.TIME_LIMIT and self.model.SolCount > 0:
            return SolveResult(status=self.model.Status, obj_val=float(self.model.ObjVal))
        return SolveResult(status=self.model.Status, obj_val=None)

    def rounded_objective(self) -> float:
        if "decisions" not in self._data:
            raise RuntimeError("Please call load_data() first")
        cost_by_id = dict(
            zip(
                self._data["decisions"]["decision_id"].astype(str),
                self._data["decisions"]["cost"].astype(float),
            )
        )
        return float(sum(cost_by_id[did] * int(round(var.X)) for did, var in self.x.items()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance_dir", type=str, help="Instance directory (containing instance.json and data/)")
    parser.add_argument("--check_opt", type=float, default=None, help="Check optimal value (e.g. -218764.88525)")
    parser.add_argument("--tol", type=float, default=1e-4, help="Tolerance for optimal value check (default 1e-4)")
    parser.add_argument("--time_limit", type=float, default=None, help="Time limit for solving (seconds)")
    parser.add_argument("--mip_gap", type=float, default=0.0, help="MIPGap (default 0.0)")
    parser.add_argument("--threads", type=int, default=None, help="Number of Gurobi threads")
    parser.add_argument("--quiet", action="store_true", help="Silent solving")
    args = parser.parse_args()

    solver = Bab1Solver(args.instance_dir)
    solver.load_data()
    solver.build_model()
    res = solver.solve(
        time_limit_sec=args.time_limit,
        mip_gap=args.mip_gap,
        threads=args.threads,
        verbose=not args.quiet,
    )

    print(f"Solve status: {res.status}")
    if res.obj_val is None:
        raise SystemExit("No available solution (infeasible or failed)")

    rounded_obj = solver.rounded_objective()
    print(f"Objective (solver reported): {res.obj_val:.6f}")
    print(f"Objective (recalculated with 0/1 rounding): {rounded_obj:.6f}")

    if args.check_opt is not None:
        diff = abs(rounded_obj - float(args.check_opt))
        ok = diff <= float(args.tol)
        print(f"Check objective value: {float(args.check_opt):.6f}")
        print(f"Difference: {diff:.6g} (tol={args.tol})")
        if not ok:
            raise SystemExit("Optimal value check failed: solver result inconsistent with expected")
        print("Optimal value check passed")


if __name__ == "__main__":
    main()