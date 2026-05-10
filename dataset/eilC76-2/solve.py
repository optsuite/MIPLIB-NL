import gurobipy as gp
from gurobipy import GRB
import csv
import os


def solve_cvrp_set_partitioning():
    # File path configuration
    c1_path = os.path.join('data', 'C1.csv')
    c2_path = os.path.join('data', 'C2.csv')

    # ---------------------------------------------------------
    # 1. Read data
    # ---------------------------------------------------------
    print("Reading data files...")

    # Read C1.csv: Route costs
    # Format: RouteID, Cost
    route_costs = {}
    try:
        with open(c1_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row: continue
                # Skip possible header row (if first column is not a number)
                if not row[0].strip().isdigit(): continue

                rid = int(row[0])
                cost = float(row[1])
                route_costs[rid] = cost
    except FileNotFoundError:
        print(f"Error: File not found {c1_path}")
        return

    # Read C2.csv: Route-Customer coverage relationship
    # Format: RouteID, CustomerID1, CustomerID2, ...
    # We need to build a reverse mapping: customer_id -> [list of route_ids that serve this customer]
    customer_to_routes = {}

    try:
        with open(c2_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if not row: continue
                if not row[0].strip().isdigit(): continue

                rid = int(row[0])
                # If the route ID does not exist in the cost table, skip it
                if rid not in route_costs:
                    continue

                # row[1:] is the list of customers served by this route
                served_customers = [int(c) for c in row[1:] if c.strip().isdigit()]

                for cust_id in served_customers:
                    if cust_id not in customer_to_routes:
                        customer_to_routes[cust_id] = []
                    customer_to_routes[cust_id].append(rid)

    except FileNotFoundError:
        print(f"Error: File not found {c2_path}")
        return

    all_customers = sorted(customer_to_routes.keys())
    print(f"Data reading completed: {len(route_costs)} candidate routes, {len(all_customers)} customers.")

    # ---------------------------------------------------------
    # 2. Build Gurobi model
    # ---------------------------------------------------------
    print("Building optimization model...")
    model = gp.Model("CVRP_Set_Partitioning")

    # Add variables: x[route_id] = 1 if the route is selected, else 0
    # Objective coefficients are specified directly via obj parameter in addVars
    x = model.addVars(route_costs.keys(), vtype=GRB.BINARY, obj=route_costs, name="x")

    # Add constraints: Each customer must be served exactly once
    # sum(x[r] for r in routes_serving_customer_c) == 1
    for cust_id in all_customers:
        serving_routes = customer_to_routes[cust_id]
        model.addConstr(gp.quicksum(x[r] for r in serving_routes) == 1, name=f"cover_cust_{cust_id}")

    # ---------------------------------------------------------
    # 3. Solve
    # ---------------------------------------------------------
    print("Starting solve...")
    # Set solver time limit (optional, e.g., 300 seconds)
    # model.setParam('TimeLimit', 300)
    model.optimize()

    # ---------------------------------------------------------
    # 4. Output results
    # ---------------------------------------------------------
    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 40)
        print(f"Optimal solution found!")
        print(f"Minimum total cost: {model.objVal:.6f}")
        print("=" * 40)

        print("Selected route plan:")
        selected_routes = []
        for rid in route_costs:
            if x[rid].X > 0.5:  # Check if variable value is 1
                selected_routes.append(rid)
                print(f"  - Route ID: {rid}, Cost: {route_costs[rid]}")

        print(f"Total selected {len(selected_routes)} routes.")

        # Optional: Save results to file
        with open('solution.txt', 'w') as f:
            f.write(f"Objective Value: {model.objVal}\n")
            f.write("Selected Routes:\n")
            for rid in selected_routes:
                f.write(f"{rid}\n")

    elif model.status == GRB.INFEASIBLE:
        print("Model infeasible. Maybe no set of routes can exactly cover all customers.")
        # Compute IIS (Irreducible Inconsistent Subsystem)
        model.computeIIS()
        model.write("model.ilp")
        print("Conflict constraints written to model.ilp")
    else:
        print(f"Solving finished, status code: {model.status}")


if __name__ == "__main__":
    solve_cvrp_set_partitioning()