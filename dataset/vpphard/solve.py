"""
Vehicle Positioning Problem (vpphard) Solver

Reads instance.json and data/*.csv under instances/vpphard,
constructs and solves the reference model using Gurobi (see model.md).

The optimal objective value for this instance should be 5 (optimal_value is also provided in instance.json for verification).
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

try:
    import gurobipy as gp
    from gurobipy import GRB
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "Failed to import/use gurobipy. Please ensure Gurobi is installed and the license is configured."
    ) from exc


@dataclass(frozen=True)
class InstanceParams:
    quota_batch_size: int
    expected_optimal_value: Optional[float]


class VPPHardSolver:
    def __init__(self, instance_folder: str):
        self.instance_folder = instance_folder
        self.data_folder = os.path.join(instance_folder, "data")

        self.params: Optional[InstanceParams] = None

        self.units: Optional[pd.DataFrame] = None
        self.targets: Optional[pd.DataFrame] = None
        self.options: Optional[pd.DataFrame] = None
        self.balance_rules: Optional[pd.DataFrame] = None
        self.windows: Optional[pd.DataFrame] = None
        self.steps: Optional[pd.DataFrame] = None
        self.option_steps: Optional[pd.DataFrame] = None
        self.quota_pools: Optional[pd.DataFrame] = None
        self.option_quota_pools: Optional[pd.DataFrame] = None
        self.quotas: Optional[pd.DataFrame] = None

        self.model: Optional[gp.Model] = None
        self.x: Optional[gp.tupledict] = None
        self.open: Optional[gp.tupledict] = None

    def _path(self, *parts: str) -> str:
        return os.path.join(self.instance_folder, *parts)

    def load_data(self) -> None:
        print("Loading data...")

        instance_path = self._path("instance.json")
        with open(instance_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        parameters = config.get("parameters", {})
        quota_batch_size = int(parameters.get("quota_batch_size", 5))

        expected = config.get("optimal_value")
        expected_opt = float(expected) if expected is not None else None

        self.params = InstanceParams(
            quota_batch_size=quota_batch_size,
            expected_optimal_value=expected_opt,
        )

        def read_csv(name: str) -> pd.DataFrame:
            p = os.path.join(self.data_folder, name)
            if not os.path.exists(p):
                raise FileNotFoundError(f"Data file not found: {p}")
            return pd.read_csv(p)

        self.units = read_csv("units.csv")
        self.targets = read_csv("targets.csv")
        self.options = read_csv("relocation_options.csv")
        self.balance_rules = read_csv("balance_rules.csv")
        self.windows = read_csv("operation_windows.csv")
        self.steps = read_csv("steps.csv")
        self.option_steps = read_csv("option_steps.csv")
        self.quota_pools = read_csv("quota_pools.csv")
        self.option_quota_pools = read_csv("option_quota_pools.csv")

        # Kept as a "summary hint", but not used for modeling constraints (real constraints are given by pools)
        quotas_path = os.path.join(self.data_folder, "quotas.csv")
        self.quotas = pd.read_csv(quotas_path) if os.path.exists(quotas_path) else None

        # Validate necessary fields
        for col in ["window_id", "base_capacity", "open_cost"]:
            if col not in self.windows.columns:
                raise ValueError(f"operation_windows.csv missing column: {col}")

        print(
            f"  locations: {self.targets['location_id'].nunique()}, "
            f"units: {self.units['unit_id'].nunique()}, "
            f"options: {self.options['option_id'].nunique()}, "
            f"windows: {self.windows['window_id'].nunique()}, "
            f"pools: {self.quota_pools['pool_id'].nunique()}, "
            f"balance_rules: {len(self.balance_rules)}"
        )
        print("Data loading completed.\n")

    def build_model(self, time_limit_s: int = 600, mip_gap: float = 1e-4, verbose: bool = True) -> None:
        if self.params is None:
            raise RuntimeError("Please call load_data() first")

        assert self.units is not None
        assert self.targets is not None
        assert self.options is not None
        assert self.balance_rules is not None
        assert self.windows is not None
        assert self.steps is not None
        assert self.option_steps is not None
        assert self.quota_pools is not None
        assert self.option_quota_pools is not None

        print("Building optimization model...")

        model = gp.Model("vpphard_vehicle_positioning")
        model.setParam("OutputFlag", 1 if verbose else 0)
        model.setParam("TimeLimit", time_limit_s)
        model.setParam("MIPGap", mip_gap)

        # 1) Derived: Supplement start_location_id for each option
        start_of_unit = dict(
            zip(self.units["unit_id"].astype(int), self.units["start_location_id"].astype(int))
        )
        options = self.options.copy()
        options["unit_id"] = options["unit_id"].astype(int)
        options["dest_location_id"] = options["dest_location_id"].astype(int)
        options["wave_id"] = options["wave_id"].astype(int)
        options["start_location_id"] = options["unit_id"].map(start_of_unit)

        if options["start_location_id"].isna().any():
            missing = options[options["start_location_id"].isna()]["unit_id"].unique()[:10]
            raise ValueError(f"Unknown unit_id in relocation_options.csv (example): {missing}")

        # 2) Derived: option -> window demand (option_steps -> steps -> window_id)
        steps = self.steps.copy()
        steps["step_id"] = steps["step_id"].astype(str)
        steps["window_id"] = steps["window_id"].astype(str)
        step_to_window = dict(zip(steps["step_id"], steps["window_id"]))

        option_steps = self.option_steps.copy()
        option_steps["step_id"] = option_steps["step_id"].astype(str)
        option_steps["option_id"] = option_steps["option_id"].astype(str)
        option_steps["window_id"] = option_steps["step_id"].map(step_to_window)

        if option_steps["window_id"].isna().any():
            missing = option_steps[option_steps["window_id"].isna()]["step_id"].unique()[:10]
            raise ValueError(f"Unknown step_id in option_steps.csv (example): {missing}")

        win_to_options: Dict[str, List[str]] = (
            option_steps.groupby("window_id")["option_id"].apply(list).to_dict()
        )

        # 3) Derived: pool -> options
        option_quota_pools = self.option_quota_pools.copy()
        option_quota_pools["option_id"] = option_quota_pools["option_id"].astype(str)
        option_quota_pools["pool_id"] = option_quota_pools["pool_id"].astype(str)
        pool_to_options: Dict[str, List[str]] = (
            option_quota_pools.groupby("pool_id")["option_id"].apply(list).to_dict()
        )

        pool_size = dict(
            zip(self.quota_pools["pool_id"].astype(str), self.quota_pools["pool_size"].astype(int))
        )

        # 4) Variables
        option_ids = options["option_id"].astype(str).tolist()
        window_ids = self.windows["window_id"].astype(str).tolist()

        x = model.addVars(option_ids, vtype=GRB.BINARY, name="x")
        open_var = model.addVars(window_ids, vtype=GRB.BINARY, name="open")

        # 5) Objective
        open_cost = dict(
            zip(self.windows["window_id"].astype(str), self.windows["open_cost"].astype(float))
        )
        model.setObjective(gp.quicksum(open_cost[w] * open_var[w] for w in window_ids), GRB.MINIMIZE)

        # 6) Constraint: Each vehicle selects exactly one plan
        for unit_id, grp in options.groupby("unit_id"):
            model.addConstr(gp.quicksum(x[o] for o in grp["option_id"].astype(str)) == 1, name=f"assign_unit_{unit_id}")

        # 7) Constraint: Number of units in place at each destination in the early morning
        required = dict(
            zip(self.targets["location_id"].astype(int), self.targets["required_units"].astype(int))
        )
        for loc, req in required.items():
            grp = options[options["dest_location_id"] == loc]
            model.addConstr(gp.quicksum(x[o] for o in grp["option_id"].astype(str)) == req, name=f"target_{loc}")

        # 8) Constraint: Quota pools (each pool must be filled to pool_size)
        for pool_id, olist in pool_to_options.items():
            if pool_id not in pool_size:
                raise ValueError(f"option_quota_pools.csv references unknown pool_id: {pool_id}")
            model.addConstr(gp.quicksum(x[o] for o in olist) == int(pool_size[pool_id]), name=f"pool_{pool_id}")

        # 9) Constraint: Key hub wave balancing (arrivals = departures)
        rules = self.balance_rules.copy()
        rules = rules[rules["rule_kind"].astype(str) == "EXCHANGE_ONLY"]
        rules["location_id"] = rules["location_id"].astype(int)
        rules["wave_id"] = rules["wave_id"].astype(int)

        for _, r in rules.iterrows():
            loc = int(r["location_id"])
            wave = int(r["wave_id"])
            arrivals = options[(options["dest_location_id"] == loc) & (options["wave_id"] == wave)]
            departures = options[(options["start_location_id"] == loc) & (options["wave_id"] == wave)]
            model.addConstr(
                gp.quicksum(x[o] for o in arrivals["option_id"].astype(str))
                - gp.quicksum(x[o] for o in departures["option_id"].astype(str))
                == 0,
                name=f"balance_{loc}_{wave}",
            )

        # 10) Constraint: Window capacity (baseline + open)
        base_capacity = dict(
            zip(self.windows["window_id"].astype(str), self.windows["base_capacity"].astype(int))
        )
        for w, olist in win_to_options.items():
            model.addConstr(
                gp.quicksum(x[o] for o in olist) <= int(base_capacity[w]) + open_var[w],
                name=f"window_{w}",
            )

        # For windows without any option dependency, open is meaningless, fix to 0 (can speed up)
        windows_with_options = set(win_to_options.keys())
        for w in window_ids:
            if w not in windows_with_options:
                model.addConstr(open_var[w] == 0, name=f"unused_window_{w}")

        model.update()
        self.model = model
        self.x = x
        self.open = open_var

        print(f"Model construction completed: vars={model.NumVars}, constrs={model.NumConstrs}\n")

    def solve(self) -> Tuple[bool, Optional[float]]:
        if self.model is None or self.x is None or self.open is None or self.params is None:
            raise RuntimeError("Please call build_model() first")

        print("=" * 60)
        print("Starting solve...")
        print("=" * 60)
        self.model.optimize()

        status = self.model.Status
        if status == GRB.OPTIMAL:
            obj = float(self.model.ObjVal)
            opened = int(round(sum(self.open[w].X for w in self.open.keys())))
            print(f"\nOptimal solution found: objective={obj:.6f}, opened_windows={opened}")

            if self.params.expected_optimal_value is not None:
                exp = self.params.expected_optimal_value
                ok = abs(obj - exp) <= 1e-6
                print(f"Optimal value check: expected={exp:g} -> {'PASS' if ok else 'FAIL'}")
                return ok, obj

            return True, obj

        if status == GRB.TIME_LIMIT and self.model.SolCount > 0:
            obj = float(self.model.ObjVal)
            print(f"\nTime limit reached but feasible solution found: objective={obj:.6f}")
            return False, obj

        if status == GRB.INFEASIBLE:
            print("\nModel is infeasible. Computing IIS ...")
            self.model.computeIIS()
            bad = [c.ConstrName for c in self.model.getConstrs() if c.IISConstr]
            print(f"Number of IIS constraints: {len(bad)} (showing first 30 only)")
            for name in bad[:30]:
                print(f"  - {name}")
            return False, None

        print(f"\nSolve finished, status code: {status}")
        return False, None


def main() -> None:
    parser = argparse.ArgumentParser(description="Solve vpphard (Vehicle Positioning Problem) instance.")
    parser.add_argument(
        "instance_folder",
        nargs="?",
        default=os.path.dirname(__file__),
        help="Instance directory (default: directory containing solver.py)",
    )
    parser.add_argument("--time-limit", type=int, default=600, help="Gurobi TimeLimit (seconds)")
    parser.add_argument("--mip-gap", type=float, default=1e-4, help="Gurobi MIPGap")
    parser.add_argument("--quiet", action="store_true", help="Disable Gurobi solver logging")
    args = parser.parse_args()

    solver = VPPHardSolver(args.instance_folder)
    solver.load_data()
    solver.build_model(time_limit_s=args.time_limit, mip_gap=args.mip_gap, verbose=not args.quiet)
    ok, obj = solver.solve()
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()