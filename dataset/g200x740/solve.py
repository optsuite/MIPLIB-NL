import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve_problem():
    # 1. Read problem.json
    # The script is expected to be run from the problem root directory
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found. Please run the script from the problem root directory.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    # 2. Extract parameters and file paths
    # Paths in problem.json are relative to the problem directory
    nodes_file = problem_data['files']['nodes']['path']
    edges_file = problem_data['files']['edges']['path']
    capacity = problem_data['parameters']['capacity']
    
    # 3. Load data
    nodes_df = pd.read_csv(nodes_file)
    edges_df = pd.read_csv(edges_file)
    
    # 4. Build Gurobi model
    model = gp.Model("SupplyChainNetworkDesign")
    
    # Set log file
    log_path = "./logs/log.txt"
    # Ensure spec directory exists
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    # Clear the log file if it exists to start fresh for Gurobi log
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("Gurobi Optimization Log\n")
        f.write("="*30 + "\n")
    
    model.setParam('LogFile', log_path)
    
    # 5. Variables
    # x[i]: flow on edge at index i
    # y[i]: binary, 1 if edge at index i is activated
    x = model.addVars(edges_df.index, lb=0, name="flow")
    y = model.addVars(edges_df.index, vtype=GRB.BINARY, name="activate")
    
    # 6. Objective
    # Minimize sum(fixed_cost * y + var_cost * x)
    obj = gp.quicksum(edges_df.loc[i, 'fixed_cost'] * y[i] + edges_df.loc[i, 'var_cost'] * x[i] 
                      for i in edges_df.index)
    model.setObjective(obj, GRB.MINIMIZE)
    
    # 7. Constraints
    # Flow balance for each node
    # sum(out) - sum(in) = -net_demand
    node_ids = nodes_df['id'].tolist()
    node_demand = nodes_df.set_index('id')['demand'].to_dict()
    
    # Pre-calculate edges for each node to speed up constraint creation
    out_edges = {node: [] for node in node_ids}
    in_edges = {node: [] for node in node_ids}
    for i, row in edges_df.iterrows():
        out_edges[row['source']].append(i)
        in_edges[row['target']].append(i)
        
    for node in node_ids:
        model.addConstr(
            gp.quicksum(x[i] for i in out_edges[node]) - 
            gp.quicksum(x[i] for i in in_edges[node]) == -node_demand[node],
            name=f"flow_balance_{node}"
        )
        
    # Capacity and activation constraints
    for i in edges_df.index:
        model.addConstr(x[i] <= capacity * y[i], name=f"capacity_{i}")
        
    # 8. Solve
    model.optimize()
    
    # 9. Output results to log.txt
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*30 + "\n")
        f.write("Final Solution Information\n")
        f.write("="*30 + "\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Optimal Objective Value: {model.objVal}\n")
            f.write("Selected Routes:\n")
            f.write(f"{'Edge ID':<10} {'Source':<10} {'Target':<10} {'Flow':<10} {'Fixed Cost':<12} {'Var Cost':<10}\n")
            for i in edges_df.index:
                if y[i].X > 0.5:
                    f.write(f"{edges_df.loc[i, 'id']:<10} {edges_df.loc[i, 'source']:<10} {edges_df.loc[i, 'target']:<10} {x[i].X:<10.2f} {edges_df.loc[i, 'fixed_cost']:<12.2f} {edges_df.loc[i, 'var_cost']:<10.2f}\n")
        else:
            f.write(f"Optimization finished with status: {model.status}\n")
            if model.status == GRB.INFEASIBLE:
                f.write("Model is infeasible. Check constraints and data.\n")

if __name__ == "__main__":
    solve_problem()
