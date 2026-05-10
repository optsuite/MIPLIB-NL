"""
sing326 Solver (Service Coverage with Policy Identities)

Reads CSVs under instances/sing326/data (or generated data directory), reconstructs and solves the optimization model using Gurobi.

Model Summary (Business-oriented):
- Exact coverage alignment is required for each time slot.
- Coverage sources: adjustable coverage segments (if enabled, take amount within bounds and charge per unit), discrete actions (if enabled, pay fixed cost and contribute fixed amount across multiple slots), expensive fallback (continuous amount, high unit price).
- There are also many internal compliance rules: signed balance identities for binary nodes.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple

import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def _read_csv(path: str) -> pd.DataFrame:
    # Critical: ref_id for aux allows empty strings, should not be read as NaN
    return pd.read_csv(path, keep_default_na=False)


@dataclass(frozen=True)
class SolveResult:
    status: int
    status_name: str
    objective: Optional[float]
    expected_objective: Optional[float]
    abs_gap: Optional[float]
    rel_gap: Optional[float]


class Sing326Solver:
    def __init__(self, instance_folder: str, data_subdir: str = "data"):
        self.instance_folder = instance_folder
        self.data_folder = os.path.join(instance_folder, data_subdir)

        self.slots = None
        self.segments = None
        self.actions = None
        self.action_contributions = None
        self.fallback = None
        self.nodes = None
        self.equations = None
        self.equation_terms = None

        self.model: Optional[gp.Model] = None

        self._segment_to_switch_node: Dict[str, str] = {}
        self._action_to_switch_node: Dict[str, str] = {}

    def load(self) -> None:
        slots_path = os.path.join(self.data_folder, "slots.csv")
        segments_path = os.path.join(self.data_folder, "segments.csv")
        actions_path = os.path.join(self.data_folder, "actions.csv")
        action_contrib_path = os.path.join(self.data_folder, "action_contributions.csv")
        fallback_path = os.path.join(self.data_folder, "fallback.csv")
        nodes_path = os.path.join(self.data_folder, "nodes.csv")
        equations_path = os.path.join(self.data_folder, "equations.csv")
        equation_terms_path = os.path.join(self.data_folder, "equation_terms.csv")

        for p in [
            slots_path,
            segments_path,
            actions_path,
            action_contrib_path,
            fallback_path,
            nodes_path,
            equations_path,
            equation_terms_path,
        ]:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Data file not found: {p}")

        self.slots = _read_csv(slots_path)
        self.segments = _read_csv(segments_path)
        self.actions = _read_csv(actions_path)
        self.action_contributions = _read_csv(action_contrib_path)
        self.fallback = _read_csv(fallback_path)
        self.nodes = _read_csv(nodes_path)
        self.equations = _read_csv(equations_path)
        self.equation_terms = _read_csv(equation_terms_path)

        # dtype + basic normalization
        self.slots["requirement"] = self.slots["requirement"].astype(float)
        for c in ["threshold_low", "threshold_high", "unit_price"]:
            self.segments[c] = self.segments[c].astype(float)
        self.actions["fixed_price"] = self.actions["fixed_price"].astype(float)
        self.action_contributions["contribution"] = self.action_contributions["contribution"].astype(float)
        self.nodes["price"] = self.nodes["price"].astype(float)
        self.equations["rhs"] = self.equations["rhs"].astype(int)
        self.equation_terms["sign"] = self.equation_terms["sign"].astype(int)

        if self.fallback.shape[0] != 1:
            raise ValueError("fallback.csv must contain exactly one row")
        self.fallback_unit_price = float(self.fallback["unit_price"].iloc[0])

        # 1-1 mapping: segment_id -> switch node_id
        seg_switch = self.nodes[self.nodes["node_kind"] == "segment_switch"][["node_id", "ref_id"]]
        if seg_switch["ref_id"].duplicated().any():
            raise ValueError("Duplicate ref_id for segment_switch in nodes.csv, cannot form 1-1 mapping")
        self._segment_to_switch_node = dict(zip(seg_switch["ref_id"], seg_switch["node_id"]))

        # 1-1 mapping: action_id -> switch node_id
        act_switch = self.nodes[self.nodes["node_kind"] == "action_switch"][["node_id", "ref_id"]]
        if act_switch["ref_id"].duplicated().any():
            raise ValueError("Duplicate ref_id for action_switch in nodes.csv, cannot form 1-1 mapping")
        self._action_to_switch_node = dict(zip(act_switch["ref_id"], act_switch["node_id"]))

        # Integrity check (Most important: modeler should not 'guess' missing mappings)
        missing_seg = set(self.segments["segment_id"]) - set(self._segment_to_switch_node)
        if missing_seg:
            raise ValueError(f"Segments exist but missing corresponding segment_switch nodes: {list(sorted(missing_seg))[:5]} ...")
        missing_act = set(self.actions["action_id"]) - set(self._action_to_switch_node)
        if missing_act:
            raise ValueError(f"Actions exist but missing corresponding action_switch nodes: {list(sorted(missing_act))[:5]} ...")

    def build_model(
        self,
        time_limit: Optional[float] = None,
        mip_gap: Optional[float] = None,
        threads: Optional[int] = None,
        log_to_console: bool = True,
    ) -> gp.Model:
        if self.slots is None:
            raise RuntimeError("Please call load() first")

        m = gp.Model("sing326")
        m.Params.LogToConsole = 1 if log_to_console else 0
        if time_limit is not None:
            m.Params.TimeLimit = float(time_limit)
        if mip_gap is not None:
            m.Params.MIPGap = float(mip_gap)
        if threads is not None:
            m.Params.Threads = int(threads)

        # Decision: all policy nodes are binary (including segment_switch / action_switch / aux)
        node_ids = self.nodes["node_id"].tolist()
        b = m.addVars(node_ids, vtype=GRB.BINARY, name="b")

        # Adjustable coverage segments: continuous coverage amount
        seg_ids = self.segments["segment_id"].tolist()
        x = m.addVars(seg_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="seg")

        # Fallback amount per slot
        slot_ids = self.slots["slot_id"].tolist()
        f = m.addVars(slot_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="fb")

        m.update()

        # Coverage segments: must be within bounds when enabled, otherwise 0
        seg_df = self.segments.set_index("segment_id")
        for seg_id in seg_ids:
            switch_node = self._segment_to_switch_node[seg_id]
            low = float(seg_df.at[seg_id, "threshold_low"])
            high = float(seg_df.at[seg_id, "threshold_high"])
            m.addConstr(x[seg_id] <= high * b[switch_node], name=f"seg_high[{seg_id}]")
            m.addConstr(x[seg_id] >= low * b[switch_node], name=f"seg_low[{seg_id}]")

        # Exact alignment per slot (segment + actions + fallback)
        seg_by_slot = self.segments.groupby("slot_id")["segment_id"].apply(list).to_dict()
        contrib_agg = (
            self.action_contributions[["slot_id", "action_id", "contribution"]]
            .groupby("slot_id", sort=False)
            .agg({"action_id": list, "contribution": list})
        )
        contrib_by_slot = {
            slot_id: list(zip(row["action_id"], [float(v) for v in row["contribution"]]))
            for slot_id, row in contrib_agg.iterrows()
        }
        req = self.slots.set_index("slot_id")["requirement"].to_dict()

        for slot_id in slot_ids:
            expr = gp.LinExpr()
            for seg_id in seg_by_slot.get(slot_id, []):
                expr += x[seg_id]
            for act_id, c in contrib_by_slot.get(slot_id, []):
                switch_node = self._action_to_switch_node[act_id]
                expr += float(c) * b[switch_node]
            expr += f[slot_id]
            m.addConstr(expr == float(req[slot_id]), name=f"slot_balance[{slot_id}]")

        # Policy identities: sum(sign * b[node]) == rhs
        terms_agg = (
            self.equation_terms[["eq_id", "node_id", "sign"]]
            .groupby("eq_id", sort=False)
            .agg({"node_id": list, "sign": list})
        )
        terms_by_eq = {
            eq_id: list(zip(row["node_id"], [int(v) for v in row["sign"]]))
            for eq_id, row in terms_agg.iterrows()
        }
        rhs = self.equations.set_index("eq_id")["rhs"].astype(int).to_dict()
        for eq_id, eq_rhs in rhs.items():
            term_list = terms_by_eq.get(eq_id, [])
            if not term_list:
                raise ValueError(f"eq_id={eq_id} exists in equations.csv but has no entries in equation_terms.csv")
            expr = gp.LinExpr()
            for nid, sgn in term_list:
                if sgn not in (-1, 1):
                    raise ValueError(f"equation_terms.sign not ±1: eq_id={eq_id}, node_id={nid}, sign={sgn}")
                expr += int(sgn) * b[nid]
            m.addConstr(expr == int(eq_rhs), name=f"policy[{eq_id}]")

        # Objective: segment variable cost + action fixed cost + node additional fixed cost + fallback cost
        obj = gp.LinExpr()
        seg_unit_price = self.segments.set_index("segment_id")["unit_price"].astype(float).to_dict()
        for seg_id in seg_ids:
            obj += float(seg_unit_price[seg_id]) * x[seg_id]

        act_fixed = self.actions.set_index("action_id")["fixed_price"].astype(float).to_dict()
        for act_id, price in act_fixed.items():
            switch_node = self._action_to_switch_node[act_id]
            obj += float(price) * b[switch_node]

        # nodes.price (usually non-zero on aux; others usually 0, but unified coding allowed)
        node_price = self.nodes.set_index("node_id")["price"].astype(float).to_dict()
        for nid, price in node_price.items():
            if abs(float(price)) > 0.0:
                obj += float(price) * b[nid]

        obj += float(self.fallback_unit_price) * gp.quicksum(f[slot_id] for slot_id in slot_ids)
        m.setObjective(obj, GRB.MINIMIZE)

        self.model = m
        return m

    def solve(
        self,
        expected_objective: Optional[float] = None,
        tol_abs: float = 1e-4,
        tol_rel: float = 1e-9,
    ) -> SolveResult:
        if self.model is None:
            raise RuntimeError("Please call build_model() first")

        self.model.optimize()
        status = int(self.model.Status)
        status_name = {
            GRB.OPTIMAL: "OPTIMAL",
            GRB.INFEASIBLE: "INFEASIBLE",
            GRB.TIME_LIMIT: "TIME_LIMIT",
            GRB.INTERRUPTED: "INTERRUPTED",
            GRB.UNBOUNDED: "UNBOUNDED",
        }.get(status, str(status))

        obj = None
        abs_gap = None
        rel_gap = None
        if self.model.SolCount > 0:
            obj = float(self.model.ObjVal)
            if expected_objective is not None:
                abs_gap = abs(obj - float(expected_objective))
                rel_gap = abs_gap / max(1.0, abs(float(expected_objective)))
                if abs_gap > tol_abs and rel_gap > tol_rel:
                    raise AssertionError(
                        f"Objective verification failed: obtained {obj:.5f}, expected {expected_objective:.5f}, "
                        f"abs_gap={abs_gap:.5g}, rel_gap={rel_gap:.5g}"
                    )

        return SolveResult(
            status=status,
            status_name=status_name,
            objective=obj,
            expected_objective=expected_objective,
            abs_gap=abs_gap,
            rel_gap=rel_gap,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="sing326: read CSV, build Gurobi model, solve, and verify objective.")
    parser.add_argument(
        "--instance",
        type=str,
        default=os.path.join("instances", "sing326"),
        help="Instance directory (containing instance.json and data/)",
    )
    parser.add_argument(
        "--data-subdir",
        type=str,
        default="data",
        help="Data subdirectory name (default 'data'; can point to generated data directory)",
    )
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--mip-gap", type=float, default=None)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--no-log", action="store_true")
    parser.add_argument(
        "--expected",
        type=float,
        default=7753674.85376,
        help="Expected optimal objective value (for self-verification)",
    )
    args = parser.parse_args()

    solver = Sing326Solver(args.instance, data_subdir=args.data_subdir)
    solver.load()
    solver.build_model(
        time_limit=args.time_limit,
        mip_gap=args.mip_gap,
        threads=args.threads,
        log_to_console=not args.no_log,
    )
    result = solver.solve(expected_objective=args.expected)
    print(
        f"Status={result.status_name}, Obj={result.objective}, "
        f"Expected={result.expected_objective}, AbsGap={result.abs_gap}, RelGap={result.rel_gap}"
    )


if __name__ == "__main__":
    main()