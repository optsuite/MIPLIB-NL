"""
Protein design solver (local + pairwise microstate selection with consistency).

Hard-mode data:
- Microstate identity is the pair (tag_a, tag_b) per unit.
- Option energies are reconstructed as value(base_term) + value(adj_term) via energy_terms.csv.
"""

from __future__ import annotations

import os
import sys

import gurobipy as gp
import pandas as pd
from gurobipy import GRB


class ProteinDesignSolver:
    def __init__(self, instance_folder: str):
        self.instance_folder = instance_folder
        self.data_folder = os.path.join(instance_folder, "data")
        self.model = gp.Model("ProteinDesign")

        self.sites: pd.DataFrame | None = None
        self.pairs: pd.DataFrame | None = None
        self.site_options: pd.DataFrame | None = None
        self.pair_options: pd.DataFrame | None = None
        self.energy_terms: pd.DataFrame | None = None

        self.term_value: dict[str, float] = {}

        self.x_site: dict[int, gp.Var] = {}
        self.x_pair: dict[int, gp.Var] = {}
        self.sig_index: dict[str, dict[tuple[str, str], int]] = {}
        self.unit_index: dict[str, gp.Var] = {}

        self.objective_value: float | None = None

    def load_data(self):
        print("Loading data...")
        self.sites = pd.read_csv(os.path.join(self.data_folder, "sites.csv"), dtype={"unit_id": str})
        self.pairs = pd.read_csv(
            os.path.join(self.data_folder, "pairs.csv"),
            dtype={"bundle_id": str, "left_unit": str, "right_unit": str},
        )
        self.site_options = pd.read_csv(
            os.path.join(self.data_folder, "site_options.csv"),
            dtype={"unit_id": str, "tag_a": str, "tag_b": str, "base_term": str, "adj_term": str, "status_code": str},
        )
        self.pair_options = pd.read_csv(
            os.path.join(self.data_folder, "pair_options.csv"),
            dtype={
                "bundle_id": str,
                "left_tag_a": str,
                "left_tag_b": str,
                "right_tag_a": str,
                "right_tag_b": str,
                "base_term": str,
                "adj_term": str,
                "status_code": str,
            },
        )
        self.energy_terms = pd.read_csv(
            os.path.join(self.data_folder, "energy_terms.csv"),
            dtype={"term_key": str, "kind": str},
        )

        if self.energy_terms["term_key"].duplicated().any():
            raise ValueError("energy_terms.csv must have unique term_key.")

        self.term_value = {str(k): float(v) for k, v in zip(self.energy_terms["term_key"], self.energy_terms["value"])}

        def row_energy(df: pd.DataFrame) -> pd.Series:
            base = df["base_term"].map(self.term_value)
            adj = df["adj_term"].map(self.term_value)
            if base.isna().any() or adj.isna().any():
                missing = set(df.loc[base.isna(), "base_term"].tolist()) | set(df.loc[adj.isna(), "adj_term"].tolist())
                raise ValueError(f"Missing term_key(s) in energy_terms.csv: {sorted(missing)[:10]}")
            return base.astype(float) + adj.astype(float)

        self.site_options = self.site_options.copy()
        self.pair_options = self.pair_options.copy()
        self.site_options["energy"] = row_energy(self.site_options)
        self.pair_options["energy"] = row_energy(self.pair_options)

    def build_model(self):
        if self.sites is None or self.pairs is None or self.site_options is None or self.pair_options is None:
            raise RuntimeError("Call load_data() before build_model().")

        self.model.setParam("OutputFlag", 0)
        self.model.setParam("TimeLimit", 600)

        print("Building model...")
        self.x_site = {int(i): self.model.addVar(vtype=GRB.BINARY, name=f"x_site[{i}]") for i in self.site_options.index}
        self.x_pair = {int(i): self.model.addVar(vtype=GRB.BINARY, name=f"x_pair[{i}]") for i in self.pair_options.index}

        obj = gp.quicksum(float(self.site_options.at[i, "energy"]) * self.x_site[i] for i in self.x_site)
        obj += gp.quicksum(float(self.pair_options.at[i, "energy"]) * self.x_pair[i] for i in self.x_pair)
        self.model.setObjective(obj, GRB.MINIMIZE)

        # Exactly one local record per unit.
        for unit_id, g in self.site_options.groupby("unit_id", sort=False):
            self.model.addConstr(gp.quicksum(self.x_site[int(i)] for i in g.index) == 1, name=f"choose_unit[{unit_id}]")

        # Exactly one interaction record per bundle.
        for bundle_id, g in self.pair_options.groupby("bundle_id", sort=False):
            self.model.addConstr(gp.quicksum(self.x_pair[int(i)] for i in g.index) == 1, name=f"choose_bundle[{bundle_id}]")

        # Build per-unit mapping from (tag_a, tag_b) -> integer signature index.
        self.sig_index = {}
        for unit_id, g in self.site_options.groupby("unit_id", sort=False):
            sigs = sorted({(str(a), str(b)) for a, b in zip(g["tag_a"], g["tag_b"])})
            self.sig_index[unit_id] = {sig: idx for idx, sig in enumerate(sigs)}

        # Integer signature variables and linking to chosen local records.
        self.unit_index = {}
        for unit_id, g in self.site_options.groupby("unit_id", sort=False):
            ub = len(self.sig_index[unit_id]) - 1
            idx_var = self.model.addVar(vtype=GRB.INTEGER, lb=0, ub=ub, name=f"sig[{unit_id}]")
            self.unit_index[unit_id] = idx_var

            expr = gp.quicksum(
                self.sig_index[unit_id][(str(g.at[i, "tag_a"]), str(g.at[i, "tag_b"]))] * self.x_site[int(i)] for i in g.index
            )
            self.model.addConstr(expr == idx_var, name=f"link_sig[{unit_id}]")

        # Consistency between bundle record endpoints and the selected unit signatures.
        pairs_map = {str(r["bundle_id"]): (str(r["left_unit"]), str(r["right_unit"])) for _, r in self.pairs.iterrows()}
        for bundle_id, g in self.pair_options.groupby("bundle_id", sort=False):
            if bundle_id not in pairs_map:
                raise ValueError(f"pair_options references unknown bundle_id: {bundle_id}")
            left_unit, right_unit = pairs_map[bundle_id]
            if left_unit not in self.sig_index or right_unit not in self.sig_index:
                raise ValueError(f"pairs.csv references unknown unit(s) for bundle {bundle_id}: {left_unit}, {right_unit}")

            left_map = self.sig_index[left_unit]
            right_map = self.sig_index[right_unit]

            expr_left = gp.quicksum(
                left_map[(str(g.at[i, "left_tag_a"]), str(g.at[i, "left_tag_b"]))] * self.x_pair[int(i)] for i in g.index
            )
            expr_right = gp.quicksum(
                right_map[(str(g.at[i, "right_tag_a"]), str(g.at[i, "right_tag_b"]))] * self.x_pair[int(i)] for i in g.index
            )
            self.model.addConstr(expr_left == self.unit_index[left_unit], name=f"match_left[{bundle_id}]")
            self.model.addConstr(expr_right == self.unit_index[right_unit], name=f"match_right[{bundle_id}]")

    def solve(self) -> float:
        print("Solving...")
        self.model.optimize()

        if self.model.status != GRB.OPTIMAL:
            raise RuntimeError(f"Optimization ended with status {self.model.status}")

        self.objective_value = float(self.model.ObjVal)
        print(f"Objective Value: {self.objective_value}")
        return self.objective_value


def main():
    if len(sys.argv) < 2:
        print("Usage: python solver.py <instance_folder>")
        raise SystemExit(2)

    instance_folder = sys.argv[1]
    solver = ProteinDesignSolver(instance_folder)
    solver.load_data()
    solver.build_model()
    solver.solve()


if __name__ == "__main__":
    main()

