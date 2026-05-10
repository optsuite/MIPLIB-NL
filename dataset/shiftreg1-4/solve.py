import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import gurobipy as gp
import pandas as pd
from gurobipy import GRB


@dataclass(frozen=True)
class InstanceParameters:
    N_employees: int
    N_time_slots: int
    time_granularity_minutes: int
    work_window_start_time_id: int
    work_window_end_time_id: int
    break_window_start_time_id: int
    break_window_end_time_id: int
    min_work_slots: int
    max_work_slots: int
    short_shift_max_work_slots: int
    long_shift_min_work_slots: int
    short_break_slots_short_shift: int
    short_break_slots_long_shift: int
    meal_break_slots_long_shift: int


def _parse_int(value: object) -> int:
    if isinstance(value, int):
        return value
    return int(str(value))


def load_instance_parameters(instance_json_path: str) -> InstanceParameters:
    with open(instance_json_path, "r", encoding="utf-8") as f:
        instance = json.load(f)
    p = instance["parameters"]
    return InstanceParameters(
        N_employees=_parse_int(p["N_employees"]),
        N_time_slots=_parse_int(p["N_time_slots"]),
        time_granularity_minutes=_parse_int(p["time_granularity_minutes"]),
        work_window_start_time_id=_parse_int(p["work_window_start_time_id"]),
        work_window_end_time_id=_parse_int(p["work_window_end_time_id"]),
        break_window_start_time_id=_parse_int(p["break_window_start_time_id"]),
        break_window_end_time_id=_parse_int(p["break_window_end_time_id"]),
        min_work_slots=_parse_int(p["min_work_slots"]),
        max_work_slots=_parse_int(p["max_work_slots"]),
        short_shift_max_work_slots=_parse_int(p["short_shift_max_work_slots"]),
        long_shift_min_work_slots=_parse_int(p["long_shift_min_work_slots"]),
        short_break_slots_short_shift=_parse_int(p["short_break_slots_short_shift"]),
        short_break_slots_long_shift=_parse_int(p["short_break_slots_long_shift"]),
        meal_break_slots_long_shift=_parse_int(p["meal_break_slots_long_shift"]),
    )


