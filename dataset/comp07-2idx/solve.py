import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import gurobipy as gp
import pandas as pd
from gurobipy import GRB


@dataclass(frozen=True)
class InstanceParameters:
    C: int
    D: int
    P: int
    T: int
    Q: int
    CP: int
    max_rooms_per_slot: int
    w_days_below: int
    w_isolated: int
    penalty_min: int
    penalty_max: int
    isolation_period_rule: str
    slot_label_format: str


def _parse_int(value: object) -> int:
    if isinstance(value, int):
        return value
    return int(str(value))


def load_instance_parameters(instance_json_path: str) -> Dict[str, str]:
    with open(instance_json_path, "r", encoding="utf-8") as file:
        instance = json.load(file)
    return instance["parameters"]


def _slot_label(day: int, period: int) -> str:
    return f"D{day}P{period}"


class CourseTimetablingSolver:
    """
    Reference Gurobi model for the instance data format in this folder.

    The goal is not to reproduce the original MPS naming, but to provide a clean
    example of how to rebuild the same optimization model from the CSV files.
    """

    def __init__(self, data_dir: str, instance_json_path: Optional[str] = None):
        self.data_dir = data_dir
        self.instance_json_path = instance_json_path

        self.params: Optional[InstanceParameters] = None
        self.courses: List[int] = []
        self.days: List[int] = []
        self.periods: List[int] = []
        self.slots: List[Tuple[int, int]] = []

        self.lectures: Dict[int, int] = {}
        self.min_days: Dict[int, int] = {}
        self.conflicts: Set[Tuple[int, int]] = set()
        self.curricula: Dict[int, List[int]] = {}
        self.availability: Dict[Tuple[int, int, int], int] = {}
        self.rooms_geq: Dict[int, int] = {}
        self.penalty_weight: Dict[Tuple[int, int], int] = {}

        self.model: Optional[gp.Model] = None
        self.y: Dict[Tuple[int, int, int], gp.Var] = {}
        self.day_used: Dict[Tuple[int, int], gp.Var] = {}
        self.days_below: Dict[int, gp.Var] = {}
        self.iso: Dict[Tuple[int, int, int], gp.Var] = {}
        self.shortfall: Dict[Tuple[int, int, int, int], gp.Var] = {}

    def _read_csv(self, filename: str) -> pd.DataFrame:
        return pd.read_csv(os.path.join(self.data_dir, filename))

    def load_data(self) -> None:
        json_params = {}
        if self.instance_json_path is not None:
            json_params = load_instance_parameters(self.instance_json_path)

        courses_df = self._read_csv("courses.csv")
        self.courses = [int(x) for x in courses_df["course_id"].tolist()]
        self.lectures = {int(r.course_id): int(r.lectures) for _, r in courses_df.iterrows()}
        self.min_days = {int(r.course_id): int(r.min_days) for _, r in courses_df.iterrows()}

        conflicts_df = self._read_csv("conflicts.csv")
        for _, row in conflicts_df.iterrows():
            a, b = int(row.course1), int(row.course2)
            if a == b:
                continue
            self.conflicts.add((a, b) if a < b else (b, a))

        curricula_df = self._read_csv("curricula.csv")
        for _, row in curricula_df.iterrows():
            q = int(row.curriculum_id)
            course_ids = [int(x) for x in str(row.course_ids).split(",") if str(x).strip() != ""]
            self.curricula[q] = course_ids

        # Hardcoded scheduling horizon as per problem description
        num_days = 5
        num_periods = 5
        self.days = list(range(num_days))
        self.periods = list(range(num_periods))
        self.slots = [(d, p) for d in self.days for p in self.periods]

        # Initialize availability to 1 (all available)
        for c in self.courses:
            for d, p in self.slots:
                self.availability[(c, d, p)] = 1

        # Apply blackouts
        if os.path.exists(os.path.join(self.data_dir, "blackout_periods.csv")):
            blackout_df = self._read_csv("blackout_periods.csv")
            for _, row in blackout_df.iterrows():
                c = int(row.course_id)
                slot = str(row.slot_label)
                # Parse 'D<day>P<period>'
                if slot.startswith('D') and 'P' in slot:
                    d = int(slot[1:slot.index('P')])
                    p = int(slot[slot.index('P')+1:])
                    self.availability[(c, d, p)] = 0
        elif os.path.exists(os.path.join(self.data_dir, "available_slots.csv")):
            availability_df = self._read_csv("available_slots.csv")
            slot_columns = [c for c in availability_df.columns if c.startswith("D") and "P" in c]
            for _, row in availability_df.iterrows():
                c = int(row.course_id)
                for col in slot_columns:
                    day = int(col[1 : col.index("P")])
                    period = int(col[col.index("P") + 1 :])
                    self.availability[(c, day, period)] = int(row[col])

        # Process Classroom Inventory to reconstruct rooms_geq
        if os.path.exists(os.path.join(self.data_dir, "classroom_inventory.csv")):
            inventory_df = self._read_csv("classroom_inventory.csv")
            penalties_df = self._read_csv("capacity_penalties.csv")
            penalty_caps = set(penalties_df["capacity"].unique())
            inventory_caps = set(inventory_df["capacity"].unique())
            all_caps = sorted(list(penalty_caps | inventory_caps))
            
            for cap in all_caps:
                # Count rooms with capacity >= cap
                count = len(inventory_df[inventory_df["capacity"] >= cap])
                if count > 0:
                    self.rooms_geq[cap] = count
                    
            self.penalty_weight = {
                (int(r.course_id), int(r.capacity)): int(r.penalty_weight) for _, r in penalties_df.iterrows()
            }
            
        elif os.path.exists(os.path.join(self.data_dir, "rooms.csv")):
            rooms_df = self._read_csv("rooms.csv")
            self.rooms_geq = {int(r.capacity): int(r.available_rooms) for _, r in rooms_df.iterrows()}
            penalties_df = self._read_csv("capacity_penalties.csv")
            self.penalty_weight = {
                (int(r.course_id), int(r.capacity)): int(r.penalty_weight) for _, r in penalties_df.iterrows()
            }

        if self.params is None:
            # Infer parameters
            p = json_params
            self.params = InstanceParameters(
                C=len(self.courses),
                D=num_days,
                P=num_periods,
                T=num_days * num_periods,
                Q=len(self.curricula),
                CP=len(self.conflicts),
                max_rooms_per_slot=_parse_int(p.get("max_rooms_per_slot", 20)),
                w_days_below=_parse_int(p.get("w_days_below", 5)),
                w_isolated=_parse_int(p.get("w_isolated", 2)),
                penalty_min=_parse_int(p.get("penalty_min", 0)),
                penalty_max=_parse_int(p.get("penalty_max", 0)),
                isolation_period_rule="isolation is evaluated for every period of a day; boundary periods consider the single adjacent period",
                slot_label_format="D<day>P<period>",
            )

    def build_model(self, time_limit_sec: int = 300, verbose: bool = False) -> None:
        if self.params is None:
            raise RuntimeError("Call load_data() first.")

        self.model = gp.Model("course_timetabling")
        self.model.Params.TimeLimit = time_limit_sec
        self.model.Params.OutputFlag = 1 if verbose else 0

        for c in self.courses:
            for d, p in self.slots:
                if self.availability.get((c, d, p), 0) == 1:
                    self.y[(c, d, p)] = self.model.addVar(vtype=GRB.BINARY, name=f"teach[{c},{d},{p}]")

        for c in self.courses:
            for d in self.days:
                self.day_used[(c, d)] = self.model.addVar(vtype=GRB.BINARY, name=f"day_used[{c},{d}]")
            self.days_below[c] = self.model.addVar(vtype=GRB.INTEGER, lb=0, name=f"days_below[{c}]")

        for q in self.curricula.keys():
            for d in self.days:
                for p in self.periods:
                    self.iso[(q, d, p)] = self.model.addVar(vtype=GRB.BINARY, name=f"iso[{q},{d},{p}]")

        for (c, cap), _w in self.penalty_weight.items():
            for d, p in self.slots:
                if (c, d, p) in self.y:
                    self.shortfall[(c, cap, d, p)] = self.model.addVar(
                        vtype=GRB.BINARY, name=f"shortfall[{c},{cap},{d},{p}]"
                    )

        self.model.update()

        obj = gp.LinExpr()
        for (c, cap, d, p), var in self.shortfall.items():
            obj += self.penalty_weight[(c, cap)] * var
        for c, var in self.days_below.items():
            obj += self.params.w_days_below * var
        for (_q, _d, _p), var in self.iso.items():
            obj += self.params.w_isolated * var
        self.model.setObjective(obj, GRB.MINIMIZE)

        self._add_constraints()
        self.model.update()

    def _add_constraints(self) -> None:
        assert self.model is not None

        for c in self.courses:
            self.model.addConstr(
                gp.quicksum(self.y.get((c, d, p), 0) for d, p in self.slots) == self.lectures[c],
                name=f"lecture_count[{c}]",
            )

        for d, p in self.slots:
            self.model.addConstr(
                gp.quicksum(self.y.get((c, d, p), 0) for c in self.courses) <= self.params.max_rooms_per_slot,
                name=f"slot_capacity_total[{d},{p}]",
            )

        for c1, c2 in sorted(self.conflicts):
            for d, p in self.slots:
                v1 = self.y.get((c1, d, p))
                v2 = self.y.get((c2, d, p))
                if v1 is None and v2 is None:
                    continue
                expr = gp.LinExpr()
                if v1 is not None:
                    expr += v1
                if v2 is not None:
                    expr += v2
                self.model.addConstr(expr <= 1, name=f"conflict[{c1},{c2},{d},{p}]")

        for c in self.courses:
            for d in self.days:
                self.model.addConstr(
                    self.day_used[(c, d)]
                    <= gp.quicksum(self.y.get((c, d, p), 0) for p in self.periods),
                    name=f"day_used_link[{c},{d}]",
                )

        for c in self.courses:
            self.model.addConstr(
                gp.quicksum(self.day_used[(c, d)] for d in self.days) + self.days_below[c] >= self.min_days[c],
                name=f"min_days_soft[{c}]",
            )

        for q, q_courses in self.curricula.items():
            q_courses_set = set(q_courses)
            for d in self.days:
                for p in self.periods:
                    expr_mid = gp.quicksum(self.y.get((c, d, p), 0) for c in q_courses_set)
                    if p == 0:
                        expr_next = gp.quicksum(self.y.get((c, d, p + 1), 0) for c in q_courses_set)
                        self.model.addConstr(
                            -expr_mid + expr_next + self.iso[(q, d, p)] >= 0,
                            name=f"curriculum_isolation[{q},{d},{p}]",
                        )
                    elif p == self.periods[-1]:
                        expr_prev = gp.quicksum(self.y.get((c, d, p - 1), 0) for c in q_courses_set)
                        self.model.addConstr(
                            expr_prev - expr_mid + self.iso[(q, d, p)] >= 0,
                            name=f"curriculum_isolation[{q},{d},{p}]",
                        )
                    else:
                        expr_prev = gp.quicksum(self.y.get((c, d, p - 1), 0) for c in q_courses_set)
                        expr_next = gp.quicksum(self.y.get((c, d, p + 1), 0) for c in q_courses_set)
                        self.model.addConstr(
                            expr_prev - expr_mid + expr_next + self.iso[(q, d, p)] >= 0,
                            name=f"curriculum_isolation[{q},{d},{p}]",
                        )

        courses_by_cap: Dict[int, List[int]] = {}
        for (c, cap) in self.penalty_weight.keys():
            courses_by_cap.setdefault(cap, []).append(c)

        for cap, cap_courses in courses_by_cap.items():
            if cap not in self.rooms_geq:
                raise ValueError(f"classroom_inventory.csv is missing capacity threshold {cap}.")
            limit = self.rooms_geq[cap]
            for d, p in self.slots:
                expr = gp.LinExpr()
                for c in cap_courses:
                    y_var = self.y.get((c, d, p))
                    if y_var is None:
                        continue
                    expr += y_var
                    s_var = self.shortfall.get((c, cap, d, p))
                    if s_var is not None:
                        expr -= s_var
                self.model.addConstr(expr <= limit, name=f"capacity_layer[{cap},{d},{p}]")

        for (c, cap, d, p), s_var in self.shortfall.items():
            y_var = self.y[(c, d, p)]
            self.model.addConstr(y_var - s_var >= 0, name=f"shortfall_activation[{c},{cap},{d},{p}]")

    def solve(self) -> None:
        if self.model is None:
            raise RuntimeError("Call build_model() first.")
        self.model.optimize()

    def objective_value(self) -> Optional[float]:
        if self.model is None or self.model.Status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
            return None
        return float(self.model.ObjVal)


def main(argv: Sequence[str]) -> int:
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    instance_json = os.path.join(os.path.dirname(__file__), "instance.json")
    solver = CourseTimetablingSolver(data_dir=data_dir, instance_json_path=instance_json)
    solver.load_data()
    solver.build_model(verbose=True)
    solver.solve()
    print(f"Status: {solver.model.Status if solver.model else 'N/A'}")
    print(f"Objective: {solver.objective_value()}")
    return 0


if __name__ == "__main__":
    main([])
