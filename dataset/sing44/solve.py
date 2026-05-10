"""
sing44 solver (Service Coverage with Policy Identities + Multi-option Fallback)

Reads CSVs under instances/sing44/data (or generated data directory), rebuilds and solves the optimization model using Gurobi.

Key difference from sing326:
- Fallback is not a single expensive channel, but 'multiple fallback options per slot', each with its own unit_price;
  Therefore, fallback decisions are modeled as continuous variables by fallback_id (option) and aggregated into the balance for the corresponding slot.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def _read_csv(path: str) -> pd.DataFrame:
    # Key: ref_id in aux allows empty strings, must not be read as NaN
    return pd.read_csv(path, keep_default_na=False)


@dataclass(frozen=True)
class SolveResult:
    status: int
    status_name: str
    objective: Optional[float]
    expected_objective: Optional[float]
    abs_gap: Optional[float]
    rel_gap: Optional[float]


class Sing44Solver:
    def __init__(self, instance_folder: str, data_subdir: str = "data"):
        self.instance_folder = instance_folder
        self.data_folder = os.path.join(instance_folder, data_subdir)

        self.slots = None
        self.segments = None
        self.actions = None
        self.action_contributions = None
        self.fallback = None
        self.fallback_bounds = None
        self.nodes = None
        self.equations = None
        self.equation_terms = None

        self.model: Optional[gp.Model] = None

        self._segment_to_switch_node: Dict[str, str] = {}
        self._action_to_switch_node: Dict[str, str] = {}

    def load(self) -> None:
        def p(name: str) -> str:
            return os.path.join(self.data_folder, name)

        needed = [
            "slots.csv",
            "segments.csv",
            "actions.csv",
            "action_contributions.csv",
            "fallback.csv",
            "fallback_bounds.csv",
            "nodes.csv",
            "equations.csv",
            "equation_terms.csv",
        ]
        # fallback_bounds.csv may not exist in augmented instances; treat as optional
        must_exist = [n for n in needed if n != "fallback_bounds.csv"]
        for name in must_exist:
            path = p(name)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Data file not found: {path}")

        self.slots = _read_csv(p("slots.csv"))
        self.segments = _read_csv(p("segments.csv"))
        self.actions = _read_csv(p("actions.csv"))
        self.action_contributions = _read_csv(p("action_contributions.csv"))
        self.fallback = _read_csv(p("fallback.csv"))
        fb_bounds_path = p("fallback_bounds.csv")
        if os.path.exists(fb_bounds_path):
            self.fallback_bounds = _read_csv(fb_bounds_path)
        else:
            self.fallback_bounds = pd.DataFrame(columns=["fallback_id", "min_amount", "max_amount"])
        self.nodes = _read_csv(p("nodes.csv"))
        self.equations = _read_csv(p("equations.csv"))
        self.equation_terms = _read_csv(p("equation_terms.csv"))

        # dtype
        self.slots["requirement"] = self.slots["requirement"].astype(float)
        for c in ["threshold_low", "threshold_high", "unit_price"]:
            self.segments[c] = self.segments[c].astype(float)
        self.actions["fixed_price"] = self.actions["fixed_price"].astype(float)
        self.action_contributions["contribution"] = self.action_contributions["contribution"].astype(float)
        self.fallback["unit_price"] = self.fallback["unit_price"].astype(float)
        if not self.fallback_bounds.empty:
            self.fallback_bounds["min_amount"] = self.fallback_bounds["min_amount"].astype(float)
            self.fallback_bounds["max_amount"] = self.fallback_bounds["max_amount"].astype(float)
        self.nodes["price"] = self.nodes["price"].astype(float)
        self.equations["rhs"] = self.equations["rhs"].astype(int)
        self.equation_terms["sign"] = self.equation_terms["sign"].astype(int)

        # segment/action switch maps
        seg_switch = self.nodes[self.nodes["node_kind"] == "segment_switch"][["node_id", "ref_id"]]
        if seg_switch["ref_id"].duplicated().any():
            raise ValueError("Duplicate ref_id for segment_switch in nodes.csv")
        self._segment_to_switch_node = dict(zip(seg_switch["ref_id"], seg_switch["node_id"]))

        act_switch = self.nodes[self.nodes["node_kind"] == "action_switch"][["node_id", "ref_id"]]
        if act_switch["ref_id"].duplicated().any():
            raise ValueError("Duplicate ref_id for action_switch in nodes.csv")
        self._action_to_switch_node = dict(zip(act_switch["ref_id"], act_switch["node_id"]))

        # completeness checks
        missing_seg = set(self.segments["segment_id"]) - set(self._segment_to_switch_node)
        if missing_seg:
            raise ValueError(f"segments missing segment_switch node mapping: {list(sorted(missing_seg))[:5]} ...")
        missing_act = set(self.actions["action_id"]) - set(self._action_to_switch_node)
        if missing_act:
            raise ValueError(f"actions missing action_switch node mapping: {list(sorted(missing_act))[:5]} ...")

        # fallback slots must exist
        slotset = set(self.slots["slot_id"])
        bad_fb = set(self.fallback["slot_id"]) - slotset
        if bad_fb:
            raise ValueError(f"fallback.csv references non-existent slot_id: {list(sorted(bad_fb))[:5]} ...")

        # fallback_bounds must reference existing fallback_id
        if not self.fallback_bounds.empty:
            fbset = set(self.fallback["fallback_id"])
            bad_ids = set(self.fallback_bounds["fallback_id"]) - fbset
            if bad_ids:
                raise ValueError(f"fallback_bounds.csv references non-existent fallback_id: {list(sorted(bad_ids))[:5]} ...")

    def build_model(
        self,
        time_limit: Optional[float] = None,
        mip_gap: Optional[float] = None,
        threads: Optional[int] = None,
        log_to_console: bool = True,
    ) -> gp.Model:
        if self.slots is None:
            raise RuntimeError("Please call load() first")

        m = gp.Model("sing44")
        m.Params.LogToConsole = 1 if log_to_console else 0
        if time_limit is not None:
            m.Params.TimeLimit = float(time_limit)
        if mip_gap is not None:
            m.Params.MIPGap = float(mip_gap)
        if threads is not None:
            m.Params.Threads = int(threads)

        # policy nodes
        node_ids = self.nodes["node_id"].tolist()
        b = m.addVars(node_ids, vtype=GRB.BINARY, name="b")

        # segments delivered amount
        seg_ids = self.segments["segment_id"].tolist()
        x = m.addVars(seg_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="seg")

        # fallback options purchased amount
        fb_ids = self.fallback["fallback_id"].tolist()
        f = m.addVars(fb_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="fb")
        # apply optional bounds for a subset
        if self.fallback_bounds is not None and not self.fallback_bounds.empty:
            for _, row in self.fallback_bounds.iterrows():
                fid = row["fallback_id"]
                f[fid].LB = float(row["min_amount"])
                f[fid].UB = float(row["max_amount"])

        m.update()

        # segment thresholds
        seg_df = self.segments.set_index("segment_id")
        for seg_id in seg_ids:
            switch_node = self._segment_to_switch_node[seg_id]
            low = float(seg_df.at[seg_id, "threshold_low"])
            high = float(seg_df.at[seg_id, "threshold_high"])
            m.addConstr(x[seg_id] <= high * b[switch_node], name=f"seg_high[{seg_id}]")
            m.addConstr(x[seg_id] >= low * b[switch_node], name=f"seg_low[{seg_id}]")

        # slot exact balance
        slot_ids = self.slots["slot_id"].tolist()
        req = self.slots.set_index("slot_id")["requirement"].to_dict()

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

        fb_by_slot = self.fallback.groupby("slot_id")["fallback_id"].apply(list).to_dict()

        for slot_id in slot_ids:
            expr = gp.LinExpr()
            for seg_id in seg_by_slot.get(slot_id, []):
                expr += x[seg_id]
            for act_id, c in contrib_by_slot.get(slot_id, []):
                expr += float(c) * b[self._action_to_switch_node[act_id]]
            for fb_id in fb_by_slot.get(slot_id, []):
                expr += f[fb_id]
            m.addConstr(expr == float(req[slot_id]), name=f"slot_balance[{slot_id}]")

        # policy identities
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
                raise ValueError(f"eq_id={eq_id} exists in equations.csv but has no corresponding entries in equation_terms.csv")
            expr = gp.LinExpr()
            for nid, sgn in term_list:
                if sgn not in (-1, 1):
                    raise ValueError(f"equation_terms.sign is not ±1: eq_id={eq_id}, node_id={nid}, sign={sgn}")
                expr += int(sgn) * b[nid]
            m.addConstr(expr == int(eq_rhs), name=f"policy[{eq_id}]")

        # objective
        obj = gp.LinExpr()

        seg_unit_price = self.segments.set_index("segment_id")["unit_price"].astype(float).to_dict()
        for seg_id in seg_ids:
            obj += float(seg_unit_price[seg_id]) * x[seg_id]

        act_fixed = self.actions.set_index("action_id")["fixed_price"].astype(float).to_dict()
        for act_id, price in act_fixed.items():
            obj += float(price) * b[self._action_to_switch_node[act_id]]

        node_price = self.nodes.set_index("node_id")["price"].astype(float).to_dict()
        for nid, price in node_price.items():
            if abs(float(price)) > 0.0:
                obj += float(price) * b[nid]

        fb_price = self.fallback.set_index("fallback_id")["unit_price"].astype(float).to_dict()
        for fb_id in fb_ids:
            obj += float(fb_price[fb_id]) * f[fb_id]

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
    parser = argparse.ArgumentParser(description="sing44: read CSV, build Gurobi model, solve, and verify objective.")
    parser.add_argument(
        "--instance",
        type=str,
        default=os.path.join("instances", "sing44"),
        help="Instance directory (contains instance.json and data/)",
    )
    parser.add_argument(
        "--data-subdir",
        type=str,
        default="data",
        help="Data subdirectory name (default data; can point to generated data)",
    )
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--mip-gap", type=float, default=None)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--no-log", action="store_true")
    parser.add_argument("--no-verify", action="store_true", help="Do not verify objective value (for augmented instances)")
    parser.add_argument(
        "--expected",
        type=float,
        default=8128831.1772,
        help="Expected optimal objective value (for self-verification)",
    )
    args = parser.parse_args()

    solver = Sing44Solver(args.instance, data_subdir=args.data_subdir)
    solver.load()
    solver.build_model(
        time_limit=args.time_limit,
        mip_gap=args.mip_gap,
        threads=args.threads,
        log_to_console=not args.no_log,
    )
    expected = None if args.no_verify else args.expected
    result = solver.solve(expected_objective=expected)
    print(
        f"Status={result.status_name}, Obj={result.objective}, "
        f"Expected={result.expected_objective}, AbsGap={result.abs_gap}, RelGap={result.rel_gap}"
    )


if __name__ == "__main__":
    main()