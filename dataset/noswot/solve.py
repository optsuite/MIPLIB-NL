import json
import csv
import os
import sys
import gurobipy as gp
from gurobipy import GRB

def solve():
    # 1. Load Problem Configuration
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # 2. Extract Parameters
    base_dir = os.path.dirname(problem_path)
    params = problem_data.get("parameters", {})
    files = problem_data.get("files", {})
    
    n = params.get("n", 5)
    m = params.get("m", 5)
    global_limit = params.get("global_limit", float('inf'))
    
    # 3. Load Data Files
    # Helper to read CSV
    def read_csv_to_dict(rel_path, key_cols, val_cols):
        path = os.path.join(base_dir, rel_path)
        data = {}
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Create key tuple (int, int) or int
                key = tuple(int(row[k]) for k in key_cols) if len(key_cols) > 1 else int(row[key_cols[0]])
                
                # Extract values
                values = {v: float(row[v]) for v in val_cols}
                data[key] = values
        return data

    # Load Machine Capacities
    # map: machine_id -> limit
    caps_path = files["machine_capacities"]["path"]
    caps_data = read_csv_to_dict(caps_path, ["machine"], ["limit"])
    C = {k: v["limit"] for k, v in caps_data.items()}

    # Load Stage Limits
    # map: stage_id -> {min_limit, max_limit}
    stage_path = files["stage_limits"]["path"]
    stage_data = read_csv_to_dict(stage_path, ["stage"], ["min_limit", "max_limit"])
    S_min = {k: v["min_limit"] for k, v in stage_data.items()}
    S_max = {k: v["max_limit"] for k, v in stage_data.items()}

    # Load Task Parameters
    # map: (machine, stage) -> {fixed_cost, unit_cost, max_qty}
    task_path = files["task_parameters"]["path"]
    task_vals = read_csv_to_dict(task_path, ["machine", "stage"], ["fixed_cost", "unit_cost", "max_qty"])
    
    # 4. Build Model
    model = gp.Model("Noswot")
    
    # Redirect log
    log_file = os.path.join(base_dir, "logs", "log.txt")
    model.setParam("LogFile", log_file)
    model.setParam("LogToConsole", 1)

    # Variables
    # x[i, j]: quantity
    # z[i, j]: binary used
    x = {}
    z = {}
    
    machines = range(1, n + 1)
    stages = range(1, m + 1)
    
    for i in machines:
        for j in stages:
            x[i, j] = model.addVar(vtype=GRB.INTEGER, name=f"x_{i}_{j}")
            z[i, j] = model.addVar(vtype=GRB.BINARY, name=f"z_{i}_{j}")

    # Objective: Maximize total quantity
    model.setObjective(gp.quicksum(x[i, j] for i in machines for j in stages), GRB.MAXIMIZE)

    # Constraints
    
    # 1. Machine Capacity
    for i in machines:
        # Sum of (Fixed * z + Unit * x) <= Capacity[i]
        expr = gp.LinExpr()
        for j in stages:
            if (i, j) in task_vals:
                params_ij = task_vals[i, j]
                expr.add(z[i, j] * params_ij["fixed_cost"])
                expr.add(x[i, j] * params_ij["unit_cost"])
        
        if i in C:
            model.addConstr(expr <= C[i], name=f"Cap_{i}")

    # 2. Task quantity limits and linking
    for i in machines:
        for j in stages:
            if (i, j) in task_vals:
                max_q = int(task_vals[i, j]["max_qty"]) # Integer constraint
                # x <= max_qty * z
                model.addConstr(x[i, j] <= max_q * z[i, j], name=f"Link_{i}_{j}")
            else:
                # If no parameters for this machine/stage, prevent production
                model.addConstr(x[i, j] == 0)
                model.addConstr(z[i, j] == 0)

    # 3. Stage Limits
    for j in stages:
        total_stage_qty = gp.quicksum(x[i, j] for i in machines)
        if j in S_min:
            model.addConstr(total_stage_qty >= S_min[j], name=f"StageMin_{j}")
        if j in S_max:
            model.addConstr(total_stage_qty <= S_max[j], name=f"StageMax_{j}")

    # 4. Global Limit
    total_qty = gp.quicksum(x[i, j] for i in machines for j in stages)
    model.addConstr(total_qty <= global_limit, name="GlobalLimit")

    # 5. Solve
    model.optimize()

    # 6. Output
    if model.Status == GRB.OPTIMAL:
        print(f"Optimal Objective Value: {model.ObjVal}")
        with open(log_file, "a") as f:
            f.write(f"\nOptimization Finished.\nOptimal Objective: {model.ObjVal}\n")
            f.write("Production Plan:\n")
            keys = sorted(x.keys())
            for (i, j) in keys:
                val = x[i, j].X
                if val > 0.5:
                    line = f"Machine {i}, Stage {j}: {val} units\n"
                    print(line.strip())
                    f.write(line)
    else:
        print("No optimal solution found.")
        with open(log_file, "a") as f:
            f.write(f"\nNo optimal solution found. Status: {model.Status}\n")

if __name__ == "__main__":
    solve()
