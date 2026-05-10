import gurobipy as gp
from gurobipy import GRB
import json
import os
import pandas as pd

def solve():
    problem_path = "./problem.json"
    
    # Read problem.json
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    n = problem_data['parameters']['n']
    
    # Parse data file path
    if 'files' in problem_data and 'network_rules' in problem_data['files']:
        data_file_path = problem_data['files']['network_rules']['path']
    else:
        print("Error: network_rules file path not found in problem.json")
        return

    # Read data
    if not os.path.exists(data_file_path):
        print(f"Error: Data file {data_file_path} not found.")
        return
        
    df = pd.read_csv(data_file_path)
    
    # Create Gurobi model
    model = gp.Model("bnatt500")
    
    # Decision Variables
    # x[i] represents the state of node i (0 or 1)
    # We include index 0 to handle cases where input index is 0 (constant 0)
    x = model.addVars(range(0, n + 1), vtype=GRB.BINARY, name="x")
    
    # Fix x[0] to 0
    model.addConstr(x[0] == 0, name="fix_x0")
    
    # Auxiliary variables z[i, m]
    # z[i, m] = 1 if the input configuration for node i is m, 0 otherwise
    # m ranges from 0 to 7 (binary 000 to 111)
    z = model.addVars(range(1, n + 1), range(8), vtype=GRB.BINARY, name="z")
    
    # Constraints
    for index, row in df.iterrows():
        i = int(row['i'])
        j = int(row['j'])
        k = int(row['k'])
        l = int(row['l'])
        
        # Truth table bits b0...b7
        b = [int(row[f'b{m}']) for m in range(8)]
        
        # 1. Unique configuration constraint: sum(z[i, m]) == 1
        model.addConstr(gp.quicksum(z[i, m] for m in range(8)) == 1, name=f"unique_config_{i}")
        
        # 2. Input consistency constraints
        # Input j (weight 4): active if m in {4, 5, 6, 7}
        model.addConstr(x[j] == gp.quicksum(z[i, m] for m in [4, 5, 6, 7]), name=f"input_j_{i}")
        
        # Input k (weight 2): active if m in {2, 3, 6, 7}
        model.addConstr(x[k] == gp.quicksum(z[i, m] for m in [2, 3, 6, 7]), name=f"input_k_{i}")
        
        # Input l (weight 1): active if m in {1, 3, 5, 7}
        model.addConstr(x[l] == gp.quicksum(z[i, m] for m in [1, 3, 5, 7]), name=f"input_l_{i}")
        
        # 3. Fixed point constraint: x[i] must match the truth table output
        model.addConstr(x[i] == gp.quicksum(b[m] * z[i, m] for m in range(8)), name=f"fixed_point_{i}")

    # Objective: Minimize x1 (arbitrary objective to find a feasible solution)
    model.setObjective(x[1], GRB.MINIMIZE)
    
    # Set Gurobi LogFile to logs/log.txt
    log_path = "./logs/log.txt"
    if os.path.exists(log_path):
        os.remove(log_path)
    model.setParam('LogFile', log_path)

    # Optimize
    model.optimize()
    
    # Append solution to log.txt
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("\n\n" + "="*50 + "\n")
        log_file.write("Solution Details\n")
        log_file.write("="*50 + "\n")
        
        if model.status == GRB.OPTIMAL:
            log_file.write(f"Optimal solution found.\n")
            log_file.write(f"Objective value: {model.objVal}\n")
            
            # Extract solution
            log_file.write("\nKey Variables (Node States):\n")
            for i in range(1, n + 1):
                state = int(x[i].X + 0.5)
                status_str = "On" if state == 1 else "Off"
                log_file.write(f"Node {i}: {state} ({status_str})\n")
        elif model.status == GRB.INFEASIBLE:
            log_file.write("Model is infeasible.\n")
        else:
            log_file.write(f"Optimization ended with status {model.status}\n")

if __name__ == "__main__":
    solve()
