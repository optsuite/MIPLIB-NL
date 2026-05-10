import json
import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import os
import sys

def solve():
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Parse parameters
    n_services = problem_data['parameters']['n_services']
    n_racks = problem_data['parameters']['n_racks']
    n_policies = problem_data['parameters']['n_policies']
    min_policies_per_rack = problem_data['parameters']['min_policies_per_rack']
    
    # Parse data file path
    microservices_path = problem_data['files']['microservices']['path']
    # Handle relative path
    if not os.path.isabs(microservices_path):
        microservices_path = os.path.join(os.path.dirname(problem_path), microservices_path)

    if not os.path.exists(microservices_path):
        print(f"Error: {microservices_path} not found.")
        return

    # Read data
    df = pd.read_csv(microservices_path)
    # Group policies by service
    service_policies = df.groupby('service_id')['policy_id'].apply(list).to_dict()
    
    # Ensure all services are in the dict (some might have no policies)
    for i in range(n_services):
        if i not in service_policies:
            service_policies[i] = []

    # Create Model
    model = gp.Model("Decomp2")
    
    # Set LogFile
    log_file = "./logs/log.txt"
    # Ensure spec dir exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    model.setParam('LogFile', log_file)

    # Variables
    x = model.addVars(n_services, n_racks, vtype=GRB.BINARY, name="x") # Service i on Rack j
    u = model.addVars(n_policies, n_racks, vtype=GRB.BINARY, name="u") # Policy k on Rack j
    y = model.addVars(n_racks, vtype=GRB.BINARY, name="y") # Rack j active
    z = model.addVars(n_policies, vtype=GRB.BINARY, name="z") # Policy k penalty

    # Objective
    # Maximize M * sum(y) - sum(z)
    obj = min_policies_per_rack * y.sum() - z.sum()
    model.setObjective(obj, GRB.MAXIMIZE)

    # Constraints
    
    # 1. Service Assignment
    model.addConstrs((x.sum(i, '*') == 1 for i in range(n_services)), name="Assign")

    # 2. Policy Requirement
    # x[i,j] <= u[k,j] for all k in Req(i)
    for i in range(n_services):
        for k in service_policies[i]:
            for j in range(n_racks):
                model.addConstr(x[i, j] <= u[k, j], name=f"Req_{i}_{k}_{j}")

    # 3. Policy Deployment Limits
    # sum_j u[k,j] <= 2
    model.addConstrs((u.sum(k, '*') <= 2 for k in range(n_policies)), name="PolicyLimit")

    # 4. Policy Penalty
    # z[k] >= sum_j u[k,j] - 1
    for k in range(n_policies):
        model.addConstr(z[k] >= u.sum(k, '*') - 1, name=f"Penalty_{k}")

    # 5. Rack Activation
    # u[k,j] <= y[j]
    for j in range(n_racks):
        for k in range(n_policies):
            model.addConstr(u[k, j] <= y[j], name=f"ActivePolicy_{k}_{j}")
            
    # y[j] <= sum_i x[i,j] (Prevent empty active racks)
    for j in range(n_racks):
        model.addConstr(y[j] <= x.sum('*', j), name=f"ActiveService_{j}")

    # 6. Average Policies Constraint
    # sum_j sum_k u[k,j] >= M * sum_j y[j]
    total_policies = gp.quicksum(u[k, j] for k in range(n_policies) for j in range(n_racks))
    total_active_racks = y.sum()
    model.addConstr(total_policies >= min_policies_per_rack * total_active_racks, name="AvgPolicies")

    # Solve
    model.optimize()

    # Write results
    if model.Status == GRB.OPTIMAL:
        with open(log_file, 'a') as f:
            f.write("\n\nSolution Details:\n")
            f.write(f"Objective Value: {model.ObjVal}\n")
            
            f.write("\nRack Assignments for Services:\n")
            for i in range(n_services):
                for j in range(n_racks):
                    if x[i, j].X > 0.5:
                        f.write(f"Service {i}: Rack {j}\n")
                        break
            
            f.write("\nRack Assignments for Policies:\n")
            for k in range(n_policies):
                racks = []
                for j in range(n_racks):
                    if u[k, j].X > 0.5:
                        racks.append(str(j))
                f.write(f"Policy {k}: {', '.join(racks)}\n")
    else:
        with open(log_file, 'a') as f:
            f.write(f"\nNo optimal solution found. Status: {model.Status}\n")

if __name__ == "__main__":
    solve()
