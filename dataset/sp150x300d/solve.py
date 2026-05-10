import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Load problem data
    problem_file = './problem.json'
    if not os.path.exists(problem_file):
        print(f"Error: {problem_file} not found.")
        return

    with open(problem_file, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Paths to data files
    locations_path = problem_data['files']['locations']['path']
    routes_path = problem_data['files']['routes']['path']

    # Load CSV data
    try:
        locations_df = pd.read_csv(locations_path)
        routes_df = pd.read_csv(routes_path)
    except FileNotFoundError as e:
        print(f"Error loading data files: {e}")
        return

    # Extract parameters
    # Nodes and Demands
    # locations.csv: id, net_demand
    nodes = locations_df['id'].tolist()
    demands = dict(zip(locations_df['id'], locations_df['net_demand']))

    # Routes
    # routes.csv: id, source, target
    # We will use route 'id' as the key for variables
    routes = {}
    incoming = {node: [] for node in nodes}
    outgoing = {node: [] for node in nodes}

    for _, row in routes_df.iterrows():
        r_id = int(row['id'])
        u = int(row['source'])
        v = int(row['target'])
        routes[r_id] = (u, v)
        
        if u in outgoing:
            outgoing[u].append(r_id)
        if v in incoming:
            incoming[v].append(r_id)

    # Calculate Big M (Total positive demand)
    M = sum(d for d in demands.values() if d > 0)

    # Initialize Gurobi Model
    model = gp.Model("MinimumEdgeNetworkFlow")

    # Set up logging
    log_file = './logs/log.txt'
    # Ensure spec directory exists (it should, since this script is in it, but good practice)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    model.setParam('LogFile', log_file)

    # Decision Variables
    # x[r_id]: flow on route r_id
    # y[r_id]: binary, 1 if route r_id is used
    x = model.addVars(routes.keys(), vtype=GRB.CONTINUOUS, lb=0, name="x")
    y = model.addVars(routes.keys(), vtype=GRB.BINARY, name="y")

    # Objective: Minimize number of activated routes
    model.setObjective(gp.quicksum(y[r_id] for r_id in routes), GRB.MINIMIZE)

    # Constraints

    # 1. Flow Conservation
    # sum(inflow) - sum(outflow) = demand
    # Note: problem description says "positive values indicate demand".
    # So Inflow - Outflow = Demand
    for i in nodes:
        inflow_sum = gp.quicksum(x[r_id] for r_id in incoming[i])
        outflow_sum = gp.quicksum(x[r_id] for r_id in outgoing[i])
        model.addConstr(inflow_sum - outflow_sum == demands[i], name=f"flow_bal_{i}")

    # 2. Linking Constraints (Big-M)
    # x[r_id] <= M * y[r_id]
    for r_id in routes:
        model.addConstr(x[r_id] <= M * y[r_id], name=f"link_{r_id}")

    # Optimize
    model.optimize()

    # Append results to log file
    with open(log_file, 'a') as f:
        f.write("\n" + "="*50 + "\n")
        f.write("Optimization Results Summary\n")
        f.write("="*50 + "\n")
        
        if model.status == GRB.OPTIMAL:
            f.write(f"Optimal Objective Value (Min Routes): {model.objVal}\n")
            f.write("\nSelected Routes:\n")
            f.write(f"{'Route ID':<10} {'Source':<10} {'Target':<10} {'Flow':<15}\n")
            f.write("-" * 45 + "\n")
            
            selected_count = 0
            for r_id, (u, v) in routes.items():
                if y[r_id].x > 0.5:
                    selected_count += 1
                    f.write(f"{r_id:<10} {u:<10} {v:<10} {x[r_id].x:<15.4f}\n")
            
            f.write("-" * 45 + "\n")
            f.write(f"Total Routes Selected: {selected_count}\n")
        else:
            f.write(f"Optimization ended with status: {model.status}\n")
            if model.status == GRB.INFEASIBLE:
                f.write("Model is infeasible.\n")

if __name__ == "__main__":
    solve()
