import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os

def solve_problem():
    # Define problem path
    problem_path = "./problem.json"
    
    # Read problem.json with utf-8 encoding
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return
        
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    # Get file paths relative to the problem directory
    base_dir = os.path.dirname(os.path.abspath(problem_path))
    warehouses_file = os.path.join(base_dir, problem_data['files']['warehouses']['path'])
    stores_file = os.path.join(base_dir, problem_data['files']['stores']['path'])
    routes_file = os.path.join(base_dir, problem_data['files']['routes']['path'])
    
    # Load data using pandas
    warehouses_df = pd.read_csv(warehouses_file)
    stores_df = pd.read_csv(stores_file)
    routes_df = pd.read_csv(routes_file)
    
    # Create Gurobi model
    model = gp.Model("Logistics_Optimization")
    
    # Set log file path and redirect Gurobi output
    log_file_path = os.path.join(base_dir, "logs", "log.txt")
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    model.setParam('LogFile', log_file_path)
    
    # Decision Variables
    # x[w_id, s_id]: quantity shipped
    # y[w_id, s_id]: binary activation variable
    x = {}
    y = {}
    
    # Add variables and capacity constraints
    for _, row in routes_df.iterrows():
        w_id = int(row['warehouse_id'])
        s_id = int(row['store_id'])
        v_cost = row['variable_cost']
        f_cost = row['fixed_cost']
        cap = row['capacity']
        
        x[w_id, s_id] = model.addVar(lb=0, ub=cap, obj=v_cost, name=f"x_{w_id}_{s_id}")
        y[w_id, s_id] = model.addVar(vtype=GRB.BINARY, obj=f_cost, name=f"y_{w_id}_{s_id}")
        
        # Capacity and Activation constraint: x[i, j] <= capacity * y[i, j]
        model.addConstr(x[w_id, s_id] <= cap * y[w_id, s_id], name=f"cap_{w_id}_{s_id}")
    
    # Supply constraints: sum(x[w, s] for s) <= supply[w]
    for _, row in warehouses_df.iterrows():
        w_id = int(row['id'])
        supply = row['supply']
        # Filter routes for this warehouse
        relevant_stores = routes_df[routes_df['warehouse_id'] == w_id]['store_id'].tolist()
        model.addConstr(gp.quicksum(x[w_id, s_id] for s_id in relevant_stores) <= supply, name=f"supply_{w_id}")
        
    # Demand constraints: sum(x[w, s] for w) == demand[s]
    for _, row in stores_df.iterrows():
        s_id = int(row['id'])
        demand = row['demand']
        # Filter routes for this store
        relevant_warehouses = routes_df[routes_df['store_id'] == s_id]['warehouse_id'].tolist()
        model.addConstr(gp.quicksum(x[w_id, s_id] for w_id in relevant_warehouses) == demand, name=f"demand_{s_id}")
        
    # Optimize the model
    model.optimize()
    
    # Append key solution information to the log file
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*30 + "\n")
        f.write("Key Solution Information:\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Optimal Total Cost: {model.objVal:.2f}\n")
            f.write("Selected Routes (Activated Lanes):\n")
            for (w_id, s_id), var in y.items():
                if var.X > 0.5:
                    quantity = x[w_id, s_id].X
                    f.write(f"Warehouse {w_id} -> Store {s_id}: Quantity = {quantity:.2f}\n")
        elif model.status == GRB.INFEASIBLE:
            f.write("Model is infeasible.\n")
        else:
            f.write(f"Optimization ended with status {model.status}\n")

if __name__ == "__main__":
    solve_problem()
