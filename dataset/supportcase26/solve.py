import json
import csv
import os
import sys
import gurobipy as gp
from gurobipy import GRB

def solve():
    problem_path = "./problem.json"
    
    # Read problem.json
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        sys.exit(1)
        
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
        
    # Parse parameters
    params = problem_data.get('parameters', {})
    n = params.get('n')
    m = params.get('m')
    p = params.get('p')
    S = params.get('S')
    
    # Parse data file path
    files = problem_data.get('files', {})
    jobs_file_info = files.get('jobs', {})
    jobs_file_path = jobs_file_info.get('path')
    
    if not jobs_file_path:
        print("Error: jobs file path not found in problem.json")
        sys.exit(1)
        
    # Read jobs data
    jobs = []
    if not os.path.exists(jobs_file_path):
        print(f"Error: Data file {jobs_file_path} not found.")
        sys.exit(1)
        
    with open(jobs_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.append({
                'id': int(row['id']),
                'group': int(row['group']),
                'arrival_time': float(row['arrival_time'])
            })
            
    # Verify data size
    if len(jobs) != n:
        print(f"Warning: Number of jobs in file ({len(jobs)}) does not match parameter n ({n}).")
        
    # Group jobs
    groups = {}
    for job in jobs:
        g_id = job['group']
        if g_id not in groups:
            groups[g_id] = []
        groups[g_id].append(job)
        
    # Sort jobs within groups by id (as per problem description)
    for g_id in groups:
        groups[g_id].sort(key=lambda x: x['id'])
        
    # Create Gurobi Model
    model = gp.Model("JobScheduling")
    
    # Set log file
    log_file_path = "./logs/log.txt"
    # Ensure spec directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    model.setParam('LogFile', log_file_path)
    
    # Variables
    # t[j]: start time of job j
    t = {}
    for job in jobs:
        j_id = job['id']
        t[j_id] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"t_{j_id}")
        
    # Binary variables for different group sequencing
    # y[i, j] = 1 if job i precedes job j (for different groups)
    y = {}
    
    # Big-M
    M = 100000.0
    
    # Constraints
    
    # 1. Arrival Time
    for job in jobs:
        j_id = job['id']
        model.addConstr(t[j_id] >= job['arrival_time'], name=f"Arrival_{j_id}")
        
    # 2. Same Group Sequence
    for g_id, group_jobs in groups.items():
        for k in range(1, len(group_jobs)):
            curr_job = group_jobs[k]
            prev_job = group_jobs[k-1]
            # t_curr >= t_prev + p
            model.addConstr(t[curr_job['id']] >= t[prev_job['id']] + p, 
                            name=f"SameGroup_{prev_job['id']}_{curr_job['id']}")
                            
    # 3. Different Group Separation
    # Iterate over all pairs of jobs from different groups
    # To avoid duplicates, we iterate through groups and pairs
    group_ids = list(groups.keys())
    for idx1 in range(len(group_ids)):
        for idx2 in range(idx1 + 1, len(group_ids)):
            g1 = group_ids[idx1]
            g2 = group_ids[idx2]
            
            for job1 in groups[g1]:
                for job2 in groups[g2]:
                    i = job1['id']
                    j = job2['id']
                    
                    # Create binary variable y_ij
                    # y_ij = 1 => i precedes j => t_j >= t_i + S
                    # y_ij = 0 => j precedes i => t_i >= t_j + S
                    y[i, j] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{j}")
                    
                    # Constraints
                    model.addConstr(t[j] >= t[i] + S - M * (1 - y[i, j]), name=f"DiffGroup_1_{i}_{j}")
                    model.addConstr(t[i] >= t[j] + S - M * y[i, j], name=f"DiffGroup_2_{i}_{j}")

    # Objective: Minimize sum of start times
    obj_expr = gp.quicksum(t[j_id] for j_id in t)
    model.setObjective(obj_expr, GRB.MINIMIZE)
    
    # Solve
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        print(f"Optimal Objective Value: {model.objVal}")
        # Optional: Print solution
        # for j_id in sorted(t.keys()):
        #     print(f"Job {j_id}: Start Time = {t[j_id].X}")
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    solve()
