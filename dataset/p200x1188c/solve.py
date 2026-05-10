import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import sys
import os

def solve():
    # 1. Read problem.json
    problem_path = "./problem.json"
    try:
        with open(problem_path, 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {problem_path} not found. Please run this script from the problem directory.")
        sys.exit(1)

    # 2. Get data file paths
    # The paths in problem.json are relative to the problem directory
    nodes_path = problem_data['files']['nodes']['path']
    edges_path = problem_data['files']['edges']['path']

    # 3. Read data
    try:
        nodes_df = pd.read_csv(nodes_path)
        edges_df = pd.read_csv(edges_path)
    except Exception as e:
        print(f"Error reading data files: {e}")
        sys.exit(1)

    # Prepare data structures
    # nodes_df columns: id, value
    # edges_df columns: id_edge, source_node, target_node, cost
    
    nodes = nodes_df.set_index('id')['value'].to_dict()
    edges = []
    for _, row in edges_df.iterrows():
        edges.append({
            'id': row['id_edge'],
            'u': row['source_node'],
            'v': row['target_node'],
            'cost': row['cost']
        })

    # Calculate Big-M (Total Supply)
    total_supply = sum(v for v in nodes.values() if v > 0)

    # 4. Build Model
    model = gp.Model("OilPipelineNetwork")
    
    # Set up logging to file
    log_file = "./logs/log.txt"
    model.setParam('LogFile', log_file)

    # Variables
    # y[e]: binary, 1 if edge e is built
    # x[e]: continuous, flow on edge e
    y = {}
    x = {}
    
    for e in edges:
        u, v, eid = e['u'], e['v'], e['id']
        y[eid] = model.addVar(vtype=GRB.BINARY, name=f"y_{eid}")
        x[eid] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"x_{eid}")

    # Objective: Minimize construction cost
    model.setObjective(gp.quicksum(e['cost'] * y[e['id']] for e in edges), GRB.MINIMIZE)

    # Constraints
    
    # 1. Flow Conservation
    # sum(flow_out) - sum(flow_in) = net_supply
    # Pre-calculate incident edges for efficiency
    out_edges = {i: [] for i in nodes}
    in_edges = {i: [] for i in nodes}
    
    for e in edges:
        u, v, eid = e['u'], e['v'], e['id']
        if u in out_edges: out_edges[u].append(eid)
        if v in in_edges: in_edges[v].append(eid)
        
    for i, val in nodes.items():
        flow_out = gp.quicksum(x[eid] for eid in out_edges[i])
        flow_in = gp.quicksum(x[eid] for eid in in_edges[i])
        model.addConstr(flow_out - flow_in == val, name=f"flow_bal_{i}")

    # 2. Linking Constraints (Big-M)
    # x[e] <= M * y[e]
    for e in edges:
        eid = e['id']
        model.addConstr(x[eid] <= total_supply * y[eid], name=f"link_{eid}")

    # 5. Solve
    model.optimize()

    # 6. Append results to log file
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n\n--- Solution Summary ---\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Optimal Objective Value (Total Cost): {model.ObjVal}\n")
            f.write("Selected Routes (Edges Constructed):\n")
            selected_edges = []
            for e in edges:
                eid = e['id']
                if y[eid].X > 0.5:
                    flow_val = x[eid].X
                    f.write(f"Edge ID: {eid}, Source: {e['u']}, Target: {e['v']}, Cost: {e['cost']}, Flow: {flow_val}\n")
                    selected_edges.append(str(eid))
            f.write(f"Total edges selected: {len(selected_edges)}\n")
        else:
            f.write(f"No optimal solution found. Status code: {model.status}\n")

if __name__ == "__main__":
    solve()
