import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    problem_path = "./problem.json"
    
    # Read problem.json
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    # Extract parameters
    n_packages = problem_data['parameters']['n_packages']
    n_tasks = problem_data['parameters']['n_tasks']
    
    # File paths
    package_task_path = problem_data['files']['package_task']['path']
    package_difficulty_path = problem_data['files']['package_difficulty']['path']
    
    # Read data
    # Assuming paths in problem.json are relative to the current working directory (problem root)
    print(f"Reading data from {package_task_path} and {package_difficulty_path}...")
    df_package_task = pd.read_csv(package_task_path)
    df_package_difficulty = pd.read_csv(package_difficulty_path)
    
    # Process data
    # Create a dictionary for package costs
    # package_id ranges from 1 to n_packages
    package_costs = {}
    for _, row in df_package_difficulty.iterrows():
        pid = row['package_id']
        difficulty = row['difficulty']
        cost = 1 if difficulty == 'easy' else 2
        package_costs[pid] = cost
        
    # Create a mapping from task to packages that cover it
    # task_id ranges from 1 to n_tasks
    task_coverage = {i: [] for i in range(1, n_tasks + 1)}
    for _, row in df_package_task.iterrows():
        pid = row['package_id']
        tid = row['task_id']
        if tid in task_coverage:
            task_coverage[tid].append(pid)
            
    # Create Gurobi Model
    model = gp.Model("CrewScheduling")
    
    # Set log file
    log_file = "./logs/log.txt"
    # Ensure spec directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    model.setParam('LogFile', log_file)
    
    # Create variables
    # x[j] = 1 if package j is selected
    print("Creating variables...")
    x = {}
    for j in range(1, n_packages + 1):
        cost = package_costs.get(j, 2) # Default to high cost if missing
        x[j] = model.addVar(vtype=GRB.BINARY, obj=cost, name=f"x_{j}")
        
    # Update model to integrate variables
    model.update()
    
    # Add constraints
    # Each task must be covered at least once
    print("Adding constraints...")
    for i in range(1, n_tasks + 1):
        if not task_coverage[i]:
            print(f"Warning: Task {i} cannot be covered!")
            continue
            
        model.addConstr(gp.quicksum(x[j] for j in task_coverage[i]) >= 1, name=f"cover_{i}")
        
    # Optimize
    print("Optimizing...")
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        print(f"Optimal objective value: {model.objVal}")
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    solve()
