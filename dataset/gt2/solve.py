import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def solve_fleet_assignment():
    # 1. Read data files
    try:
        df_c1 = pd.read_csv('data/C1.csv')  # Vehicle inventory
        df_c2 = pd.read_csv('data/C2.csv')  # Transportation cost matrix
        df_c3 = pd.read_csv('data/C3.csv')  # Transportation capacity matrix
        df_c4 = pd.read_csv('data/C4.csv')  # Destination demand
    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        return

    # 2. Data preprocessing and index extraction
    # Extract vehicle ID list (from C1)
    vehicles = df_c1['VehicleID'].tolist()

    # Extract destination ID list (from C2 column names, excluding 'VehicleID')
    # Note: Column names are usually strings '1', '2' etc., we need to match with LocationID in C4
    destinations = [col for col in df_c2.columns if col != 'VehicleID']

    # Convert data to dictionary for quick access
    # Inventory: {VehicleID: Quantity}
    supply = dict(zip(df_c1['VehicleID'], df_c1['Quantity']))

    # Demand: {LocationID: RequiredQuantity}
    # Ensure destination ID types are consistent (usually column names are str, C4 might be int)
    demand = dict(zip(df_c4['LocationID'].astype(str), df_c4['RequiredQuantity']))

    # Cost: {(VehicleID, LocationID): Cost}
    costs = {}
    for _, row in df_c2.iterrows():
        vid = row['VehicleID']
        for dest in destinations:
            costs[(vid, dest)] = row[dest]

    # Capacity: {(VehicleID, LocationID): Capacity}
    capacities = {}
    for _, row in df_c3.iterrows():
        vid = row['VehicleID']
        for dest in destinations:
            capacities[(vid, dest)] = row[dest]

    # 3. Initialize Gurobi model
    model = gp.Model("FleetAssignment")

    # 4. Create decision variables
    # x[i, j]: Quantity of vehicle i sent to destination j
    # lb=0, vtype=GRB.INTEGER (non-negative integer)
    x = model.addVars(vehicles, destinations, vtype=GRB.INTEGER, name="x")

    # 5. Set objective function: Minimize total cost
    model.setObjective(
        gp.quicksum(costs[(i, j)] * x[i, j] for i in vehicles for j in destinations),
        GRB.MINIMIZE
    )

    # 6. Add constraints

    # Constraint 1: Supply Constraints
    # For each vehicle i, total quantity sent to all destinations <= inventory quantity
    for i in vehicles:
        model.addConstr(
            gp.quicksum(x[i, j] for j in destinations) <= supply[i],
            name=f"Supply_Vehicle_{i}"
        )

    # Constraint 2: Demand Constraints
    # For each destination j, total cargo transported >= demand quantity
    for j in destinations:
        model.addConstr(
            gp.quicksum(capacities[(i, j)] * x[i, j] for i in vehicles) >= demand[j],
            name=f"Demand_Location_{j}"
        )

    # 7. Solve model
    print("Starting to solve model...")
    model.optimize()

    # 8. Output results
    if model.status == GRB.OPTIMAL:
        print("\nOptimal solution found!")
        print(f"Minimum total cost: {model.ObjVal:,.2f}")

        print("\nDetailed schedule:")
        print("-" * 40)
        print(f"{'VehicleID':<10} {'DestID':<10} {'Quantity':<10}")
        print("-" * 40)

        for i in vehicles:
            for j in destinations:
                if x[i, j].X > 0.5:  # Print non-zero variables
                    print(f"{i:<10} {j:<10} {int(x[i, j].X):<10}")

        # Export solution to file (optional)
        # model.write("solution.sol")
    else:
        print("\nOptimal solution not found. Model status:", model.status)


if __name__ == "__main__":
    solve_fleet_assignment()