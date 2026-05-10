import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os


def solve_power_schedule():
    # ---------------------------------------------------------
    # 1. Read configuration file (instance.json)
    # ---------------------------------------------------------
    json_path = 'instance.json'
    if not os.path.exists(json_path):
        print(f"Error: Cannot find {json_path}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        instance = json.load(f)

    # Extract parameters
    params = instance['parameters']
    T = params['T']  # Number of time periods (144)
    K = params['K']  # Maximum number of adjustments (10)
    M = params['M']  # Big M / Max capacity (167940.0)

    print(f"Parameters loaded: T={T}, K={K}, M={M}")

    # ---------------------------------------------------------
    # 2. Read data file (D1.csv)
    # ---------------------------------------------------------
    # Try reading from the path defined in json, if not exists try current directory
    csv_rel_path = instance['files']['files_1']['path']  # "data/D1.csv"

    if os.path.exists(csv_rel_path):
        csv_path = csv_rel_path
    elif os.path.exists(os.path.basename(csv_rel_path)):
        csv_path = os.path.basename(csv_rel_path)  # Compatible with file in the same level
    else:
        print(f"Error: Cannot find data file {csv_rel_path}")
        return

    df = pd.read_csv(csv_path)
    # Convert to dictionary: {time_id: demand}
    # Assume first column of csv is id (1..144), second column is demand
    demands = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))

    print(f"Data loaded: Read {len(demands)} demand records")

    # ---------------------------------------------------------
    # 3. Build Gurobi Model
    # ---------------------------------------------------------
    model = gp.Model("PowerGenerationDispatch")

    # --- Variable Declaration ---

    # P[t]: Power generation at time period t
    # Upper bound is M, lower bound is current demand (Demand_t), satisfying demand constraint directly
    P = {}
    for t in range(1, T + 1):
        P[t] = model.addVar(lb=demands[t], ub=M, vtype=GRB.CONTINUOUS, name=f"Power_{t}")

    # y[t]: Whether adjustment occurs at time period t (relative to t-1)
    # Concept of "adjustment" only starts from t=2
    y = {}
    for t in range(2, T + 1):
        y[t] = model.addVar(vtype=GRB.BINARY, name=f"IsAdjust_{t}")

    # --- Objective Function ---
    # Minimize Total Power Generation
    model.setObjective(gp.quicksum(P[t] for t in range(1, T + 1)), GRB.MINIMIZE)

    # --- Constraints ---

    # 1. Adjustment count limit (Cardinality Constraint)
    # Total number of adjustments within the cycle does not exceed K
    model.addConstr(gp.quicksum(y[t] for t in range(2, T + 1)) <= K, name="MaxAdjustmentLimit")

    # 2. State transition/logic constraints (Big-M formulation)
    # If y[t] == 0 (no adjustment), then P[t] == P[t-1]
    # i.e.: P[t] - P[t-1] <= M * y[t]   and   P[t-1] - P[t] <= M * y[t]
    # If y[t] == 1, variation allowed between -M and M (practically limited by Capacity)
    for t in range(2, T + 1):
        model.addConstr(P[t] - P[t - 1] <= M * y[t], name=f"Link_Up_{t}")
        model.addConstr(P[t - 1] - P[t] <= M * y[t], name=f"Link_Down_{t}")

    # ---------------------------------------------------------
    # 4. Solve and Output
    # ---------------------------------------------------------
    # Set time limit or gap (optional)
    model.setParam('TimeLimit', 60)
    model.setParam('MIPGap', 0.0001)

    print("\nStarting solution...")
    model.optimize()

    print("\n" + "=" * 30)
    if model.status == GRB.OPTIMAL:
        print(f"[Optimal Solution Found]")
        print(f"Minimum Total Power Generation (Optimal Value): {model.objVal:,.2f}")

        # Count actual adjustments
        adjust_count = sum(y[t].x for t in range(2, T + 1))
        print(f"Actual adjustment count: {int(adjust_count)} / {K}")

        # Output simple schedule table
        print("\n--- Schedule Summary (Periods with Adjustments) ---")
        prev_p = P[1].x
        print(f"T=1  : Power = {prev_p:.2f} (Demand: {demands[1]}) [Initial]")

        for t in range(2, T + 1):
            curr_p = P[t].x
            is_adj = y[t].x > 0.5
            if is_adj:
                diff = curr_p - prev_p
                direction = "Up" if diff > 0 else "Down"
                print(f"T={t:<3}: Power = {curr_p:.2f} (Demand: {demands[t]}) -> [{direction} {abs(diff):.2f}]")
                prev_p = curr_p
            # Option to print all periods, only printing changes here for brevity

    else:
        print("Optimal solution not found. Gurobi Status:", model.status)
    print("=" * 30)


if __name__ == "__main__":
    solve_power_schedule()