class ShiftSchedulingSolver:
    """
    Reference Gurobi implementation for the simplified data format in this folder.

    Simplifications:
    - Employees are implicit: employee_id = 0..N_employees-1 (from instance.json).
    - Time slots are implicit: time_id = 0..N_time_slots-1 with fixed granularity.
    - Rulebook nodes are derived from rulebook_edges.csv (no rulebook_nodes.csv).
    """

    def __init__(self, data_dir: str, instance_json_path: str):
        self.data_dir = data_dir
        self.instance_json_path = instance_json_path

        self.params: InstanceParameters = load_instance_parameters(instance_json_path)

        self.employees: List[int] = list(range(self.params.N_employees))
        self.time_slots: List[int] = list(range(self.params.N_time_slots))

        self.demand: Dict[int, int] = {}
        self.under_penalty: Dict[int, float] = {}
        self.over_penalty: Dict[int, float] = {}
        self.work_cost: Dict[Tuple[int, int], float] = {}

        # Pre-expanded (time-layered) rulebook graph
        self.rulebook_edges: List[Tuple[int, str, str, str]] = []
        self.edges_by_time_label: Dict[Tuple[int, str], List[int]] = {}
        self.edges_outgoing: Dict[Tuple[int, str], List[int]] = {}
        self.edges_incoming: Dict[Tuple[int, str], List[int]] = {}
        self.rulebook_nodes: List[Tuple[int, str]] = []
        self.rulebook_last_time: int = 0

        self.start_state: str = "q0"
        self.accept_state: str = "rs"

        self.model: Optional[gp.Model] = None
        self.w: Dict[int, gp.Var] = {}
        self.u: Dict[int, gp.Var] = {}
        self.work: Dict[Tuple[int, int], gp.Var] = {}
        self.short_break: Dict[Tuple[int, int], gp.Var] = {}
        self.meal_break: Dict[Tuple[int, int], gp.Var] = {}
        self.off: Dict[Tuple[int, int], gp.Var] = {}
        self.shortage: Dict[int, gp.Var] = {}
        self.surplus: Dict[int, gp.Var] = {}
        self.flow: Dict[Tuple[int, int, int], gp.Var] = {}

    def _read_csv(self, filename: str) -> pd.DataFrame:
        return pd.read_csv(os.path.join(self.data_dir, filename))

    def load_data(self) -> None:
        demand_df = self._read_csv("demand.csv")
        self.demand = {int(r.time_id): int(r.required_staff) for _, r in demand_df.iterrows()}
        self.under_penalty = {int(r.time_id): float(r.under_penalty) for _, r in demand_df.iterrows()}
        self.over_penalty = {int(r.time_id): float(r.over_penalty) for _, r in demand_df.iterrows()}

        cost_df = self._read_csv("work_cost.csv")
        self.work_cost = {
            (int(r.employee_id), int(r.time_id)): float(r.cost) for _, r in cost_df.iterrows()
        }

        edges_df = self._read_csv("rulebook_edges.csv")
        self.rulebook_edges = [
            (int(r.time_id), str(r.from_state), str(r.to_state), str(r.label)) for _, r in edges_df.iterrows()
        ]

        self.edges_by_time_label.clear()
        self.edges_outgoing.clear()
        self.edges_incoming.clear()
        nodes = set()
        for edge_id, (t, fs, ts, label) in enumerate(self.rulebook_edges):
            self.edges_by_time_label.setdefault((t, label), []).append(edge_id)
            self.edges_outgoing.setdefault((t, fs), []).append(edge_id)
            self.edges_incoming.setdefault((t + 1, ts), []).append(edge_id)
            nodes.add((t, fs))
            nodes.add((t + 1, ts))
        self.rulebook_nodes = sorted(nodes)
        self.rulebook_last_time = max(t for (t, _, _, _) in self.rulebook_edges)

    def build_model(self, verbose: bool = False, time_limit_s: Optional[float] = 300.0) -> None:
        self.model = gp.Model("shiftreg1-4_clean")
        self.model.Params.OutputFlag = 1 if verbose else 0
        if time_limit_s is not None:
            self.model.Params.TimeLimit = float(time_limit_s)

        for e in self.employees:
            self.w[e] = self.model.addVar(vtype=GRB.BINARY, name=f"works[{e}]")
            self.u[e] = self.model.addVar(vtype=GRB.BINARY, name=f"long_shift[{e}]")

        for e in self.employees:
            for t in self.time_slots:
                self.work[(e, t)] = self.model.addVar(vtype=GRB.BINARY, name=f"work[{e},{t}]")
                self.short_break[(e, t)] = self.model.addVar(vtype=GRB.BINARY, name=f"short_break[{e},{t}]")
                self.meal_break[(e, t)] = self.model.addVar(vtype=GRB.BINARY, name=f"meal_break[{e},{t}]")
                self.off[(e, t)] = self.model.addVar(vtype=GRB.BINARY, name=f"off[{e},{t}]")

        for t in self.demand:
            self.shortage[t] = self.model.addVar(lb=0.0, name=f"under[{t}]")
            self.surplus[t] = self.model.addVar(lb=0.0, name=f"over[{t}]")

        for e in self.employees:
            for edge_id, (t, _, _, _) in enumerate(self.rulebook_edges):
                self.flow[(e, t, edge_id)] = self.model.addVar(lb=0.0, name=f"flow[{e},{t},{edge_id}]")

        self.model.update()

        # One status per employee and time slot (conditional on being scheduled)
        for e in self.employees:
            for t in self.time_slots:
                self.model.addConstr(
                    self.off[(e, t)] + self.work[(e, t)] + self.short_break[(e, t)] + self.meal_break[(e, t)]
                    == self.w[e],
                    name=f"one_status[{e},{t}]",
                )

        # Soft demand balance
        for t, req in self.demand.items():
            self.model.addConstr(
                gp.quicksum(self.work[(e, t)] for e in self.employees) + self.shortage[t] - self.surplus[t] == req,
                name=f"demand[{t}]",
            )

        # Shift totals and classification
        for e in self.employees:
            total_work = gp.quicksum(self.work[(e, t)] for t in self.time_slots)
            self.model.addConstr(total_work <= self.params.max_work_slots * self.w[e], name=f"max_work[{e}]")
            self.model.addConstr(total_work >= self.params.min_work_slots * self.w[e], name=f"min_work[{e}]")

            self.model.addConstr(
                total_work
                <= self.params.short_shift_max_work_slots
                + (self.params.max_work_slots - self.params.short_shift_max_work_slots) * self.u[e],
                name=f"short_max_or_long[{e}]",
            )
            self.model.addConstr(total_work >= self.params.long_shift_min_work_slots * self.u[e], name=f"long_min[{e}]")
            self.model.addConstr(self.u[e] <= self.w[e], name=f"long_implies_work[{e}]")

            self.model.addConstr(
                gp.quicksum(self.short_break[(e, t)] for t in self.time_slots) == self.w[e] + self.u[e],
                name=f"short_break_count[{e}]",
            )
            self.model.addConstr(
                gp.quicksum(self.meal_break[(e, t)] for t in self.time_slots)
                == self.params.meal_break_slots_long_shift * self.u[e],
                name=f"meal_break_count[{e}]",
            )

        # Link rulebook edge flows to status indicators (per time and label) for the rulebook horizon.
        labels = ["off", "work", "short_break", "meal_break"]
        var_by_label = {
            "off": self.off,
            "work": self.work,
            "short_break": self.short_break,
            "meal_break": self.meal_break,
        }
        for e in self.employees:
            for t in [tt for tt in self.time_slots if tt <= self.rulebook_last_time]:
                for label in labels:
                    edge_ids = self.edges_by_time_label.get((t, label), [])
                    if not edge_ids:
                        self.model.addConstr(var_by_label[label][(e, t)] == 0, name=f"label_unavailable[{label},{e},{t}]")
                        continue
                    flows = [self.flow[(e, t, edge_id)] for edge_id in edge_ids]
                    self.model.addConstr(
                        gp.quicksum(flows) == var_by_label[label][(e, t)],
                        name=f"link[{label},{e},{t}]",
                    )

        # For time slots beyond the rulebook horizon, force employees to be off duty (if scheduled).
        for e in self.employees:
            for t in [tt for tt in self.time_slots if tt > self.rulebook_last_time]:
                self.model.addConstr(self.short_break[(e, t)] == 0, name=f"post_rulebook_short_break[{e},{t}]")
                self.model.addConstr(self.meal_break[(e, t)] == 0, name=f"post_rulebook_meal_break[{e},{t}]")
                self.model.addConstr(self.work[(e, t)] == 0, name=f"post_rulebook_work[{e},{t}]")
                self.model.addConstr(self.off[(e, t)] == self.w[e], name=f"post_rulebook_off[{e},{t}]")

        # Flow conservation on the time-layered nodes
        for e in self.employees:
            for (t, s) in self.rulebook_nodes:
                if t > self.rulebook_last_time:
                    continue
                outgoing_edge_ids = self.edges_outgoing.get((t, s), [])
                outgoing = [self.flow[(e, t, edge_id)] for edge_id in outgoing_edge_ids]

                if t == 0:
                    inflow = self.w[e] if s == self.start_state else 0
                else:
                    incoming_edge_ids = self.edges_incoming.get((t, s), [])
                    incoming = []
                    for edge_id in incoming_edge_ids:
                        t0, _, _, _ = self.rulebook_edges[edge_id]
                        incoming.append(self.flow[(e, t0, edge_id)])
                    inflow = gp.quicksum(incoming)

                if outgoing or (t == 0 and s == self.start_state):
                    self.model.addConstr(gp.quicksum(outgoing) == inflow, name=f"flow[{e},{t},{s}]")

        # Terminal requirement at the last rulebook time
        term_edge_ids = self.edges_outgoing.get((self.rulebook_last_time, self.accept_state), [])
        if not term_edge_ids:
            raise ValueError("rulebook_edges.csv has no outgoing edge from the accept state at the terminal time.")
        for e in self.employees:
            flows = [self.flow[(e, self.rulebook_last_time, edge_id)] for edge_id in term_edge_ids]
            self.model.addConstr(gp.quicksum(flows) == self.w[e], name=f"terminal[{e}]")

        # Objective
        obj = gp.LinExpr()
        for (e, t), var in self.work.items():
            cost = self.work_cost.get((e, t), 0.0)
            if cost:
                obj += cost * var
        for t in self.demand:
            obj += self.under_penalty[t] * self.shortage[t]
            obj += self.over_penalty[t] * self.surplus[t]
        self.model.setObjective(obj, GRB.MINIMIZE)
        self.model.update()

    def solve(self) -> None:
        if self.model is None:
            raise RuntimeError("Call build_model() first.")
        self.model.optimize()


