"""
tanglegram6 Solver (Orientation Harmonization with Pairwise Evidence)

Reads CSV data under instances/tanglegram6/data, builds and solves a 0-1 optimization model using Gurobi.

Usage:
  python solver.py instances/tanglegram6
  python solver.py instances/tanglegram6 data_generated_20260127_120000
"""

from __future__ import annotations

import csv
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Tuple

import gurobipy as gp
from gurobipy import GRB


@dataclass(frozen=True)
class Evidence:
    evidence_id: int
    u: int
    v: int
    expected_parity: str  # 'same' | 'opposite' (decoded via evidence_semantics.csv)
    weight: float


class OrientationHarmonizationSolver:
    """
    Business explanation:
    - Each entity chooses a binary "reference orientation" (0/1).
    - Each piece of evidence requires ends to be co-oriented (co_move) or counter-oriented (counter_move).
    - Violating evidence incurs a penalty of weight; the goal is to minimize total penalty.
    """

    def __init__(self, instance_folder: str, data_subdir: str = "data"):
        self.instance_folder = instance_folder
        self.data_dir = os.path.join(instance_folder, data_subdir)

        self.num_entities: int = 0
        self.violation_unit_cost: float = 1.0
        self.expected_optimal_value: float | None = None

        self.evidence: List[Evidence] = []

        self.model = gp.Model("OrientationHarmonization")
        self.s: Dict[int, gp.Var] = {}
        self.z: Dict[int, gp.Var] = {}

        self.obj_val: float | None = None

    def _read_csv(self, path: str) -> List[dict]:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def load_data(self) -> None:
        print("Loading data...")

        json_path = os.path.join(self.instance_folder, "instance.json")
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Not found: {json_path}")

        with open(json_path, "r", encoding="utf-8-sig") as f:
            config = json.load(f)

        params = config.get("parameters", {})
        self.violation_unit_cost = float(params.get("violation_unit_cost", 1.0))

        opt = config.get("optimal_value")
        if opt is not None and str(opt).strip() != "":
            self.expected_optimal_value = float(opt)

        entities_path = os.path.join(self.data_dir, "entities.csv")
        evidence_path = os.path.join(self.data_dir, "evidence.csv")
        semantics_path = os.path.join(self.data_dir, "evidence_semantics.csv")

        if not os.path.exists(entities_path):
            raise FileNotFoundError(f"Not found: {entities_path}")
        if not os.path.exists(evidence_path):
            raise FileNotFoundError(f"Not found: {evidence_path}")
        if not os.path.exists(semantics_path):
            raise FileNotFoundError(f"Not found: {semantics_path}")

        ent_rows = self._read_csv(entities_path)
        entity_keys = [r["entity_key"] for r in ent_rows]
        if len(entity_keys) != len(set(entity_keys)):
            raise ValueError("entity_key in entities.csv is not unique")
        key_to_idx = {k: i for i, k in enumerate(entity_keys)}
        self.num_entities = len(entity_keys)

        sem_rows = self._read_csv(semantics_path)
        semantics = {}
        for r in sem_rows:
            et = r["effect_type"].strip()
            ad = r["agreement_domain"].strip()
            ep = r["expected_parity"].strip()
            if ep not in ("same", "opposite"):
                raise ValueError(f"Invalid expected_parity in evidence_semantics.csv: {ep}")
            semantics[(et, ad)] = ep

        ev_rows = self._read_csv(evidence_path)
        self.evidence = []
        for r in ev_rows:
            eid = int(r["evidence_id"])
            uk = r["u_entity_key"].strip()
            vk = r["v_entity_key"].strip()
            if uk not in key_to_idx or vk not in key_to_idx:
                raise ValueError(f"evidence_id={eid} references unknown entity_key: {uk}, {vk}")
            u = key_to_idx[uk]
            v = key_to_idx[vk]
            if u == v:
                raise ValueError(f"evidence_id={eid} has self-loop (u==v)")

            et = r["effect_type"].strip()
            ad = r["agreement_domain"].strip()
            if (et, ad) not in semantics:
                raise ValueError(f"(effect_type, agreement_domain) for evidence_id={eid} not defined in semantics table: {(et, ad)}")
            expected_parity = semantics[(et, ad)]

            w = float(r["weight"])
            self.evidence.append(Evidence(eid, u, v, expected_parity, w))

        print(f"  Num entities: {self.num_entities}")
        print(f"  Num evidence: {len(self.evidence)}")
        print(f"  violation_unit_cost: {self.violation_unit_cost}")
        if self.expected_optimal_value is not None:
            print(f"  Expected optimal value (for verification): {self.expected_optimal_value:g}")
        print("Data loading completed.\n")

    def build_model(self) -> None:
        print("Building optimization model...")

        # Variables: one binary orientation s_v per entity
        for v in range(self.num_entities):
            self.s[v] = self.model.addVar(vtype=GRB.BINARY, name=f"s[{v}]")

        # Variables: one binary violation indicator z_e per evidence
        for e in self.evidence:
            self.z[e.evidence_id] = self.model.addVar(vtype=GRB.BINARY, name=f"z[{e.evidence_id}]")

        self.model.update()

        # Objective: min sum w_e * z_e * violation_unit_cost
        obj = gp.quicksum(e.weight * self.z[e.evidence_id] for e in self.evidence) * self.violation_unit_cost
        self.model.setObjective(obj, GRB.MINIMIZE)

        # Constraints: linearize "compatibility" by relation
        for e in self.evidence:
            u, v = e.u, e.v
            z = self.z[e.evidence_id]

            if e.expected_parity == "same":
                # z >= s_u - s_v
                # z >= s_v - s_u
                self.model.addConstr(z >= self.s[u] - self.s[v], name=f"co_a[{e.evidence_id}]")
                self.model.addConstr(z >= self.s[v] - self.s[u], name=f"co_b[{e.evidence_id}]")
            else:
                # expected opposite: violate when equal
                # z >= s_u + s_v - 1
                # z >= 1 - s_u - s_v
                self.model.addConstr(z >= self.s[u] + self.s[v] - 1, name=f"ct_a[{e.evidence_id}]")
                self.model.addConstr(z >= 1 - self.s[u] - self.s[v], name=f"ct_b[{e.evidence_id}]")

        self.model.update()
        print(f"  Num variables: {self.model.NumVars} (s={len(self.s)}, z={len(self.z)})")
        print(f"  Num constrs: {self.model.NumConstrs}")
        print("Model building completed.\n")

    def solve(self, time_limit_sec: int | None = None) -> bool:
        print("=" * 60)
        print("Starting solve...")
        print("=" * 60)

        if time_limit_sec is not None:
            self.model.Params.TimeLimit = time_limit_sec
        self.model.Params.OutputFlag = 1
        self.model.Params.MIPGap = 0.0

        self.model.optimize()

        if self.model.Status == GRB.OPTIMAL:
            self.obj_val = float(self.model.ObjVal)
            print(f"\nOptimal objective value: {self.obj_val:g}")
            return True

        if self.model.Status == GRB.TIME_LIMIT and self.model.SolCount > 0:
            self.obj_val = float(self.model.ObjVal)
            print(f"\nTime limit reached, current best: {self.obj_val:g}")
            return True

        if self.model.Status == GRB.INFEASIBLE:
            print("\nModel is infeasible.")
            return False

        print(f"\nSolver status abnormal: {self.model.Status}")
        return False

    def verify_optimal_value(self, tol: float = 1e-6) -> None:
        if self.expected_optimal_value is None or self.obj_val is None:
            return
        if abs(self.obj_val - self.expected_optimal_value) > tol:
            raise AssertionError(
                f"Optimal value verification failed: found {self.obj_val:g}, expected {self.expected_optimal_value:g}"
            )
        print(f"Optimal value verification passed: {self.obj_val:g} matches expected.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python solver.py <instance_folder> [data_subdir]")
        print("Example: python solver.py instances/tanglegram6")
        print("Example: python solver.py instances/tanglegram6 data_generated_20260127_120000")
        sys.exit(1)

    instance_folder = sys.argv[1]
    data_subdir = sys.argv[2] if len(sys.argv) >= 3 else "data"

    if not os.path.exists(instance_folder):
        print(f"Error: Instance directory does not exist: {instance_folder}")
        sys.exit(1)

    try:
        solver = OrientationHarmonizationSolver(instance_folder, data_subdir=data_subdir)
        solver.load_data()
        solver.build_model()
        ok = solver.solve()
        if not ok:
            sys.exit(1)
        solver.verify_optimal_value()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()