import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os
import sys

def solve():
    problem_path = "./problem.json"
    
    # Read problem.json
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    # Parse parameters
    capacities = problem_data['parameters']['capacities']
    
    # Parse file paths
    nodes_path = problem_data['files']['nodes']['path']
    links_path = problem_data['files']['links']['path']
    demands_path = problem_data['files']['demands']['path']
    
    # Load data
    try:
        nodes_df = pd.read_csv(nodes_path)
        links_df = pd.read_csv(links_path)
        demands_df = pd.read_csv(demands_path)
    except FileNotFoundError as e:
        print(f"Error loading data files: {e}")
        return
    
    # Create Gurobi model
    model = gp.Model("NetworkDesign")
    
    # Redirect log to file
    log_file = "./logs/log.txt"
    # Ensure spec directory exists (it should, since this script is in it, but log is written there)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    model.setParam('LogFile', log_file)
    
    # Sets
    nodes = set(nodes_df['id'])
    links = links_df.set_index('id').to_dict('index')
    demands = demands_df.to_dict('index')
    
    # Variables
    # x[k, i, j]: flow of demand k on arc (i, j)
    x = {}
    # y[l, m]: binary, 1 if module m is installed on link l
    y = {}
    
    # Create variables
    for l_id, link in links.items():
        i, j = link['source'], link['target']
        # Create y variables for each capacity
        for cap in capacities:
            y[l_id, cap] = model.addVar(vtype=GRB.BINARY, name=f"y_{l_id}_{cap}")
            
        # Create x variables for each demand on both directions of the link
        for k_id in demands:
            x[k_id, i, j] = model.addVar(vtype=GRB.CONTINUOUS, name=f"x_{k_id}_{i}_{j}")
            x[k_id, j, i] = model.addVar(vtype=GRB.CONTINUOUS, name=f"x_{k_id}_{j}_{i}")
            
    model.update()
    
    # Objective
    obj = 0
    # Installation costs
    for l_id, link in links.items():
        for cap in capacities:
            # Construct column name for fixed cost
            # Capacities in json are floats, but csv headers use int format for whole numbers
            if cap == int(cap):
                col_name = f"fixed_cost_{int(cap)}"
            else:
                col_name = f"fixed_cost_{cap}"
            
            if col_name in link:
                obj += link[col_name] * y[l_id, cap]
            else:
                # Fallback or error handling if column name doesn't match expectation
                # Try the float string representation just in case
                col_name_float = f"fixed_cost_{cap}"
                if col_name_float in link:
                    obj += link[col_name_float] * y[l_id, cap]
                else:
                    print(f"Warning: Cost column for capacity {cap} not found in links data.")
            
    # Routing costs
    for k_id in demands:
        for l_id, link in links.items():
            i, j = link['source'], link['target']
            cost = link['routing_cost']
            obj += cost * (x[k_id, i, j] + x[k_id, j, i])
            
    model.setObjective(obj, GRB.MINIMIZE)
    
    # Constraints
    
    # 1. Flow Conservation
    # Pre-compute arcs for easier lookup
    arcs_out = {n: [] for n in nodes}
    arcs_in = {n: [] for n in nodes}
    
    for l_id, link in links.items():
        i, j = link['source'], link['target']
        arcs_out[i].append((i, j))
        arcs_out[j].append((j, i))
        arcs_in[j].append((i, j))
        arcs_in[i].append((j, i))
        
    for k_id, demand in demands.items():
        s, t, h = demand['source'], demand['target'], demand['value']
        for n in nodes:
            flow_out = gp.quicksum(x[k_id, u, v] for u, v in arcs_out[n])
            flow_in = gp.quicksum(x[k_id, u, v] for u, v in arcs_in[n])
            
            if n == s:
                model.addConstr(flow_out - flow_in == h, name=f"flow_{k_id}_{n}")
            elif n == t:
                model.addConstr(flow_out - flow_in == -h, name=f"flow_{k_id}_{n}")
            else:
                model.addConstr(flow_out - flow_in == 0, name=f"flow_{k_id}_{n}")
                
    # 2. Capacity Constraints
    for l_id, link in links.items():
        i, j = link['source'], link['target']
        total_flow = gp.quicksum(x[k_id, i, j] + x[k_id, j, i] for k_id in demands)
        installed_cap = gp.quicksum(cap * y[l_id, cap] for cap in capacities)
        model.addConstr(total_flow <= installed_cap, name=f"cap_{l_id}")
        
    # 3. Module Selection
    for l_id in links:
        model.addConstr(gp.quicksum(y[l_id, cap] for cap in capacities) <= 1, name=f"select_{l_id}")
        
    # Optimize
    model.optimize()
    
    # Append results to log
    with open(log_file, 'a') as f:
        f.write("\n\n--- Solution Details ---\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Optimal Objective Value: {model.objVal}\n\n")
            
            f.write("Selected Modules:\n")
            for l_id, link in links.items():
                for cap in capacities:
                    if y[l_id, cap].X > 0.5:
                        f.write(f"Link {l_id} ({link['source']}--{link['target']}): Capacity {cap}\n")
                        
            f.write("\nTraffic Routing:\n")
            for k_id, demand in demands.items():
                # Only print if there is flow
                has_flow = False
                for l_id, link in links.items():
                    i, j = link['source'], link['target']
                    if x[k_id, i, j].X > 1e-6 or x[k_id, j, i].X > 1e-6:
                        has_flow = True
                        break
                
                if has_flow:
                    f.write(f"Demand {k_id} ({demand['source']} -> {demand['target']}, val={demand['value']}):\n")
                    for l_id, link in links.items():
                        i, j = link['source'], link['target']
                        if x[k_id, i, j].X > 1e-6:
                            f.write(f"  {i} -> {j}: {x[k_id, i, j].X}\n")
                        if x[k_id, j, i].X > 1e-6:
                            f.write(f"  {j} -> {i}: {x[k_id, j, i].X}\n")
        else:
            f.write(f"No optimal solution found. Status code: {model.status}\n")

if __name__ == "__main__":
    solve()
