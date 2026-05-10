import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Load problem definition
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Parse parameters
    n_packages = problem_data['parameters']['n_packages']
    n_tasks = problem_data['parameters']['n_tasks']
    hard_packages_limit = problem_data['parameters']['hard_packages_limit']

    # Determine data file paths
    # The problem.json might have paths relative to the problem root or inconsistent paths.
    # We check if the file exists at the path specified in json, otherwise check ./data/
    
    def get_data_path(json_path_entry):
        path_in_json = json_path_entry['path']
        if os.path.exists(path_in_json):
            return path_in_json
        
        # Try correcting common path issues (e.g. if it says ./file.csv but it is in ./data/file.csv)
        filename = os.path.basename(path_in_json)
        data_dir_path = os.path.join("data", filename)
        if os.path.exists(data_dir_path):
            return data_dir_path
            
        return path_in_json # Return original if neither found, to let pandas fail with clear error

    package_task_path = get_data_path(problem_data['files']['package_task'])
    package_difficulty_path = get_data_path(problem_data['files']['package_difficulty'])

    print(f"Loading data from:\n - {package_task_path}\n - {package_difficulty_path}")

    # Load Data
    # package_task.csv: package_id, task_id
    df_package_task = pd.read_csv(package_task_path)
    
    # package_difficulty.csv: package_id, difficulty
    df_package_difficulty = pd.read_csv(package_difficulty_path)

    # Preprocess Data
    # Create a dictionary mapping task_id to list of package_ids covering it
    # Assuming package_id and task_id are 1-based integers as per description
    
    # Group packages by task for coverage constraints
    task_coverage = df_package_task.groupby('task_id')['package_id'].apply(list).to_dict()

    # Map package difficulties and costs
    # difficulty: 'easy' -> cost 1, 'hard' -> cost 2
    package_costs = {}
    hard_packages = set()
    
    for _, row in df_package_difficulty.iterrows():
        pid = row['package_id']
        diff = row['difficulty']
        if diff == 'easy':
            package_costs[pid] = 1
        elif diff == 'hard':
            package_costs[pid] = 2
            hard_packages.add(pid)
        else:
            # Default or error handling
            package_costs[pid] = 1000 

    # Initialize Gurobi Model
    model = gp.Model("Rail507_CrewScheduling")
    
    # Setup logging
    log_file = "./logs/log.txt"
    model.setParam('LogFile', log_file)
    model.setParam('LogToConsole', 1)

    # Create Variables
    # x[j] = 1 if package j is selected
    x = {}
    # We iterate through all packages defined in difficulty file (1 to n_packages)
    all_packages = df_package_difficulty['package_id'].unique()
    
    for j in all_packages:
        x[j] = model.addVar(vtype=GRB.BINARY, name=f"x_{j}")

    # Set Objective: Minimize total cost
    model.setObjective(gp.quicksum(package_costs[j] * x[j] for j in all_packages), GRB.MINIMIZE)

    # Constraints
    
    # 1. Task Coverage: Each task must be covered by at least one package
    # Tasks are 1 to n_tasks
    for i in range(1, n_tasks + 1):
        if i in task_coverage:
            covering_packages = task_coverage[i]
            model.addConstr(gp.quicksum(x[j] for j in covering_packages) >= 1, name=f"Cover_Task_{i}")
        else:
            print(f"Warning: Task {i} has no covering packages!")

    # 2. Hard Packages Limit
    model.addConstr(gp.quicksum(x[j] for j in hard_packages if j in x) <= hard_packages_limit, name="Hard_Limit")

    # Optimize
    model.optimize()

    # Output result
    if model.status == GRB.OPTIMAL:
        print(f"Optimal Objective Value: {model.ObjVal}")
        # Optional: Save solution to file if needed
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    solve()
