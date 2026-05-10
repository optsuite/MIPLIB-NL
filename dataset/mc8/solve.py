import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve_problem():
    # Path to problem.json
    problem_path = "./problem.json"
    
    # Read problem.json
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    parameters = problem_data['parameters']
    n = parameters['n']
    m = parameters['m']
    capacity = parameters['capacity']
    
    # Read data files
    nodes_df = pd.read_csv(problem_data['files']['nodes']['path'])
    edges_df = pd.read_csv(problem_data['files']['edges']['path'])
    
    # Initialize Gurobi model
    model = gp.Model("Logistics_Optimization")
    
    # Set log file
    log_file_path = "./logs/log.txt"
    # Ensure the directory exists (though it should if we are running from problem root)
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    model.setParam('LogFile', log_file_path)
    
    # Arcs and variables
    # We have two directions for each edge
    arcs = []
    var_costs = {}
    fixed_costs = {}
    
    for _, row in edges_df.iterrows():
        u, v = int(row['source']), int(row['target'])
        # Forward arc
        arcs.append((u, v))
        var_costs[(u, v)] = row['var_cost_fwd']
        fixed_costs[(u, v)] = row['fixed_cost_fwd']
        # Backward arc
        arcs.append((v, u))
        var_costs[(v, u)] = row['var_cost_bwd']
        fixed_costs[(v, u)] = row['fixed_cost_bwd']
    
    # Decision variables
    x = model.addVars(arcs, lb=0, name="flow")
    y = model.addVars(arcs, vtype=GRB.BINARY, name="setup")
    
    # Objective function
    model.setObjective(
        gp.quicksum(fixed_costs[i, j] * y[i, j] + var_costs[i, j] * x[i, j] for i, j in arcs),
        GRB.MINIMIZE
    )
    
    # Constraints
    # 1. Flow conservation
    node_ids = nodes_df['id'].tolist()
    demands = dict(zip(nodes_df['id'], nodes_df['demand']))
    
    for i in node_ids:
        model.addConstr(
            gp.quicksum(x[i, j] for j in node_ids if (i, j) in arcs) -
            gp.quicksum(x[j, i] for j in node_ids if (j, i) in arcs) == -demands[i],
            name=f"flow_conservation_{i}"
        )
    
    # 2. Capacity and linking constraints
    for i, j in arcs:
        model.addConstr(x[i, j] <= capacity * y[i, j], name=f"capacity_{i}_{j}")
    
    # Solve the model
    model.optimize()
    
    # Append key information to log.txt
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*30 + "\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Optimal Total Cost: {model.objVal}\n")
            f.write("Selected Routes:\n")
            for i, j in arcs:
                if y[i, j].X > 0.5:
                    f.write(f"Route {i} -> {j}: Flow = {x[i, j].X}, Fixed Cost = {fixed_costs[i, j]}, Var Cost = {var_costs[i, j]}\n")
        else:
            f.write("No optimal solution found.\n")

if __name__ == "__main__":
    solve_problem()
