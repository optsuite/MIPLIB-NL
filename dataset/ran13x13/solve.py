import json
import csv
import os
import gurobipy as gp
from gurobipy import GRB

def solve():
    # Define paths
    problem_file = 'problem.json'
    log_file = os.path.join('logs', 'log.txt')
    
    # Ensure spec directory exists for log file
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Read problem.json
    if not os.path.exists(problem_file):
        print(f"Error: {problem_file} not found. Please run this script from the problem directory.")
        return

    with open(problem_file, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Helper function to read CSV data
    def read_csv(file_path):
        data = []
        if not os.path.exists(file_path):
            print(f"Error: Data file {file_path} not found.")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Try to convert numeric values to float
                converted_row = {}
                for k, v in row.items():
                    try:
                        converted_row[k] = float(v)
                    except ValueError:
                        converted_row[k] = v
                data.append(converted_row)
        return data

    # Load data
    files_config = problem_data['files']
    
    warehouses_data = read_csv(files_config['warehouses']['path'])
    stores_data = read_csv(files_config['stores']['path'])
    routes_data = read_csv(files_config['routes']['path'])

    if not warehouses_data or not stores_data or not routes_data:
        print("Error loading data files.")
        return

    # Process data into dictionaries
    # Warehouses: id -> supply
    warehouses = {w['id']: w['supply'] for w in warehouses_data}
    
    # Stores: id -> demand
    stores = {s['id']: s['demand'] for s in stores_data}
    
    # Routes: (warehouse_id, store_id) -> {variable_cost, fixed_cost, capacity}
    routes = {}
    for r in routes_data:
        key = (r['warehouse_id'], r['store_id'])
        routes[key] = {
            'variable_cost': r['variable_cost'],
            'fixed_cost': r['fixed_cost'],
            'capacity': r['capacity']
        }

    # Create Gurobi Model
    model = gp.Model("FixedChargeTransportation")
    
    # Set log file
    model.setParam('LogFile', log_file)

    # Create Variables
    x = {} # Continuous flow variables
    y = {} # Binary open/close variables

    for (w_id, s_id), params in routes.items():
        # Only create variables if warehouse and store exist (sanity check)
        if w_id in warehouses and s_id in stores:
            x[w_id, s_id] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{w_id}_{s_id}")
            y[w_id, s_id] = model.addVar(vtype=GRB.BINARY, name=f"y_{w_id}_{s_id}")

    # Update model to integrate variables
    model.update()

    # Set Objective: Minimize Total Cost (Variable + Fixed)
    obj_expr = gp.LinExpr()
    for w_id, s_id in x:
        params = routes[(w_id, s_id)]
        obj_expr += params['variable_cost'] * x[w_id, s_id] + params['fixed_cost'] * y[w_id, s_id]
    
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # Add Constraints

    # 1. Supply Constraints: Flow out of warehouse <= Supply
    for w_id, supply in warehouses.items():
        model.addConstr(
            gp.quicksum(x[w_id, s_id] for s_id in stores if (w_id, s_id) in x) <= supply,
            name=f"Supply_{w_id}"
        )

    # 2. Demand Constraints: Flow into store == Demand
    for s_id, demand in stores.items():
        model.addConstr(
            gp.quicksum(x[w_id, s_id] for w_id in warehouses if (w_id, s_id) in x) == demand,
            name=f"Demand_{s_id}"
        )

    # 3. Capacity and Linking Constraints: Flow <= Capacity * Open
    for w_id, s_id in x:
        capacity = routes[(w_id, s_id)]['capacity']
        model.addConstr(
            x[w_id, s_id] <= capacity * y[w_id, s_id],
            name=f"Capacity_{w_id}_{s_id}"
        )

    # Optimize
    model.optimize()

    # Output results
    if model.status == GRB.OPTIMAL:
        print(f"\nOptimization Successful.")
        print(f"Optimal Total Cost: {model.objVal:.2f}")
        print("\nSelected Routes and Shipments:")
        
        # Append to log file manually if needed, but Gurobi log captures solver output.
        # We will print the solution details to stdout as requested.
        
        for w_id, s_id in x:
            if y[w_id, s_id].x > 0.5: # If route is open
                flow = x[w_id, s_id].x
                print(f"  Route {w_id} -> {s_id}: Shipped {flow:.2f} units (Capacity: {routes[(w_id, s_id)]['capacity']})")
    else:
        print(f"Optimization ended with status {model.status}")

if __name__ == "__main__":
    solve()
