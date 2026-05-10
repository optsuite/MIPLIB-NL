import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os

def solve():
    problem_path = "./problem.json"
    
    # Read problem definition
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_def = json.load(f)
    
    # Extract parameters
    params = problem_def['parameters']
    capacity = params['capacity']
    
    # Paths for data files
    nodes_path = problem_def['files']['nodes']['path']
    edges_path = problem_def['files']['edges']['path']
    
    # Since paths in json might be relative to json location, but we assume CWD is the problem dir
    # we can use them directly if they are structured like "./data/..."
    
    # Read data
    nodes_df = pd.read_csv(nodes_path)
    edges_df = pd.read_csv(edges_path)
    
    # Helper to clean/map IDs if necessary, assuming 1-based index from sample check
    # Nodes: id, demand
    # Edges: source, target, var_cost_fwd, fixed_cost_fwd, var_cost_bwd, fixed_cost_bwd
    
    nodes = nodes_df.set_index('id')['demand'].to_dict()
    
    # Create Gurobi Model
    m = gp.Model("FixedChargeNetworkDesign")
    
    # Setup Log File
    log_file_path = "./logs/log.txt"
    # Ensure spec directory exists (though it should since this script is in it)
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    m.setParam("LogFile", log_file_path)
    
    # Decision Variables
    x = {} # Flow
    y = {} # Binary open/close status
    
    # Build arcs from edges (bi-directional)
    arcs = []
    
    for _, row in edges_df.iterrows():
        u = int(row['source'])
        v = int(row['target'])
        
        # Forward arc (u -> v)
        c_fwd = row['var_cost_fwd']
        f_fwd = row['fixed_cost_fwd']
        
        x[u, v] = m.addVar(lb=0, ub=capacity, obj=c_fwd, vtype=GRB.CONTINUOUS, name=f"x_{u}_{v}")
        y[u, v] = m.addVar(obj=f_fwd, vtype=GRB.BINARY, name=f"y_{u}_{v}")
        arcs.append((u, v))
        
        # Backward arc (v -> u)
        c_bwd = row['var_cost_bwd']
        f_bwd = row['fixed_cost_bwd']
        
        x[v, u] = m.addVar(lb=0, ub=capacity, obj=c_bwd, vtype=GRB.CONTINUOUS, name=f"x_{v}_{u}")
        y[v, u] = m.addVar(obj=f_bwd, vtype=GRB.BINARY, name=f"y_{v}_{u}")
        arcs.append((v, u))
        
    # Constraints
    
    # 1. Flow Conservation
    # sum(flow_in) - sum(flow_out) = demand
    # Input CSV says: "positive for demand, negative for supply"
    # Standard balance eqn: In - Out = Demand
    
    # Organize arcs by node for easier summation
    in_arcs = {i: [] for i in nodes}
    out_arcs = {i: [] for i in nodes}
    
    for u, v in arcs:
        if u in out_arcs: out_arcs[u].append((u,v))
        if v in in_arcs: in_arcs[v].append((u,v))
        
    for i, demand in nodes.items():
        flow_in = gp.quicksum(x[u, v] for u, v in in_arcs[i])
        flow_out = gp.quicksum(x[u, v] for u, v in out_arcs[i])
        m.addConstr(flow_in - flow_out == demand, name=f"balance_{i}")
        
    # 2. Capacity / Linking Constraints
    # x_ij <= Capacity * y_ij
    for u, v in arcs:
        m.addConstr(x[u, v] <= capacity * y[u, v], name=f"cap_{u}_{v}")
        
    # Optimize
    m.optimize()
    
    # Append results to log file
    if m.status in [GRB.OPTIMAL, GRB.SUBOPTIMAL]:
        with open(log_file_path, "a", encoding='utf-8') as log:
            log.write("\nKey Solution Information:\n")
            log.write("Selected Edges (Flow > 0):\n")
            log.write(f"{'Source':<10} {'Target':<10} {'Flow':<15} {'FixedCost':<15} {'VarCost':<15}\n")
            log.write("-" * 65 + "\n")
            
            total_fixed = 0
            total_var = 0
            
            # Re-iterate directly or sorting
            sorted_arcs = sorted(arcs)
            for u, v in sorted_arcs:
                flow_val = x[u, v].X
                is_open = y[u, v].X > 0.5
                
                if flow_val > 1e-6 or is_open: # Filter for display
                    # Retrieve costs again safely or store them differently? 
                    # Simpler to just map back or assume uniqueness.
                    # Since we have (u,v), let's find cost in model obj coefficients to be precise or re-lookup
                    # Re-lookup from input df is safer for reporting
                    
                    # For simplicity, just output what we have.
                    # We know f_cost from obj coeff of y, c_cost from obj coeff of x?
                    # The objective coefficients were set during variable creation.
                    
                    f_cost = y[u,v].Obj
                    c_cost = x[u,v].Obj
                    
                    log.write(f"{u:<10} {v:<10} {flow_val:<15.2f} {f_cost:<15.2f} {c_cost:<15.2f}\n")
                    
            log.write(f"\nObjective Value: {m.ObjVal}\n")
    else:
        with open(log_file_path, "a") as log:
            log.write(f"\nOptimization ended with status {m.status}\n")

if __name__ == "__main__":
    solve()
