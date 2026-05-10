import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os

def solve():
    # Load problem definition
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_def = json.load(f)

    # Extract parameters
    n_cities = problem_def['parameters']['n_cities']
    
    # Get file paths
    distances_path = problem_def['files']['city_distances']['path']
    core_cities_path = problem_def['files']['core_cities']['path']

    # Read data
    # Assuming paths are relative to the problem directory
    if not os.path.exists(distances_path):
        print(f"Error: {distances_path} not found.")
        return
    if not os.path.exists(core_cities_path):
        print(f"Error: {core_cities_path} not found.")
        return

    df_dist = pd.read_csv(distances_path)
    df_core = pd.read_csv(core_cities_path)

    # Prepare data structures
    terminals = set(df_core['city_id'].tolist())
    root = list(terminals)[0]
    num_terminals = len(terminals)
    
    edges = []
    for _, row in df_dist.iterrows():
        u, v, d = int(row['city1']), int(row['city2']), float(row['distance'])
        if u > v:
            u, v = v, u
        edges.append((u, v, d))

    # Create Gurobi Model
    model = gp.Model("SteinerTree")
    
    # Set up logging
    log_file = "./logs/log.txt"
    model.setParam("LogFile", log_file)
    model.setParam("LogToConsole", 1)

    # Variables
    # x[u, v] = 1 if edge {u, v} is in the tree
    x = {}
    # f[u, v] = flow from u to v
    f = {}

    for u, v, d in edges:
        x[u, v] = model.addVar(vtype=GRB.BINARY, name=f"x_{u}_{v}", obj=d)
        # Create directed flow variables for both directions
        f[u, v] = model.addVar(vtype=GRB.CONTINUOUS, name=f"f_{u}_{v}")
        f[v, u] = model.addVar(vtype=GRB.CONTINUOUS, name=f"f_{v}_{u}")

    # Objective is already set via obj argument in addVar for x
    model.modelSense = GRB.MINIMIZE

    # Constraints
    
    # 1. Flow Conservation
    # We need adjacency list to easily sum flows
    adj = {i: [] for i in range(n_cities)}
    for u, v, d in edges:
        adj[u].append(v)
        adj[v].append(u)

    for i in range(n_cities):
        # Net flow: Outflow - Inflow
        # flow_balance = sum(f[i, j] for j in neighbors) - sum(f[j, i] for j in neighbors)
        # But wait, standard conservation is usually Inflow - Outflow = Demand
        # Let's stick to the model.md:
        # Root: Net Outflow = |S| - 1  => Sum(f_root,j) - Sum(f_j,root) = |S| - 1
        # Other Terminals: Net Inflow = 1 => Sum(f_j,t) - Sum(f_t,j) = 1
        # Non-Terminals: Net Flow = 0
        
        expr = gp.LinExpr()
        for neighbor in adj[i]:
            # Outgoing flow f[i, neighbor]
            # Incoming flow f[neighbor, i]
            # Net Outflow = Out - In
            if i < neighbor:
                expr += f[i, neighbor] - f[neighbor, i]
            else:
                expr += f[i, neighbor] - f[neighbor, i]
        
        if i == root:
            model.addConstr(expr == num_terminals - 1, name=f"flow_root_{i}")
        elif i in terminals:
            model.addConstr(expr == -1, name=f"flow_terminal_{i}")
        else:
            model.addConstr(expr == 0, name=f"flow_steiner_{i}")

    # 2. Capacity / Coupling
    # f[u, v] <= (|S| - 1) * x[u, v]
    M = num_terminals - 1
    for u, v, d in edges:
        model.addConstr(f[u, v] <= M * x[u, v], name=f"cap_{u}_{v}")
        model.addConstr(f[v, u] <= M * x[u, v], name=f"cap_{v}_{u}")

    # Optimize
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print(f"Optimal solution found: {model.objVal}")
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    solve()
