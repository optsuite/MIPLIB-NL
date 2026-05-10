import json
import gurobipy as gp
from gurobipy import GRB
import csv
import os

def solve():
    # Load problem parameters
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    n = problem_data['parameters']['n']
    m = problem_data['parameters']['m']
    k = problem_data['parameters']['k']
    c = problem_data['parameters']['c']
    
    # Handle data path relative to the problem directory
    data_path = problem_data['files']['project_teams']['path']
    
    # Load data
    researcher_to_teams = {i: [] for i in range(n)}
    
    if os.path.exists(data_path):
        with open(data_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team_id = int(row['team_id'])
                researcher_id = int(row['researcher_id'])
                if researcher_id < n:
                    researcher_to_teams[researcher_id].append(team_id)
    else:
        print(f"Error: Data file {data_path} not found.")
        return

    # Create model
    model = gp.Model("SecureLabAssignment")
    
    # Variables
    # x[i, l] = 1 if researcher i is in lab l
    x = model.addVars(n, k, vtype=GRB.BINARY, name="x")
    
    # z[j, l] = 1 if team j is assigned to lab l
    z = model.addVars(m, k, vtype=GRB.BINARY, name="z")
    
    # Objective: Maximize assigned researchers
    model.setObjective(gp.quicksum(x[i, l] for i in range(n) for l in range(k)), GRB.MAXIMIZE)
    
    # Constraints
    
    # 1. Each researcher at most one lab
    model.addConstrs((x.sum(i, '*') <= 1 for i in range(n)), name="ResearcherAssignment")
    
    # 2. Lab capacity
    model.addConstrs((x.sum('*', l) <= c for l in range(k)), name="LabCapacity")
    
    # 3. Each team at most one lab
    model.addConstrs((z.sum(j, '*') <= 1 for j in range(m)), name="TeamAssignment")
    
    # 4. Team Cohesion
    # If researcher i is in lab l, then all their teams j must be in lab l
    for i in range(n):
        for l in range(k):
            for team_j in researcher_to_teams[i]:
                model.addConstr(x[i, l] <= z[team_j, l], name=f"Cohesion_{i}_{team_j}_{l}")
                
    # Setup logging
    log_file = os.path.join('logs', 'log.txt')
    # Ensure spec directory exists
    os.makedirs('logs', exist_ok=True)
    
    model.setParam('LogFile', log_file)
    
    # Solve
    model.optimize()
    
    # Append solution to log file
    with open(log_file, 'a') as f:
        f.write("\n\nSolution:\n")
        if model.Status == GRB.OPTIMAL:
            f.write(f"Optimal Objective Value: {model.ObjVal}\n")
            
            # Lab assignments
            lab_assignments = {l: [] for l in range(k)}
            for i in range(n):
                for l in range(k):
                    if x[i, l].X > 0.5:
                        lab_assignments[l].append(i)
            
            for l in range(k):
                f.write(f"Lab {l}: {lab_assignments[l]}\n")
                f.write(f"  Count: {len(lab_assignments[l])}\n")
        else:
            f.write("No optimal solution found.\n")

if __name__ == "__main__":
    solve()
