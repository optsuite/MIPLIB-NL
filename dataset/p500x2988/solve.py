import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import json
import os

def solve():
    # Load problem parameters
    problem_file = 'problem.json'
    if not os.path.exists(problem_file):
        print(f"Error: {problem_file} not found.")
        return

    with open(problem_file, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Paths
    nodes_path = problem_data['files']['nodes']['path']
    edges_path = problem_data['files']['edges']['path']

    # Read data
    try:
        nodes_df = pd.read_csv(nodes_path)
        edges_df = pd.read_csv(edges_path)
    except FileNotFoundError as e:
        print(f"Error reading data files: {e}")
        return

    # Calculate Big-M (Total Supply)
    # Sum of all positive values in the 'value' column of nodes
    total_supply = nodes_df[nodes_df['value'] > 0]['value'].sum()
    
    # Initialize Model
    m = gp.Model("PipelineNetwork")
    
    # Logging setup
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, 'log.txt')
    
    # Clear previous log file if exists
    if os.path.exists(log_file):
        os.remove(log_file)
        
    m.setParam('LogFile', log_file)
    
    # Variables
    x = {} # Flow variables
    y = {} # Construction binary variables
    
    # Store edge info for easy access later
    edges_info = []
    
    # Create variables
    for _, row in edges_df.iterrows():
        u = row['source_node']
        v = row['target_node']
        fc = row['flow_cost']
        ic = row['fixed_cost']
        eid = row['id_edge']
        
        edges_info.append({
            'id': eid,
            'u': u,
            'v': v,
            'fc': fc,
            'ic': ic
        })
        
        x[eid] = m.addVar(lb=0, name=f"x_{eid}")
        y[eid] = m.addVar(vtype=GRB.BINARY, name=f"y_{eid}")

    m.update()
    
    # Objective Function: Minimize (Flow Cost * Flow) + (Fixed Cost * Binary)
    obj = gp.LinExpr()
    for e in edges_info:
        eid = e['id']
        obj += e['fc'] * x[eid] + e['ic'] * y[eid]
    m.setObjective(obj, GRB.MINIMIZE)
    
    # Constraints
    
    # 1. Flow Conservation
    # Pre-process edge connections
    node_in = {node_id: [] for node_id in nodes_df['id']}
    node_out = {node_id: [] for node_id in nodes_df['id']}
    
    for e in edges_info:
        if e['u'] in node_out:
            node_out[e['u']].append(e['id'])
        if e['v'] in node_in:
            node_in[e['v']].append(e['id'])
        
    node_supply = dict(zip(nodes_df['id'], nodes_df['value']))
    
    for i, supply in node_supply.items():
        expr = gp.LinExpr()
        # Outflow
        for eid in node_out[i]:
            expr += x[eid]
        # Inflow
        for eid in node_in[i]:
            expr -= x[eid]
        
        m.addConstr(expr == supply, name=f"flow_bal_{i}")
        
    # 2. Linking Constraints (Big-M)
    # x_ij <= M * y_ij
    for e in edges_info:
        eid = e['id']
        m.addConstr(x[eid] <= total_supply * y[eid], name=f"link_{eid}")
        
    # Optimize
    m.optimize()
    
    # Append results to log file
    with open(log_file, 'a') as f:
        f.write("\n" + "="*50 + "\n")
        if m.status == GRB.OPTIMAL:
            f.write("Optimization Finished: Optimal Solution Found\n")
            f.write(f"Objective Value: {m.objVal}\n")
            f.write("-" * 30 + "\n")
            f.write("Selected Routes and Flows:\n")
            
            selected_edges = []
            for e in edges_info:
                eid = e['id']
                if y[eid].x > 0.5: # If edge is constructed
                    flow = x[eid].x
                    selected_edges.append((e, flow))
                    f.write(f"Edge ID: {eid}, Route: {e['u']} -> {e['v']}, Flow: {flow:.2f}, Fixed Cost: {e['ic']}, Unit Flow Cost: {e['fc']}\n")
            
            f.write("-" * 30 + "\n")
            f.write(f"Total Edges Constructed: {len(selected_edges)}\n")
        else:
            f.write(f"Optimization Finished: No optimal solution found. Status code: {m.status}\n")

if __name__ == "__main__":
    solve()
