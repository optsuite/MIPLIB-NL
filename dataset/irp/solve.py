import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def solve_irp_with_gurobi():
    # ================= 1. Read Data =================
    print("Reading data files...")
    try:
        # Read candidate routes and their costs (Variables & Objective)
        # Assuming files are in the current directory, modify path if not
        df_c1 = pd.read_csv('data/C1.csv')

        # Read constraint coverage relationships (Constraints)
        df_c2 = pd.read_csv('data/C2.csv')
    except FileNotFoundError:
        print("Error: C1.csv or C2.csv file not found. Please ensure files are in the current working directory.")
        return

    # ================= 2. Build Model =================
    # Create Gurobi model
    model = gp.Model("IRP_SetPartitioning")

    print(f"Data Overview: {len(df_c1)} candidate plans, {df_c2['Constraint_ID'].nunique()} constraint requirements")

    # --- Create Decision Variables ---
    # Create a binary variable (0/1) for each row in table C1
    # x[route_id] = 1 means select this route, 0 means do not select
    # Objective function coefficients are specified via obj parameter when creating variables
    print("Creating decision variables...")
    x = {}
    for idx, row in df_c1.iterrows():
        route_id = row['Candidate_Route_ID']
        cost = row['Cost']
        x[route_id] = model.addVar(vtype=GRB.BINARY, obj=cost, name=route_id)

    # --- Create Constraints ---
    # Group by Constraint_ID, each group corresponds to a constraint
    # Constraint logic: For each requirement (Constraint_ID), the sum of selected covering plans must equal 1
    # sum(x[j]) == 1  for all constraints i
    print("Building constraints...")
    grouped = df_c2.groupby('Constraint_ID')

    for constraint_id, group in grouped:
        # Get all candidate plan IDs involved in this constraint
        covering_routes = group['Covering_Route_ID'].tolist()

        # Use quicksum to build linear expression
        model.addConstr(
            gp.quicksum(x[rid] for rid in covering_routes if rid in x) == 1,
            name=constraint_id
        )

    # ================= 3. Solve =================
    print("Starting to solve...")
    # Set solution parameters (optional)
    model.setParam('OutputFlag', 1)  # Show solution log
    model.setParam('MIPGap', 0.0)  # Require exact solution

    model.optimize()

    # ================= 4. Output Results =================
    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 30)
        print(f"Solution successful!")
        print(f"Minimum Total Cost (Objective Value): {model.objVal:,.2f}")
        print("=" * 30)

        print("\nSelected optimal delivery plan combination:")
        selected_routes = []
        total_cost_check = 0

        for v in model.getVars():
            if v.x > 0.5:  # Floating point tolerance check
                print(f" - {v.varName} (Cost: {v.obj:.2f})")
                selected_routes.append(v.varName)
                total_cost_check += v.obj

        print(f"\nA total of {len(selected_routes)} routes selected.")
    else:
        print("No optimal solution found. Status code:", model.status)


if __name__ == "__main__":
    solve_irp_with_gurobi()