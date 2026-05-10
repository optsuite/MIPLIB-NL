import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Load problem parameters
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Extract parameters
    n = problem_data['parameters']['n']
    # m = problem_data['parameters']['m'] # Not strictly needed if we read distances
    k = problem_data['parameters']['k']
    l_max = problem_data['parameters']['l']
    capacities = problem_data['parameters']['capacity']
    tariffs = problem_data['parameters']['tariff']

    # Load data files
    cities_path = problem_data['files']['cities']['path']
    distances_path = problem_data['files']['distances']['path']

    # Adjust paths to be relative to the current working directory if needed
    # Assuming script is run from the problem directory, paths like "./data/..." are correct.
    
    try:
        cities_df = pd.read_csv(cities_path)
        distances_df = pd.read_csv(distances_path)
    except FileNotFoundError as e:
        print(f"Error loading data files: {e}")
        return

    # Data processing
    # Cities: id -> value (generation)
    # Ensure IDs are 1-based or handle mapping. Problem says 1 to n.
    generation = cities_df.set_index('id')['value'].to_dict()

    # Edges: (id1, id2) -> distance
    edges = []
    dist_map = {}
    for _, row in distances_df.iterrows():
        u, v = int(row['id1']), int(row['id2'])
        d = row['d']
        # Ensure u < v for unique edge key
        if u > v:
            u, v = v, u
        edges.append((u, v))
        dist_map[(u, v)] = d

    # Create Gurobi Model
    model = gp.Model("PowerTransmission")
    
    # Set up logging
    log_file = os.path.join("logs", "log.txt")
    # Ensure spec directory exists
    os.makedirs("logs", exist_ok=True)
    model.setParam("LogFile", log_file)
    model.setParam("LogToConsole", 1)

    # Variables
    # f[u, v]: flow from u to v (can be negative)
    f = {}
    # y[u, v, t]: number of lines of type t on edge (u, v)
    y = {}

    for u, v in edges:
        f[u, v] = model.addVar(lb=-GRB.INFINITY, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name=f"f_{u}_{v}")
        for t in range(k):
            # t is 0-indexed here, corresponding to capacities[t]
            # Types 0 to k-2 are binary (at most 1)
            # Type k-1 is integer (at most l_max)
            if t < k - 1:
                y[u, v, t] = model.addVar(vtype=GRB.BINARY, name=f"y_{u}_{v}_{t}")
            else:
                y[u, v, t] = model.addVar(lb=0, ub=l_max, vtype=GRB.INTEGER, name=f"y_{u}_{v}_{t}")

    # Objective: Minimize total cost
    # Cost = sum over edges (distance * sum over types (tariff * count))
    obj_expr = gp.LinExpr()
    for u, v in edges:
        d = dist_map[(u, v)]
        for t in range(k):
            cost_per_unit = tariffs[t]
            obj_expr += d * cost_per_unit * y[u, v, t]
    
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # Constraints

    # 1. Flow Conservation
    # sum(flow out) - sum(flow in) = generation
    # For edge (u, v) with u < v, f[u, v] is flow u -> v.
    # If we are at node i:
    #   Out neighbors j: if i < j, flow is f[i, j]
    #                    if j < i, flow is -f[j, i] (since f[j, i] is j -> i)
    
    # Build adjacency list for easier constraint construction
    adj = {i: [] for i in range(1, n + 1)}
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)

    for i in range(1, n + 1):
        flow_balance = gp.LinExpr()
        for neighbor in adj[i]:
            if i < neighbor:
                # Edge is (i, neighbor), flow f[i, neighbor] is out of i
                flow_balance += f[i, neighbor]
            else:
                # Edge is (neighbor, i), flow f[neighbor, i] is into i
                flow_balance -= f[neighbor, i]
        
        model.addConstr(flow_balance == generation.get(i, 0), name=f"balance_{i}")

    # 2. Capacity Constraints
    # |f[u, v]| <= sum(capacity[t] * y[u, v, t])
    for u, v in edges:
        total_capacity = gp.LinExpr()
        for t in range(k):
            total_capacity += capacities[t] * y[u, v, t]
        
        model.addConstr(f[u, v] <= total_capacity, name=f"cap_pos_{u}_{v}")
        model.addConstr(-f[u, v] <= total_capacity, name=f"cap_neg_{u}_{v}")

    # Optimize
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print(f"Optimal Objective Value: {model.objVal}")
        # Optional: Save solution to file if needed
    else:
        print("Optimization ended with status:", model.status)

if __name__ == "__main__":
    solve()
