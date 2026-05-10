"""
bab2 Solver (Vehicle routing with profits + integrated crew scheduling)

Features:
- Reads `data/*.csv` pointed to by `files` in `instance.json`
- Rebuilds optimization model using Gurobi and solves it
- Can verify consistency using known optimal value: The optimal objective value for this instance is -357544.3115

Usage:
  python instances/bab2/solver.py instances/bab2
  python instances/bab2/solver.py instances/bab2 --check_opt -357544.3115
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


class Bab2Solver:
    def __init__(self, instance_dir: str) -> None:
        self.instance_dir = instance_dir
        self.config_path = os.path.join(instance_dir, "instance.json")
        self.config: Dict = {}

        self.model = gp.Model("bab2")
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
        return os.path.join(self.instance_dir, files[key]["path"])

    def load_data(self) -> None:
        self._load_config()
        required = [
            "decisions",
            "start_slots",
            "start_options",
            "flow_nodes",
            "flow_arcs",
            "flow_exceptions",
            "packages",
            "package_candidates",
            "windows",
            "window_members",
            "mix_targets",
            "mix_flags",
            "coverage_groups",
            "coverage_members",
            "conflict_groups",
            "conflict_members",
            "dependencies",
            "exact_choice_groups",
            "exact_choice_members",
            "cardinality_caps",
            "cardinality_cap_members",
            "redundant_bounds",
        ]
        for k in required:
            self._data[k] = pd.read_csv(self._csv_path(k))

    def build_model(self, include_redundant_bounds: bool = False) -> None:
        d = self._data
        decisions = d["decisions"]
        decision_ids = decisions["decision_id"].astype(str).tolist()
        cost = dict(zip(decision_ids, decisions["cost"].astype(float).tolist()))

        self.x = self.model.addVars(decision_ids, vtype=GRB.BINARY, name="x")
        self.model.setObjective(gp.quicksum(cost[i] * self.x[i] for i in decision_ids), GRB.MINIMIZE)

        # 1) start slots
        slot_to_opts: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["start_options"].iterrows():
            slot_to_opts[str(r["start_slot_id"])].append(str(r["decision_id"]))
        for sid, opts in slot_to_opts.items():
            self.model.addConstr(gp.quicksum(self.x[o] for o in opts) == 1, name=f"start[{sid}]")

        # 2) flow balance
        node_rhs = dict(zip(d["flow_nodes"]["node_id"].astype(str), d["flow_nodes"]["rhs"].astype(float)))
        node_terms: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
        for _, r in d["flow_arcs"].iterrows():
            did = str(r["decision_id"])
            fr = str(r["from_node"])
            to = str(r["to_node"])
            node_terms[fr].append((did, 1.0))
            node_terms[to].append((did, -1.0))
        for _, r in d["flow_exceptions"].iterrows():
            did = str(r["decision_id"])
            node = str(r["node_id"])
            coef = float(r["coef"])
            node_terms[node].append((did, coef))
        for node, rhs_val in node_rhs.items():
            expr = gp.quicksum(coef * self.x[did] for did, coef in node_terms.get(node, []))
            self.model.addConstr(expr == float(rhs_val), name=f"flow[{node}]")

        # 3) packages
        pkg_to_open = dict(zip(d["packages"]["package_id"].astype(str), d["packages"]["package_decision_id"].astype(str)))
        pkg_to_cands: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["package_candidates"].iterrows():
            pkg_to_cands[str(r["package_id"])].append(str(r["candidate_id"]))
        for pid, open_dec in pkg_to_open.items():
            self.model.addConstr(
                gp.quicksum(self.x[c] for c in pkg_to_cands.get(pid, [])) == 2 * self.x[open_dec],
                name=f"pkg[{pid}]",
            )

        # 4) windows
        win_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["window_members"].iterrows():
            win_to_members[str(r["window_id"])].append(str(r["decision_id"]))
        for _, r in d["windows"].iterrows():
            wid = str(r["window_id"])
            members = win_to_members.get(wid, [])
            s = gp.quicksum(self.x[m] for m in members)
            self.model.addConstr(s >= float(r["min_count"]), name=f"win_min[{wid}]")
            self.model.addConstr(s <= float(r["max_count"]), name=f"win_max[{wid}]")
            self.model.addConstr(s <= float(r["hard_cap"]), name=f"win_cap[{wid}]")

        # 5) mix
        p_by_dim = dict(zip(d["mix_targets"]["mix_dimension_id"].astype(str), d["mix_targets"]["max_share"].astype(float)))
        dim_to_flags: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        for _, r in d["mix_flags"].iterrows():
            dim_to_flags[str(r["mix_dimension_id"])].append((str(r["decision_id"]), int(r["flag"])))
        for dim, flags in dim_to_flags.items():
            p = float(p_by_dim[dim])
            expr = gp.quicksum((flag - p) * self.x[did] for did, flag in flags)
            self.model.addConstr(expr <= 0.0, name=f"mix[{dim}]")

        # 6) coverage
        cov_min = dict(zip(d["coverage_groups"]["coverage_group_id"].astype(str), d["coverage_groups"]["min_selected"].astype(int)))
        g_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["coverage_members"].iterrows():
            g_to_members[str(r["coverage_group_id"])].append(str(r["decision_id"]))
        for gid, k in cov_min.items():
            self.model.addConstr(gp.quicksum(self.x[m] for m in g_to_members.get(gid, [])) >= int(k), name=f"cov[{gid}]")

        # 7) conflicts
        conf_ids = d["conflict_groups"]["conflict_group_id"].astype(str).tolist()
        c_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["conflict_members"].iterrows():
            c_to_members[str(r["conflict_group_id"])].append(str(r["decision_id"]))
        for cid in conf_ids:
            self.model.addConstr(gp.quicksum(self.x[m] for m in c_to_members.get(cid, [])) <= 1, name=f"conf[{cid}]")

        # 8) dependencies
        parent_to_children: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["dependencies"].iterrows():
            parent_to_children[str(r["parent_id"])].append(str(r["child_id"]))
        for parent, children in parent_to_children.items():
            self.model.addConstr(self.x[parent] <= gp.quicksum(self.x[c] for c in children), name=f"dep[{parent}]")

        # 9) exact-choice (may be empty)
        exact_k = dict(zip(d["exact_choice_groups"]["exact_group_id"].astype(str), d["exact_choice_groups"]["required_selected"].astype(int)))
        x_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["exact_choice_members"].iterrows():
            x_to_members[str(r["exact_group_id"])].append(str(r["decision_id"]))
        for xid, k in exact_k.items():
            self.model.addConstr(gp.quicksum(self.x[m] for m in x_to_members.get(xid, [])) == int(k), name=f"exact[{xid}]")

        # 10) caps
        cap_k = dict(zip(d["cardinality_caps"]["cap_group_id"].astype(str), d["cardinality_caps"]["max_selected"].astype(int)))
        k_to_members: Dict[str, List[str]] = defaultdict(list)
        for _, r in d["cardinality_cap_members"].iterrows():
            k_to_members[str(r["cap_group_id"])].append(str(r["decision_id"]))
        for kid, k in cap_k.items():
            self.model.addConstr(gp.quicksum(self.x[m] for m in k_to_members.get(kid, [])) <= int(k), name=f"cap[{kid}]")

        # 11) redundant bounds (optional; usually empty / redundant under binary)
        if include_redundant_bounds and len(d["redundant_bounds"]) > 0:
            for _, r in d["redundant_bounds"].iterrows():
                did = str(r["decision_id"])
                ub = float(r["upper_bound"])
                self.model.addConstr(self.x[did] <= ub, name=f"rb[{did}]")

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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance_dir", type=str, help="Instance directory (containing instance.json and data/)")
    parser.add_argument("--check_opt", type=float, default=None, help="Check optimal value (e.g. -357544.3115)")
    parser.add_argument("--tol", type=float, default=1e-4, help="Tolerance for optimal value check (default 1e-4)")
    parser.add_argument("--time_limit", type=float, default=None, help="Time limit for solving (seconds)")
    parser.add_argument("--mip_gap", type=float, default=0.0, help="MIPGap (default 0.0)")
    parser.add_argument("--threads", type=int, default=None, help="Number of Gurobi threads")
    parser.add_argument("--quiet", action="store_true", help="Quiet solving")
    args = parser.parse_args()

    solver = Bab2Solver(args.instance_dir)
    solver.load_data()
    solver.build_model(include_redundant_bounds=False)
    res = solver.solve(
        time_limit_sec=args.time_limit,
        mip_gap=args.mip_gap,
        threads=args.threads,
        verbose=not args.quiet,
    )

    print(f"Solve status: {res.status}")
    if res.obj_val is None:
        raise SystemExit("No valid solution found (infeasible or solver failed)")

    print(f"Objective value: {res.obj_val:.6f}")

    if args.check_opt is not None:
        diff = abs(res.obj_val - float(args.check_opt))
        ok = diff <= float(args.tol)
        print(f"Check optimal value: {float(args.check_opt):.6f}")
        print(f"Difference: {diff:.6g} (tol={args.tol})")
        if not ok:
            raise SystemExit("Optimal value check failed: solver result is inconsistent with expectation")
        print("Optimal value check passed")


if __name__ == "__main__":
    main()