def main(argv: Sequence[str]) -> int:
    base_dir = os.path.dirname(__file__)
    data_dir = os.path.join(base_dir, "data")
    instance_json = os.path.join(base_dir, "instance.json")
    mps_path = os.path.join(base_dir, "shiftreg1-4.mps")

    solver = ShiftSchedulingSolver(data_dir=data_dir, instance_json_path=instance_json)
    solver.load_data()
    solver.build_model(verbose=False, time_limit_s=300.0)
    solver.solve()

    print(f"Status: {solver.model.Status if solver.model else 'N/A'}")
    if solver.model is not None and solver.model.SolCount:
        obj = float(solver.model.ObjVal)
        print(f"Objective: {obj}")

        with open(instance_json, "r", encoding="utf-8") as f:
            expected = float(json.load(f)["optimal_value"])
        print(f"Expected optimal_value: {expected}")
        print(f"Objective - expected: {obj - expected} (should be ~0.0)")

    if os.path.exists(mps_path):
        m = gp.read(mps_path)
        m.Params.OutputFlag = 0
        m.optimize()
        print(f"MPS status: {m.Status}")
        if m.SolCount and solver.model is not None and solver.model.SolCount:
            print(f"MPS objective: {float(m.ObjVal)}")
            print(f"Solver objective - MPS objective: {float(solver.model.ObjVal) - float(m.ObjVal)} (should be ~0.0)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main([]))
