import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import gurobipy as gp
import pandas as pd
from gurobipy import GRB


@dataclass(frozen=True)
class InstanceParameters:
    N: int
    A: int


def _parse_int(value: object) -> int:
    if isinstance(value, int):
        return value
    return int(str(value))


def load_instance_parameters(instance_json_path: str) -> InstanceParameters:
    with open(instance_json_path, "r", encoding="utf-8") as file:
        instance = json.load(file)
    p = instance["parameters"]
    return InstanceParameters(N=_parse_int(p["N"]), A=_parse_int(p["A"]))


class ContainerLoadingSolver:
    def __init__(self, data_dir: str, instance_json_path: Optional[str] = None):
        self.data_dir = data_dir
        self.instance_json_path = instance_json_path

        self.params: Optional[InstanceParameters] = None

        self.container_dims: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.items: List[int] = []
        self.profit: Dict[int, float] = {}
        self.orientations: Dict[int, List[int]] = {}
        self.oriented_size: Dict[Tuple[int, int], Tuple[float, float, float]] = {}

        self.model: Optional[gp.Model] = None
        self.load_item: Dict[int, gp.Var] = {}
        self.use_orientation: Dict[Tuple[int, int], gp.Var] = {}
        self.pos: Dict[Tuple[int, str], gp.Var] = {}
        self.before: Dict[Tuple[int, int, str], gp.Var] = {}

    def _read_csv(self, filename: str) -> pd.DataFrame:
        return pd.read_csv(os.path.join(self.data_dir, filename))

    def load_data(self) -> None:
        if self.instance_json_path is not None:
            self.params = load_instance_parameters(self.instance_json_path)

        container_df = self._read_csv("container.csv")
        if len(container_df) != 1:
            raise ValueError("container.csv must contain exactly one row.")
        row = container_df.iloc[0]
        self.container_dims = (float(row.length), float(row.width), float(row.height))

        items_df = self._read_csv("items.csv")
        self.items = [int(x) for x in items_df["item_id"].tolist()]
        self.profit = {int(r.item_id): float(r.profit) for _, r in items_df.iterrows()}

        orient_df = self._read_csv("orientations.csv")
        for _, r in orient_df.iterrows():
            item_id = int(r.item_id)
            o = int(r.orientation_id)
            self.orientations.setdefault(item_id, []).append(o)
            self.oriented_size[(item_id, o)] = (float(r.length), float(r.width), float(r.height))

        missing = [i for i in self.items if i not in self.orientations]
        if missing:
            raise ValueError(f"orientations.csv is missing orientations for item_id(s): {missing[:10]}")

        if self.params is not None:
            if self.params.N != len(self.items):
                raise ValueError(f"instance.json N={self.params.N} but items.csv has {len(self.items)} rows.")
            if self.params.A != 3:
                raise ValueError("This format assumes 3 spatial axes (A=3).")

    def build_model(self, time_limit_sec: int = 300, verbose: bool = False) -> None:
        if not self.items:
            raise RuntimeError("Call load_data() first.")

        Lx, Ly, Lz = self.container_dims
        axes = ["x", "y", "z"]
        axis_len = {"x": Lx, "y": Ly, "z": Lz}

        self.model = gp.Model("container_loading_3d")
        self.model.Params.TimeLimit = time_limit_sec
        self.model.Params.OutputFlag = 1 if verbose else 0

        for i in self.items:
            self.load_item[i] = self.model.addVar(vtype=GRB.BINARY, name=f"load[{i}]")
            for o in self.orientations[i]:
                self.use_orientation[(i, o)] = self.model.addVar(vtype=GRB.BINARY, name=f"use_ori[{i},{o}]")

        for i in self.items:
            for a in axes:
                self.pos[(i, a)] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"pos[{i},{a}]")

        for i in self.items:
            for j in self.items:
                if i == j:
                    continue
                for a in axes:
                    self.before[(i, j, a)] = self.model.addVar(vtype=GRB.BINARY, name=f"before[{i},{j},{a}]")

        self.model.update()

        # The original MPS is a minimization model with negative profit coefficients.
        # To match that convention (and `instance.json` optimal_value), we minimize
        # the negative of total loaded profit here.
        self.model.setObjective(
            -gp.quicksum(self.profit[i] * self.load_item[i] for i in self.items), GRB.MINIMIZE
        )

        for i in self.items:
            self.model.addConstr(
                gp.quicksum(self.use_orientation[(i, o)] for o in self.orientations[i]) == self.load_item[i],
                name=f"one_orientation[{i}]",
            )

        size_expr: Dict[Tuple[int, str], gp.LinExpr] = {}
        for i in self.items:
            for a_idx, a in enumerate(axes):
                expr = gp.LinExpr()
                for o in self.orientations[i]:
                    expr += self.oriented_size[(i, o)][a_idx] * self.use_orientation[(i, o)]
                size_expr[(i, a)] = expr

        for i in self.items:
            for a in axes:
                La = axis_len[a]
                self.model.addConstr(
                    self.pos[(i, a)] + size_expr[(i, a)] <= La + La * (1 - self.load_item[i]),
                    name=f"inside[{i},{a}]",
                )
                self.model.addConstr(
                    self.pos[(i, a)] <= La * self.load_item[i],
                    name=f"pos_zero_if_not_loaded[{i},{a}]",
                )

        for i in self.items:
            for j in self.items:
                if i == j:
                    continue
                for a in axes:
                    La = axis_len[a]
                    self.model.addConstr(
                        self.pos[(i, a)]
                        + size_expr[(i, a)]
                        <= self.pos[(j, a)]
                        + La * (1 - self.before[(i, j, a)])
                        + La * (2 - self.load_item[i] - self.load_item[j]),
                        name=f"no_overlap[{i},{j},{a}]",
                    )
                    self.model.addConstr(
                        self.before[(i, j, a)] <= self.load_item[i], name=f"before_link_i[{i},{j},{a}]"
                    )
                    self.model.addConstr(
                        self.before[(i, j, a)] <= self.load_item[j], name=f"before_link_j[{i},{j},{a}]"
                    )

        for idx_i, i in enumerate(self.items):
            for j in self.items[idx_i + 1 :]:
                self.model.addConstr(
                    gp.quicksum(self.before[(i, j, a)] + self.before[(j, i, a)] for a in axes)
                    >= self.load_item[i] + self.load_item[j] - 1,
                    name=f"pair_separation[{i},{j}]",
                )

        self.model.update()

    def solve(self) -> None:
        if self.model is None:
            raise RuntimeError("Call build_model() first.")
        self.model.optimize()

    def objective_value(self) -> Optional[float]:
        if self.model is None or self.model.Status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
            return None
        return float(self.model.ObjVal)

    def loaded_profit(self) -> Optional[float]:
        obj = self.objective_value()
        if obj is None:
            return None
        return -obj


def main(argv: Sequence[str]) -> int:
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")
    instance_json = os.path.join(base_dir, "instance.json")
    mps_path = os.path.join(base_dir, "pigeon-08.mps")

    solver = ContainerLoadingSolver(data_dir=data_dir, instance_json_path=instance_json)
    solver.load_data()
    solver.build_model(verbose=True)
    solver.solve()

    print(f"Status: {solver.model.Status if solver.model else 'N/A'}")
    print(f"Objective (MPS min form): {solver.objective_value()}")
    print(f"Loaded profit: {solver.loaded_profit()}")

    if os.path.exists(mps_path):
        m = gp.read(mps_path)
        m.Params.OutputFlag = 0
        m.optimize()
        print(f"MPS status: {m.Status}")
        if m.SolCount and solver.objective_value() is not None:
            print(f"MPS objective: {float(m.ObjVal)}")
            print(f"Solver objective - MPS objective: {solver.objective_value() - float(m.ObjVal)} (should be 0.0)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main([]))
