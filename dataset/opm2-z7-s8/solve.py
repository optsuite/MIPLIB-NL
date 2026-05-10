import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import json
import os

def solve():
    # Configuration
    problem_file = "./problem.json"
    spec_dir = "./spec"
    log_file = os.path.join(spec_dir, "log.txt")
    
    # Ensure spec directory exists
    if not os.path.exists(spec_dir):
        os.makedirs(spec_dir)

    # 1. Read problem configuration
    print(f"Reading problem definition from {problem_file}...")
    with open(problem_file, "r", encoding="utf-8") as f:
        problem_data = json.load(f)
    
    resource_capacity = problem_data["parameters"]["resource_capacity"]
    
    # Resolve data file paths relative to the problem file location
    # Assuming the script is run from the problem root, paths like "./data/..." work directly
    projects_path = problem_data["files"]["projects"]["path"]
    costs_path = problem_data["files"]["resource_costs"]["path"]
    deps_path = problem_data["files"]["dependencies"]["path"]
    
    # 2. Load Data
    print("Loading data files...")
    df_projects = pd.read_csv(projects_path)
    df_costs = pd.read_csv(costs_path)
    df_deps = pd.read_csv(deps_path)
    
    # Projects: dict id -> npv
    # Ensure IDs are integers
    projects = df_projects.set_index("id")["npv"].to_dict()
    
    # 3. Build Gurobi Model
    print("Building model...")
    model = gp.Model("ProjectPortfolioSelection")
    
    # Set Gurobi logging
    model.setParam("LogFile", log_file)
    model.setParam("LogToConsole", 0) # Disable console output to keep it clean, or 1 if user wants to see it. 
                                      # User said "first redirect log to file", implying file is the primary destination.
                                      # I'll enable console too so the user sees progress in terminal.
    model.setParam("LogToConsole", 1)

    # Variables: x[i] = 1 if project i is selected
    x = model.addVars(projects.keys(), vtype=GRB.BINARY, name="x")
    
    # Objective: Maximize total NPV
    model.setObjective(gp.quicksum(projects[i] * x[i] for i in projects), GRB.MAXIMIZE)
    
    # Constraint 1: Resource Capacities
    # Group costs by resource ID
    # This avoids iterating through the entire dataframe for every resource type
    resource_groups = df_costs.groupby("res_id")
    
    for res_id, group in resource_groups:
        model.addConstr(
            gp.quicksum(row.cost * x[row.project_id] for row in group.itertuples(index=False)) <= resource_capacity,
            name=f"Capacity_Res{res_id}"
        )
            
    # Constraint 2: Dependencies
    # If project_id is selected, required_project_id must be selected: x[src] <= x[req]
    for row in df_deps.itertuples(index=False):
        p_id = row.project_id
        req_id = row.required_project_id
        if p_id in x and req_id in x:
            model.addConstr(x[p_id] <= x[req_id], name=f"Dep_{p_id}_{req_id}")
            
    # 4. Optimize
    print("Starting optimization...")
    model.optimize()
    
    # 5. Output results
    additional_log = ""
    if model.Status == GRB.OPTIMAL:
        msg = "Optimization status: OPTIMAL"
        print(msg)
        additional_log += f"\n{msg}\n"
        
        obj_val = model.ObjVal
        msg = f"Objective Value: {obj_val}"
        print(msg)
        additional_log += f"{msg}\n"
        
        selected_projects = [i for i in projects if x[i].X > 0.5]
        # Sorting for deterministic output
        selected_projects.sort()
        
        msg = f"Number of selected projects: {len(selected_projects)}"
        print(msg)
        additional_log += f"{msg}\n"
        
        msg = f"Selected Projects: {selected_projects}"
        print(msg)
        additional_log += f"{msg}\n"
        
    else:
        msg = f"Optimization ended with status {model.Status}"
        print(msg)
        additional_log += f"\n{msg}\n"

    # Append key info to the log file
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(additional_log)
        
if __name__ == "__main__":
    solve()
