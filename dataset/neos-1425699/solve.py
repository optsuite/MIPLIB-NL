import gurobipy as gp
from gurobipy import GRB
import pandas as pd


def solve_supply_chain():
    # ----------------------------------------------------------------
    # 1. Data reading and preprocessing
    # ----------------------------------------------------------------
    try:
        # Read fixed costs (cost1.csv - no header)
        cost1 = pd.read_csv('data/cost1.csv', header=None)
        fixed_costs = dict(zip(cost1[0], cost1[1]))
        dcs = list(fixed_costs.keys())

        # Read facility capacities (facility_production.csv - no header)
        prod_cap = pd.read_csv('data/facility_production.csv', header=None)
        capacities = dict(zip(prod_cap[0], prod_cap[1]))
        plants = list(capacities.keys())

        # Read customer demands (q.csv - no header)
        q_df = pd.read_csv('data/q.csv', header=None)
        demands = dict(zip(q_df[0], q_df[1]))
        customers = list(demands.keys())

        # Read transport cost 1: Plant -> DC (cost2.csv - with header)
        cost2 = pd.read_csv('data/cost2.csv', index_col=0)
        transport_cost_1 = {}
        for p in plants:
            for d in dcs:
                transport_cost_1[(p, d)] = cost2.loc[p, d]

        # Read transport cost 2: DC -> Customer (cost3.csv - with header)
        cost3 = pd.read_csv('data/cost3.csv', index_col=0)
        transport_cost_2 = {}
        for d in dcs:
            for c in customers:
                transport_cost_2[(d, c)] = cost3.loc[d, c]

    except FileNotFoundError as e:
        print(f"Error: File {e.filename} not found. Please ensure all csv files are in the current directory.")
        return

    # ----------------------------------------------------------------
    # 2. Build Gurobi Model
    # ----------------------------------------------------------------
    model = gp.Model("SupplyChainNetwork")

    # --- Decision Variables ---
    # y[j]: Whether to open DC j (binary variable)
    y = model.addVars(dcs, vtype=GRB.BINARY, name="y")

    # x[i, j]: Flow from plant i to DC j (integer)
    x = model.addVars(plants, dcs, vtype=GRB.INTEGER, name="x")

    # z[j, k]: Flow from DC j to customer k (integer)
    z = model.addVars(dcs, customers, vtype=GRB.INTEGER, name="z")

    # --- Objective: Minimize total cost (Construction + Primary Transport + Secondary Transport) ---
    obj = (gp.quicksum(fixed_costs[j] * y[j] for j in dcs) +
           gp.quicksum(transport_cost_1[(i, j)] * x[i, j] for i in plants for j in dcs) +
           gp.quicksum(transport_cost_2[(j, k)] * z[j, k] for j in dcs for k in customers))

    model.setObjective(obj, GRB.MINIMIZE)

    # --- Constraints ---

    # 1. Plant capacity constraint: Outflow from each plant <= capacity
    for i in plants:
        model.addConstr(gp.quicksum(x[i, j] for j in dcs) <= capacities[i], name=f"Cap_{i}")

    # 2. Customer demand constraint: Received amount for each customer >= demand
    for k in customers:
        model.addConstr(gp.quicksum(z[j, k] for j in dcs) >= demands[k], name=f"Demand_{k}")

    # 3. Flow conservation constraint: Inflow to DC = Outflow from DC
    for j in dcs:
        model.addConstr(gp.quicksum(x[i, j] for i in plants) == gp.quicksum(z[j, k] for k in customers),
                        name=f"Flow_{j}")

    # 4. Location logic constraint (Big-M): Inflow allowed only if DC is open
    # M can be set to sum of total capacities to ensure feasible flow is not restricted
    M = sum(capacities.values())
    for j in dcs:
        model.addConstr(gp.quicksum(x[i, j] for i in plants) <= M * y[j], name=f"Link_{j}")

    # 5. Must select N3 distribution centers (according to JSON file N3=4)
    model.addConstr(gp.quicksum(y[j] for j in dcs) == 4, name="Select_4_DCs")

    # ----------------------------------------------------------------
    # 3. Solve and Output
    # ----------------------------------------------------------------
    print("\nStarting optimization...")
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print(f"\n--- Optimal solution found ---")
        print(f"Minimum total cost: {model.objVal:,.2f}")

        print("\n[Location Decisions]")
        for j in dcs:
            if y[j].x > 0.5:
                print(f"  - Open: {j} (Fixed Cost: {fixed_costs[j]})")

        print("\n[Logistics Plan Example (Partial)]")
        # Print some non-zero flows for checking
        print("  Primary Transport (Plant -> DC):")
        for i in plants:
            for j in dcs:
                if x[i, j].x > 0:
                    print(f"    {i} -> {j}: {x[i, j].x}")

        print("  Secondary Transport (DC -> Customer):")
        count = 0
        for j in dcs:
            for k in customers:
                if z[j, k].x > 0 and count < 5:  # Print only the first 5 as an example
                    print(f"    {j} -> {k}: {z[j, k].x}")
                    count += 1
    else:
        print("No optimal solution found.")


if __name__ == "__main__":
    solve_supply_chain()