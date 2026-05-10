import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve_problem():
    # 1. Read problem.json
    # The script is expected to be run from the problem root directory
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found. Please run this script from the problem root directory.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    # 2. Parse file paths
    # Paths in problem.json are relative to the problem directory
    materials_file = problem_data['files']['materials']['path']
    radiations_file = problem_data['files']['radiations']['path']
    interactions_file = problem_data['files']['interactions']['path']
    
    # 3. Load data
    materials_df = pd.read_csv(materials_file)
    radiations_df = pd.read_csv(radiations_file)
    interactions_df = pd.read_csv(interactions_file)
    
    # 4. Initialize Gurobi model
    model = gp.Model("ShieldingSystem")
    
    # Redirect log to logs/log.txt
    log_file_path = "./logs/log.txt"
    # Ensure spec directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    model.setParam('LogFile', log_file_path)
    
    # 5. Define variables
    # x[i] is the number of layers of material i
    material_ids = materials_df['id'].tolist()
    costs = dict(zip(materials_df['id'], materials_df['cost']))
    
    x = model.addVars(material_ids, vtype=GRB.INTEGER, lb=0, name="x")
    
    # 6. Define objective
    model.setObjective(gp.quicksum(costs[i] * x[i] for i in material_ids), GRB.MINIMIZE)
    
    # 7. Define constraints
    # Group interactions by radiation_id for efficient constraint construction
    interaction_map = interactions_df.groupby('radiation_id')
    
    for _, rad_row in radiations_df.iterrows():
        rad_id = rad_row['id']
        threshold = rad_row['threshold']
        
        if rad_id in interaction_map.groups:
            group = interaction_map.get_group(rad_id)
            # Sum of (attenuation * layers) >= threshold
            model.addConstr(
                gp.quicksum(row['attenuation'] * x[row['material_id']] for _, row in group.iterrows()) >= threshold,
                name=f"rad_{rad_id}"
            )
    
    # 8. Solve
    model.optimize()
    
    # 9. Output results to log.txt
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*30 + "\n")
        f.write("Key Solution Information:\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Total Minimum Cost: {model.objVal:.4f}\n")
            f.write("Selected Material Layers:\n")
            for i in material_ids:
                val = x[i].x
                if val > 0.5:  # Only print materials used
                    material_name = materials_df.loc[materials_df['id'] == i, 'name'].values[0]
                    f.write(f"Material {i} ({material_name}): {int(round(val))} layers\n")
        elif model.status == GRB.INFEASIBLE:
            f.write("The problem is infeasible.\n")
        else:
            f.write(f"Optimization ended with status {model.status}\n")

if __name__ == "__main__":
    solve_problem()
