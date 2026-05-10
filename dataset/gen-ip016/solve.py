import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Read problem.json
    problem_path = "./problem.json"
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    # Get file paths from problem.json
    # The paths in problem.json are relative to the problem directory
    base_dir = os.path.dirname(os.path.abspath(problem_path))
    items_path = os.path.join(base_dir, problem_data['files']['items']['path'])
    constraints_path = os.path.join(base_dir, problem_data['files']['constraints']['path'])
    coefficients_path = os.path.join(base_dir, problem_data['files']['coefficients']['path'])
    
    # Load data
    items_df = pd.read_csv(items_path)
    constraints_df = pd.read_csv(constraints_path)
    coefficients_df = pd.read_csv(coefficients_path)
    
    # Parameters
    n = problem_data['parameters']['n']
    m = problem_data['parameters']['m']
    
    # Create model
    model = gp.Model("InvestmentOptimization")
    
    # Set log file
    log_file_path = "./logs/log.txt"
    # Ensure the spec directory exists (though it should if this script is in it)
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    model.setParam('LogFile', log_file_path)
    
    # Decision Variables: Number of units to invest in each project (integers)
    # x[i] corresponds to project with id i+1
    x = model.addVars(n, vtype=GRB.INTEGER, lb=0, name="x")
    
    # Objective Function: Maximize total expected return
    returns = items_df.set_index('id')['return'].to_dict()
    model.setObjective(gp.quicksum(returns[i+1] * x[i] for i in range(n)), GRB.MAXIMIZE)
    
    # Constraints: Weighted sum of impacts for each risk factor <= threshold
    thresholds = constraints_df.set_index('id')['threshold'].to_dict()
    
    # Group coefficients by constraint_id to build constraints efficiently
    coeffs_grouped = coefficients_df.groupby('constraint_id')
    for cid, group in coeffs_grouped:
        if cid in thresholds:
            model.addConstr(
                gp.quicksum(row['value'] * x[int(row['item_id']) - 1] for _, row in group.iterrows()) <= thresholds[cid],
                name=f"risk_factor_{cid}"
            )
    
    # Solve the model
    model.optimize()
    
    # Append key solution information to the log file
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*30 + "\n")
        f.write("Key Solution Information:\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Status: Optimal\n")
            f.write(f"Maximum Total Expected Return: {model.objVal:.4f}\n")
            f.write("Investment Quantities:\n")
            for i in range(n):
                val = x[i].X
                if val > 1e-6:  # Only print non-zero investments
                    f.write(f"  Project {i+1}: {int(val + 0.5)} units\n")
        elif model.status == GRB.INFEASIBLE:
            f.write("Status: Infeasible\n")
        elif model.status == GRB.UNBOUNDED:
            f.write("Status: Unbounded\n")
        else:
            f.write(f"Status: {model.status}\n")
        f.write("="*30 + "\n")

if __name__ == "__main__":
    solve()
