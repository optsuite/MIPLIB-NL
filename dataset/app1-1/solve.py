import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import sys

def solve():
    # Load problem.json
    problem_file = "problem.json"
    if not os.path.exists(problem_file):
        print(f"Error: {problem_file} not found.")
        return

    with open(problem_file, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Extract parameters
    n_regions = problem_data['parameters']['n_regions']
    n_suppliers = problem_data['parameters']['n_suppliers_per_region']
    n_kpis = problem_data['parameters']['n_kpis']
    
    bids_path = problem_data['files']['bids']['path']
    targets_path = problem_data['files']['targets']['path']

    # Load data
    if not os.path.exists(bids_path) or not os.path.exists(targets_path):
        print("Error: Data files not found.")
        return

    bids_df = pd.read_csv(bids_path)
    targets_df = pd.read_csv(targets_path)

    # Map department_id to preferred supplier
    pref_supplier = dict(zip(targets_df['department_id'], targets_df['preferred_supplier_id']))
    
    # Prepare Gurobi model
    model = gp.Model("SupplierSelection")
    
    # Set log file
    log_file = os.path.join("logs", "log.txt")
    # Ensure spec directory exists
    os.makedirs("logs", exist_ok=True)
    
    model.Params.LogFile = log_file
    
    # Variables
    # Weights for KPIs
    w = model.addVars(range(1, n_kpis + 1), lb=0.0, ub=1.0, name="w")
    # Binary variables for each region (1 if preferred supplier wins)
    y = model.addVars(pref_supplier.keys(), vtype=GRB.BINARY, name="y")
    
    # Objective: Maximize sum of y
    model.setObjective(y.sum(), GRB.MAXIMIZE)
    
    # Constraint: Sum of weights = 1
    model.addConstr(w.sum() == 1, "WeightSum")
    
    # Big-M calculation
    # Calculate the maximum possible difference in scores to set a safe M
    metric_cols = [f'metric_{k}' for k in range(1, n_kpis + 1)]
    max_score = bids_df[metric_cols].max().max()
    min_score = bids_df[metric_cols].min().min()
    # The maximum difference between any two weighted scores is bounded by max_score - min_score
    M = max_score - min_score + 10.0 
    
    # Constraints for each region
    grouped_bids = bids_df.groupby('department_id')
    
    for dept_id, group in grouped_bids:
        if dept_id not in pref_supplier:
            continue
            
        p_id = pref_supplier[dept_id]
        
        # Get preferred supplier's scores
        p_row = group[group['supplier_id'] == p_id]
        if p_row.empty:
            print(f"Warning: Preferred supplier {p_id} not found in region {dept_id}")
            continue
        
        p_scores = {k: p_row[f'metric_{k}'].values[0] for k in range(1, n_kpis + 1)}
        
        # Iterate over other suppliers
        for _, row in group.iterrows():
            s_id = row['supplier_id']
            if s_id == p_id:
                continue
            
            # Constraint: Score(other) - Score(pref) >= -M(1 - y)
            # Sum(w_k * S_other_k) - Sum(w_k * S_pref_k) >= -M(1 - y)
            # Sum(w_k * (S_other_k - S_pref_k)) >= -M(1 - y)
            
            lhs = gp.LinExpr()
            for k in range(1, n_kpis + 1):
                diff = row[f'metric_{k}'] - p_scores[k]
                lhs.addTerms(diff, w[k])
            
            model.addConstr(lhs >= -M * (1 - y[dept_id]), f"Win_{dept_id}_{s_id}")

    # Solve
    model.optimize()
    
    # Append results to log
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n\n--- Solution Info ---\n")
        if model.Status == GRB.OPTIMAL:
            f.write(f"Objective Value: {model.ObjVal}\n")
            f.write("Weights:\n")
            for k in range(1, n_kpis + 1):
                f.write(f"  w_{k}: {w[k].X}\n")
            
            f.write("\nWinning Regions (Preferred Supplier has lowest score):\n")
            winning_count = 0
            for dept_id in pref_supplier:
                if y[dept_id].X > 0.5:
                    f.write(f"  Region {dept_id} (Preferred Supplier: {pref_supplier[dept_id]})\n")
                    winning_count += 1
            f.write(f"Total Winning Regions: {winning_count}\n")
        else:
            f.write("No optimal solution found.\n")

if __name__ == "__main__":
    solve()
