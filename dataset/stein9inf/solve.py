import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def solve_drone_problem():
    # 1. Read instance.json to get parameters K1, K2
    try:
        with open('instance.json', 'r', encoding='utf-8') as f:
            instance_data = json.load(f)
            # Note: M and N in json may differ from actual row/column counts in data.
            # Here we rely on K1, K2 and the actual content of S1.csv.
            K1 = instance_data['parameters']['K1']
            K2 = instance_data['parameters']['K2']
            print(f"Parameter settings: K1 = {K1}, K2 = {K2}")
    except FileNotFoundError:
        print("instance.json file not found.")
        return

    # 2. Read S1.csv to get coverage relationships
    try:
        df = pd.read_csv('data/S1.csv')
    except FileNotFoundError:
        print("S1.csv file not found.")
        return

    # Extract all hangars and locations
    # Assume CSV column names are Location_ID, Hangar_1, Hangar_2, Hangar_3
    # If the number of hangar columns is not fixed, adjust dynamically
    hangar_columns = [col for col in df.columns if 'Hangar' in col]

    # Build coverage map: location -> set of hangars
    coverage_map = {}
    all_hangars = set()

    for idx, row in df.iterrows():
        loc = row['Location_ID']
        possible_hangars = []
        for col in hangar_columns:
            h = row[col]
            if pd.notna(h):
                h = str(h).strip()
                possible_hangars.append(h)
                all_hangars.add(h)
        coverage_map[loc] = possible_hangars

    sorted_hangars = sorted(list(all_hangars))
    print(f"Detected {len(coverage_map)} surveillance points and {len(sorted_hangars)} candidate hangars.")

    # 3. Build Gurobi model
    model = gp.Model("DroneSurveillance")

    # Define variables: x[j] is a 0/1 variable indicating whether hangar j is enabled
    # vtype=GRB.BINARY indicates binary variable
    x = model.addVars(sorted_hangars, vtype=GRB.BINARY, name="x")

    # 4. Add constraints

    # (1) Coverage constraint: Each location must have at least one responsible hangar enabled
    for loc, hangars in coverage_map.items():
        if not hangars:
            print(f"Warning: Location {loc} has no optional hangar coverage! The model will be infeasible.")
        model.addConstr(gp.quicksum(x[h] for h in hangars) >= 1, name=f"Cover_{loc}")

    # (2) Total investment constraint: K1 <= sum(x) <= K2
    total_investment = gp.quicksum(x[h] for h in sorted_hangars)
    model.addConstr(total_investment >= K1, name="Min_Capacity_K1")
    model.addConstr(total_investment <= K2, name="Max_Capacity_K2")

    # 5. Set objective function: Minimize total investment
    model.setObjective(total_investment, GRB.MINIMIZE)

    # 6. Solve
    print("\nStarting solution...")
    model.optimize()

    # 7. Output results
    if model.status == GRB.OPTIMAL:
        print(f"\nOptimal solution found! Minimum investment: {model.ObjVal}")
        print("Enabled hangars:")
        selected_hangars = []
        for h in sorted_hangars:
            if x[h].X > 0.5:  # Check if variable value is 1
                selected_hangars.append(h)
                print(f" - {h}")
        print(f"Total {len(selected_hangars)} hangars enabled.")
    elif model.status == GRB.INFEASIBLE:
        print("\nProblem Infeasible.")
        print("It may be that the restrictions of K1/K2 make it impossible to cover all points.")
        # Calculate minimum required if ignoring capacity limits
        print("Suggest checking if there exists a hangar combination satisfying coverage requirements within [K1, K2] range.")
    else:
        print(f"\nSolving finished, status code: {model.status}")


if __name__ == "__main__":
    solve_drone_problem()