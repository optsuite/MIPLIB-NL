import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import gurobipy as gp
import pandas as pd
from gurobipy import GRB


@dataclass(frozen=True)
class InstanceParameters:
    N_nodes: int
    N_arcs: int
    N_commodities: int
    required_outgoing: int
    required_incoming: int


def _parse_int(value: object) -> int:
    if isinstance(value, int):
        return value
    return int(str(value))


def load_instance_parameters(instance_json_path: str) -> InstanceParameters:
    with open(instance_json_path, "r", encoding="utf-8") as f:
        instance = json.load(f)
    p = instance["parameters"]
    return InstanceParameters(
        N_nodes=_parse_int(p["N_nodes"]),
        N_arcs=_parse_int(p["N_arcs"]),
        N_commodities=_parse_int(p["N_commodities"]),
        required_outgoing=_parse_int(p["required_outgoing"]),
        required_incoming=_parse_int(p["required_incoming"]),
    )


class CongestionNetworkSolver:
    """
    Reference Gurobi implementation for the data format in this folder.

    This solver rebuilds a lane-commitment-and-routing model from the CSV files,
    using clean identifiers (arc_id, node_id, commodity_id) instead of the MPS naming.
    """

    def __init__(self, data_dir: str, instance_json_path: Optional[str] = None):
        self.data_dir = data_dir
        self.instance_json_path = instance_json_path

        self.params: Optional[InstanceParameters] = None

        self.nodes: List[str] = []
        self.commodities: List[str] = []
        self.source_node: Dict[str, str] = {}

        self.arcs: List[str] = []
        self.arc_from: Dict[str, str] = {}
        self.arc_to: Dict[str, str] = {}
        self.x_type: Dict[str, str] = {}
        self.x_lb: Dict[str, float] = {}
        self.x_ub: Dict[str, float] = {}

        self.required_out: Dict[str, float] = {}
        self.required_in: Dict[str, float] = {}

        self.net_inflow: Dict[Tuple[str, str], float] = {}
        self.capacity_multiplier: Dict[Tuple[str, str], float] = {}

        self.model: Optional[gp.Model] = None
        self.z: Optional[gp.Var] = None
        self.x: Dict[str, gp.Var] = {}
        self.flow: Dict[Tuple[str, str], gp.Var] = {}
        self.total_flow: Dict[str, gp.Var] = {}

    def _read_csv(self, filename: str) -> pd.DataFrame:
        return pd.read_csv(os.path.join(self.data_dir, filename))

    def load_data(self) -> None:
        if self.instance_json_path is not None:
            self.params = load_instance_parameters(self.instance_json_path)

        nodes_df = self._read_csv("nodes.csv")
        self.nodes = [str(x) for x in nodes_df["node_id"].tolist()]

        comm_df = self._read_csv("commodities.csv")
        self.commodities = [str(x) for x in comm_df["commodity_id"].tolist()]
        self.source_node = {str(r.commodity_id): str(r.source_node) for _, r in comm_df.iterrows()}

        arcs_df = self._read_csv("arcs.csv")
        self.arcs = [str(x) for x in arcs_df["arc_id"].tolist()]
        self.arc_from = {str(r.arc_id): str(r.from_node) for _, r in arcs_df.iterrows()}
        self.arc_to = {str(r.arc_id): str(r.to_node) for _, r in arcs_df.iterrows()}
        self.x_type = {str(r.arc_id): str(r.x_decision_type) for _, r in arcs_df.iterrows()}
        self.x_lb = {str(r.arc_id): float(r.x_lb) for _, r in arcs_df.iterrows()}
        self.x_ub = {str(r.arc_id): float(r.x_ub) for _, r in arcs_df.iterrows()}

        deg_df = self._read_csv("degree_requirements.csv")
        self.required_out = {str(r.node_id): float(r.required_outgoing) for _, r in deg_df.iterrows()}
        self.required_in = {str(r.node_id): float(r.required_incoming) for _, r in deg_df.iterrows()}

        dem_df = self._read_csv("demands.csv")
        self.net_inflow = {(str(r.commodity_id), str(r.node_id)): float(r.net_inflow) for _, r in dem_df.iterrows()}

        cap_df = self._read_csv("capacity_multipliers.csv")
        self.capacity_multiplier = {
            (str(r.commodity_id), str(r.arc_id)): float(r.capacity_multiplier) for _, r in cap_df.iterrows()
        }

        if self.params is not None:
            if self.params.N_nodes != len(self.nodes):
                raise ValueError(f"instance.json N_nodes={self.params.N_nodes} but nodes.csv has {len(self.nodes)} rows.")
            if self.params.N_arcs != len(self.arcs):
                raise ValueError(f"instance.json N_arcs={self.params.N_arcs} but arcs.csv has {len(self.arcs)} rows.")
            if self.params.N_commodities != len(self.commodities):
                raise ValueError(
                    f"instance.json N_commodities={self.params.N_commodities} but commodities.csv has {len(self.commodities)} rows."
                )

    def build_model(self, time_limit_sec: int = 300, verbose: bool = False) -> None:
        if not self.nodes or not self.arcs or not self.commodities:
            raise RuntimeError("Call load_data() first.")

        self.model = gp.Model("congestion_network")
        self.model.Params.TimeLimit = time_limit_sec
        self.model.Params.OutputFlag = 1 if verbose else 0

        self.z = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name="z")

        for a in self.arcs:
            vtype = GRB.INTEGER if self.x_type[a].strip().lower() == "integer" else GRB.CONTINUOUS
            self.x[a] = self.model.addVar(vtype=vtype, lb=self.x_lb[a], ub=self.x_ub[a], name=f"x[{a}]")

        for a in self.arcs:
            self.total_flow[a] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"F[{a}]")

        for (k, a), cap in self.capacity_multiplier.items():
            if cap < 0:
                raise ValueError(f"capacity_multiplier must be nonnegative, got {cap} for ({k},{a}).")
            self.flow[(k, a)] = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f[{k},{a}]")

        self.model.update()

        assert self.z is not None
        self.model.setObjective(self.z, GRB.MINIMIZE)

        for n in self.nodes:
            out_arcs = [a for a in self.arcs if self.arc_from[a] == n]
            in_arcs = [a for a in self.arcs if self.arc_to[a] == n]
            self.model.addConstr(gp.quicksum(self.x[a] for a in out_arcs) == self.required_out[n], name=f"out[{n}]")
            self.model.addConstr(gp.quicksum(self.x[a] for a in in_arcs) == self.required_in[n], name=f"in[{n}]")

        for a in self.arcs:
            eligible = [k for k in self.commodities if (k, a) in self.flow]
            self.model.addConstr(
                self.total_flow[a] == gp.quicksum(self.flow[(k, a)] for k in eligible),
                name=f"total[{a}]",
            )
            self.model.addConstr(self.total_flow[a] <= self.z, name=f"z_ge_lane[{a}]")

        for (k, a), cap in self.capacity_multiplier.items():
            self.model.addConstr(self.flow[(k, a)] <= cap * self.x[a], name=f"cap[{k},{a}]")

        for (k, n), rhs in self.net_inflow.items():
            src = self.source_node.get(k)
            if src is None:
                raise ValueError(f"commodities.csv missing source_node for commodity_id={k}.")
            if n == src:
                raise ValueError(f"demands.csv should omit the origin site: got demand row for commodity {k} at node {n}.")

            in_arcs = [a for a in self.arcs if self.arc_to[a] == n and (k, a) in self.flow]
            out_arcs = [a for a in self.arcs if self.arc_from[a] == n and (k, a) in self.flow]
            self.model.addConstr(
                gp.quicksum(self.flow[(k, a)] for a in in_arcs) - gp.quicksum(self.flow[(k, a)] for a in out_arcs)
                == rhs,
                name=f"bal[{k},{n}]",
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


def main(argv: Sequence[str]) -> int:
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")
    instance_json = os.path.join(base_dir, "instance.json")
    mps_path = os.path.join(base_dir, "bienst2.mps")

    solver = CongestionNetworkSolver(data_dir=data_dir, instance_json_path=instance_json)
    solver.load_data()
    solver.build_model(verbose=False)
    solver.solve()

    print(f"Status: {solver.model.Status if solver.model else 'N/A'}")
    obj = solver.objective_value()
    print(f"Objective: {obj}")

    if os.path.exists(instance_json) and obj is not None:
        with open(instance_json, "r", encoding="utf-8") as f:
            expected = float(json.load(f)["optimal_value"])
        print(f"Expected optimal_value: {expected}")
        print(f"Objective - expected: {obj - expected} (should be ~0.0)")

    if os.path.exists(mps_path):
        m = gp.read(mps_path)
        m.Params.OutputFlag = 0
        m.optimize()
        print(f"MPS status: {m.Status}")
        if m.SolCount:
            print(f"MPS objective: {float(m.ObjVal)}")
            if obj is not None:
                diff = obj - float(m.ObjVal)
                print(f"Solver objective - MPS objective: {diff} (should be ~0.0)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main([]))
