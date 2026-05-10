import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def solve_crew_scheduling():
    # ===============================
    # 1. Read data
    # ===============================
    print("Reading data files...")
    # C1.csv contains variable info: pairing_id (schedule scheme), cost
    df_costs = pd.read_csv('data/C1.csv')

    # C2.csv contains the sparse structure of the constraint matrix: pairing_id, flight_leg_id (covered flight)
    df_structure = pd.read_csv('data/C2.csv')

    # ===============================
    # 2. Data preprocessing
    # ===============================
    print("Preprocessing data...")

    # Convert costs to a dictionary for easy lookup by ID: {'x1': 2164.0, ...}
    cost_dict = dict(zip(df_costs['pairing_id'], df_costs['cost']))

    # Get list of all pairing IDs (variable indices)
    pairings = df_costs['pairing_id'].tolist()

    # Group structure data by flight leg ID
    # The goal is to know which pairings can cover each flight leg
    # Result format: {'c1': ['x1', 'x2', ...], 'c2': ['x1', ...]}
    flight_cover_dict = df_structure.groupby('flight_leg_id')['pairing_id'].apply(list).to_dict()

    print(f"Number of variables (pairings): {len(pairings)}")
    print(f"Number of constraints (flight legs): {len(flight_cover_dict)}")

    # ===============================
    # 3. Build Gurobi model
    # ===============================
    print("Building optimization model...")
    model = gp.Model("CrewScheduling")

    # 4. Create decision variables
    # x[j] is a 0-1 variable: 1 means select this pairing, 0 means do not select
    # obj=cost_dict will automatically set the objective function coefficients to the corresponding costs
    x = model.addVars(pairings, vtype=GRB.BINARY, obj=cost_dict, name="x")

    # 5. Add constraints
    # Set partitioning constraint: A * x = 1
    # For every flight leg, the sum of x for all pairings covering it must equal 1
    for flight_leg, covering_pairings in flight_cover_dict.items():
        # gp.quicksum is Gurobi's optimized summation function, faster than sum()
        model.addConstr(
            gp.quicksum(x[p] for p in covering_pairings) == 1,
            name=f"cover_{flight_leg}"
        )

    # Set objective: Minimize total cost
    model.ModelSense = GRB.MINIMIZE

    # (Optional) Set time limit (seconds) or Gap
    # model.Params.TimeLimit = 300
    # model.Params.MIPGap = 0.01

    # ===============================
    # 6. Start solving
    # ===============================
    print("Starting to solve...")
    model.optimize()

    # ===============================
    # 7. Output results
    # ===============================
    if model.status == GRB.OPTIMAL:
        print("\n======== Solved Successfully ========")
        print(f"Minimum Total Cost (Optimal Objective): {model.objVal}")

        print("\nSelected Pairings:")
        selected_pairings = []
        for p in pairings:
            # Check if variable value is close to 1
            if x[p].X > 0.5:
                print(f"  {p}: Cost = {cost_dict[p]}")
                selected_pairings.append({'pairing_id': p, 'cost': cost_dict[p]})

        # Save results to file
        res_df = pd.DataFrame(selected_pairings)
        res_df.to_csv('solution_result.csv', index=False)
        print(f"\nResults saved to 'solution_result.csv'")

    else:
        print("Optimal solution not found. Status Code:", model.status)


if __name__ == "__main__":
    solve_crew_scheduling()