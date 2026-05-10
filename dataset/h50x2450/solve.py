import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve_problem():
    # 1. Read problem.json
    problem_path = "./problem.json"
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    parameters = problem_data['parameters']
    num_nodes = parameters['num_nodes']
    source_node = parameters['source_node']
    total_supply = parameters['total_supply']
    
    # 2. Read data files
    nodes_file = problem_data['files']['nodes']['path']
    edges_file = problem_data['files']['edges']['path']
    
    df_nodes = pd.read_csv(nodes_file)
    df_edges = pd.read_csv(edges_file)
    
    # 3. Prepare model data
    # Nodes and their supply/demand
    node_values = {row['id']: row['value'] for _, row in df_nodes.iterrows()}
    all_node_ids = list(node_values.keys())
    
    # Edges
    potential_edges = []
    for _, row in df_edges.iterrows():
        u, v = int(row['id1']), int(row['id2'])
        fixed_cost = float(row['fixed_cost'])
        var_cost = float(row['variable_cost'])
        potential_edges.append((u, v, fixed_cost, var_cost))
    
    # 4. Build Gurobi Model
    model = gp.Model("WaterSupplyNetwork")
    
    # Set log file
    log_file_path = "./logs/log.txt"
    # Ensure spec directory exists (though it should if this script is running from there)
    os.makedirs("./spec", exist_ok=True)
    model.setParam('LogFile', log_file_path)
    
    # Variables
    # x[u,v] = 1 if edge {u,v} is built
    x = {}
    # y[u,v] = 1 if flow goes from u to v
    y = {}
    # q[u,v] = quantity of flow from u to v
    q = {}
    
    for u, v, fc, vc in potential_edges:
        x[u, v] = model.addVar(vtype=GRB.BINARY, name=f"x_{u}_{v}", obj=fc)
        
        # Arcs in both directions
        y[u, v] = model.addVar(vtype=GRB.BINARY, name=f"y_{u}_{v}")
        y[v, u] = model.addVar(vtype=GRB.BINARY, name=f"y_{v}_{u}")
        
        q[u, v] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"q_{u}_{v}", obj=vc)
        q[v, u] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"q_{v}_{u}", obj=vc)
        
        # Linking: y_uv + y_vu = x_uv
        model.addConstr(y[u, v] + y[v, u] == x[u, v], name=f"link_x_y_{u}_{v}")
        
        # Capacity: q_uv <= M * y_uv
        M = total_supply
        model.addConstr(q[u, v] <= M * y[u, v], name=f"cap_{u}_{v}")
        model.addConstr(q[v, u] <= M * y[v, u], name=f"cap_{v}_{u}")

    # Flow Balance
    for i in all_node_ids:
        # Outflow - Inflow = value
        outflow = gp.quicksum(q[u, v] for u, v, fc, vc in potential_edges if u == i) + \
                  gp.quicksum(q[v, u] for u, v, fc, vc in potential_edges if v == i)
        inflow = gp.quicksum(q[v, u] for u, v, fc, vc in potential_edges if u == i) + \
                 gp.quicksum(q[u, v] for u, v, fc, vc in potential_edges if v == i)
        
        model.addConstr(outflow - inflow == node_values[i], name=f"flow_bal_{i}")

    # Tree Structure: Each node (except source) has at most one incoming edge
    for i in all_node_ids:
        incoming_arcs = []
        for u, v, fc, vc in potential_edges:
            if v == i:
                incoming_arcs.append(y[u, v])
            if u == i:
                incoming_arcs.append(y[v, u])
        
        if i == source_node:
            model.addConstr(gp.quicksum(incoming_arcs) == 0, name=f"source_no_inflow_{i}")
        else:
            model.addConstr(gp.quicksum(incoming_arcs) <= 1, name=f"at_most_one_in_{i}")

    # 5. Optimize
    model.optimize()
    
    # 6. Output results
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*30 + "\n")
        f.write("Optimization Results:\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Total Cost: {model.objVal}\n")
            f.write("Flow Details:\n")
            for (u, v), var in q.items():
                if var.X > 1e-6:
                    f.write(f"Node {u} -> Node {v}: Flow = {var.X}\n")
            for (v, u), var in q.items(): # This is wrong because q keys are (u,v) and (v,u) already? 
                # Wait, I added q[u,v] and q[v,u] in the loop.
                pass
            # Let's redo the flow printing logic to be clearer
            f.write("\nDetailed Flow Paths:\n")
            # Collect all arcs with flow
            active_flows = []
            for u, v, fc, vc in potential_edges:
                if q[u, v].X > 1e-6:
                    active_flows.append((u, v, q[u, v].X))
                if q[v, u].X > 1e-6:
                    active_flows.append((v, u, q[v, u].X))
            
            for u, v, val in active_flows:
                f.write(f"Node {u} flows to Node {v}, Flow: {val}\n")
                print(f"Node {u} flows to Node {v}, Flow: {val}")
        else:
            f.write("No optimal solution found.\n")
            print("No optimal solution found.")

if __name__ == "__main__":
    solve_problem()
