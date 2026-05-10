import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve_problem(problem_path="instance.json"):
    # 1. Load Problem Data
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    params = problem_data['parameters']
    n_jobs = params['n']
    time_limit = params['time_limit']
    cost_mech = params['cost_mechaniker']
    cost_tech = params['cost_techniker']
    
    # Helper to resolve paths relative to problem.json
    base_dir = os.path.dirname(problem_path)
    def get_path(key):
        return os.path.join(base_dir, problem_data['files'][key]['path'])

    # Load CSVs
    df_durations = pd.read_csv(get_path('durations'))
    df_windows = pd.read_csv(get_path('time_windows'))
    df_precedence = pd.read_csv(get_path('precedence'))
    df_resources = pd.read_csv(get_path('resources'))

    # Process Data
    # Jobs are 1-based in data
    jobs = list(range(1, n_jobs + 1))
    modes = [1, 2, 3]
    
    # Durations: {(job, mode): duration}
    durations = {}
    for _, row in df_durations.iterrows():
        jid = row['job_id']
        for m in modes:
            col = f'duration_{m}'
            if pd.notna(row[col]):
                durations[(jid, m)] = int(row[col])

    # Time Windows: {(job, mode): limit}
    start_limits = {}
    for _, row in df_windows.iterrows():
        start_limits[(row['job_id'], row['mode'])] = int(row['allowed_start_offset_limit'])

    # Precedence: adjacency list
    predecessors = {j: [] for j in jobs}
    for _, row in df_precedence.iterrows():
        predecessors[row['successor_id']].append(row['predecessor_id'])

    # Resources: {job: type}
    job_resources = {}
    for _, row in df_resources.iterrows():
        job_resources[row['job_id']] = row['resource_type']

    # 2. Build Model
    model = gp.Model("ProjectScheduling")
    
    # Set log file
    log_file_path = os.path.join(os.path.dirname(__file__), 'log.txt')
    model.setParam('LogFile', log_file_path)
    
    # Variables
    # x[j, m, t] = 1 if job j starts at time t in mode m
    x = {}
    for j in jobs:
        for m in modes:
            if (j, m) in durations:
                d = durations[(j, m)]
                # Valid start times: 0 to time_limit - d
                # Also check time window constraint: (t % 25) < limit
                limit = start_limits.get((j, m), 25)
                for t in range(time_limit - d + 1):
                    if (t % 25) < limit:
                        x[j, m, t] = model.addVar(vtype=GRB.BINARY, name=f"x_{j}_{m}_{t}")

    n_mech = model.addVar(vtype=GRB.INTEGER, lb=0, name="N_mech")
    n_tech = model.addVar(vtype=GRB.INTEGER, lb=0, name="N_tech")

    # Objective
    model.setObjective(cost_mech * n_mech + cost_tech * n_tech, GRB.MINIMIZE)

    # Constraints
    
    # 1. Job Execution
    for j in jobs:
        model.addConstr(gp.quicksum(x[j, m, t] for m in modes for t in range(time_limit + 1) if (j, m, t) in x) == 1, f"JobExec_{j}")

    # 2. Precedence
    # Start time of j >= Finish time of i
    # S_j = sum(t * x[j,m,t])
    # F_i = sum((t + d) * x[i,m,t])
    for j in jobs:
        for i in predecessors[j]:
            start_j = gp.quicksum(t * x[j, m, t] for m in modes for t in range(time_limit + 1) if (j, m, t) in x)
            finish_i = gp.quicksum((t + durations[(i, m)]) * x[i, m, t] for m in modes for t in range(time_limit + 1) if (i, m, t) in x)
            model.addConstr(start_j >= finish_i, f"Pred_{i}_{j}")

    # 3. Resource Capacity
    # For each time t, sum of resources used <= N_type
    # Job j uses resource at time t if it started at s such that s <= t < s + d
    # i.e., s in [t - d + 1, t]
    
    for t in range(time_limit):
        # Mechanikers
        mech_usage = gp.LinExpr()
        tech_usage = gp.LinExpr()
        
        for j in jobs:
            rtype = job_resources[j]
            for m in modes:
                if (j, m) in durations:
                    d = durations[(j, m)]
                    # Check if job j in mode m could be active at time t
                    # It must have started between t - d + 1 and t
                    for s in range(max(0, t - d + 1), t + 1):
                        if (j, m, s) in x:
                            if rtype == 'Mechaniker':
                                mech_usage += m * x[j, m, s]
                            elif rtype == 'Techniker':
                                tech_usage += m * x[j, m, s]
        
        model.addConstr(mech_usage <= n_mech, f"CapMech_{t}")
        model.addConstr(tech_usage <= n_tech, f"CapTech_{t}")

    # 3. Solve
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print(f"Optimal Objective: {model.objVal}")
        print(f"Mechanikers: {n_mech.x}")
        print(f"Technikers: {n_tech.x}")
        
        # Append solution details to log file
        with open(log_file_path, 'a', encoding='utf-8') as log_f:
            log_f.write("\n\nSolution Details:\n")
            log_f.write(f"Optimal Objective: {model.objVal}\n")
            log_f.write(f"Mechanikers: {int(n_mech.x)}\n")
            log_f.write(f"Technikers: {int(n_tech.x)}\n")
            log_f.write("-" * 60 + "\n")
            log_f.write(f"{'Job ID':<10} {'Mode':<10} {'Start':<10} {'End':<10} {'People':<10}\n")
            log_f.write("-" * 60 + "\n")
            
            # Collect schedule
            schedule = []
            for j in jobs:
                for m in modes:
                    for t in range(time_limit + 1):
                        if (j, m, t) in x and x[j, m, t].x > 0.5:
                            d = durations[(j, m)]
                            schedule.append({
                                'Job ID': j,
                                'Mode': m,
                                'Start': t,
                                'End': t + d,
                                'People': m # Mode number equals number of people
                            })
            
            # Sort by Start Time then Job ID
            schedule.sort(key=lambda x: (x['Start'], x['Job ID']))
            
            for item in schedule:
                log_f.write(f"{item['Job ID']:<10} {item['Mode']:<10} {item['Start']:<10} {item['End']:<10} {item['People']:<10}\n")
            log_f.write("-" * 60 + "\n")

    else:
        print("No optimal solution found.")
        with open(log_file_path, 'a', encoding='utf-8') as log_f:
            log_f.write("\nNo optimal solution found.\n")

if __name__ == "__main__":
    solve_problem()
