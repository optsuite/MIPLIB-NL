import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def solve_transportation_problem():
    # 1. Read data
    try:
        # index_col=0 ensures the first column (ID) is used as the index
        c1_fixed_cost = pd.read_csv("data/C1.csv", index_col=0)  # Fixed cost
        c2_unit_cost = pd.read_csv("data/C2.csv", index_col=0)  # Unit transportation cost
        c3_supply = pd.read_csv("data/C3.csv", index_col=0)  # Factory supply
        c4_demand = pd.read_csv("data/C4.csv", index_col=0)  # Customer demand
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        return

    # Extract sets
    factories = c3_supply.index.tolist()  # e.g., [0, 1, 2, 3]
    customers = c4_demand.index.tolist()  # e.g., [0, 1, 2, 3, 4, 5]

    # Ensure column name format consistency (convert column names to integers for indexing)
    c1_fixed_cost.columns = c1_fixed_cost.columns.astype(int)
    c2_unit_cost.columns = c2_unit_cost.columns.astype(int)

    # 2. Initialize model
    model = gp.Model("Fixed_Charge_Transportation")

    # 3. Define variables
    x = {}  # Transportation quantity (Continuous)
    y = {}  # Route status (Binary)

    for i in factories:
        for j in customers:
            # X_ij >= 0
            x[i, j] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"X_{i}_{j}")
            # Y_ij in {0, 1}
            y[i, j] = model.addVar(vtype=GRB.BINARY, name=f"Y_{i}_{j}")

    # 4. Set objective function
    # Minimize sum(UnitCost * X + FixedCost * Y)
    obj_expr = gp.quicksum(
        c2_unit_cost.loc[i, j] * x[i, j] +
        c1_fixed_cost.loc[i, j] * y[i, j]
        for i in factories for j in customers
    )
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # 5. Add constraints

    # (A) Supply constraints: Total amount shipped from each factory equals its supply
    for i in factories:
        supply = c3_supply.loc[i, "Supply"]
        model.addConstr(
            gp.quicksum(x[i, j] for j in customers) == supply,
            name=f"Supply_Constraint_Factory_{i}"
        )

    # (B) Demand constraints: Total amount received by each customer equals its demand
    for j in customers:
        demand = c4_demand.loc[j, "Demand"]
        model.addConstr(
            gp.quicksum(x[i, j] for i in factories) == demand,
            name=f"Demand_Constraint_Customer_{j}"
        )

    # (C) Logical linking constraints (Big-M):
    # If Y=0 (not open), then X must be 0.
    # If Y=1 (open), then X <= M.
    # M can be min(Supply, Demand) as a sufficiently large upper bound.
    for i in factories:
        for j in customers:
            M = min(c3_supply.loc[i, "Supply"], c4_demand.loc[j, "Demand"])
            model.addConstr(
                x[i, j] <= M * y[i, j],
                name=f"Linking_Constraint_{i}_{j}"
            )

    # 6. Solve model
    model.optimize()

    # 7. Output results
    if model.status == GRB.OPTIMAL:
        print("\n=== Optimal solution found ===")
        print(f"Minimum Total Cost (Objective Value): {model.objVal:.2f}")

        print("\nDetailed Transportation Plan:")
        print(f"{'Factory':<10} {'Customer':<10} {'Flow':<10} {'Route Status'}")
        print("-" * 45)
        for i in factories:
            for j in customers:
                if x[i, j].x > 0.0001:  # Print only paths with flow
                    print(f"{i:<10} {j:<10} {x[i, j].x:<10.2f} {'Open'}")

        # Can also save results to CSV
        # output_df = pd.DataFrame([[i, j, x[i, j].x] for i in factories for j in customers], columns=['Factory', 'Customer', 'Flow'])
        # output_df.to_csv("solution.csv", index=False)

    else:
        print("Optimal solution not found.")


if __name__ == "__main__":
    solve_transportation_problem()