import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os
import sys

def solve_gsvm():
    # Paths
    problem_file = "./problem.json"
    log_file = "./logs/log.txt"
    
    # Ensure spec directory exists for logging
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 1. Read Problem Definition
    try:
        with open(problem_file, 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {problem_file} not found.")
        return

    params = problem_data.get('parameters', {})
    files_config = problem_data.get('files', {})
    
    # Hyperparameters
    c_global = params.get('C_global', 0.3)
    cost_ratio_outlier = params.get('cost_ratio_outlier', 2.0)
    
    # 2. Load Data
    labels_path = files_config['labels']['path']
    expr_path = files_config['expressions']['path']
    
    # Read Labels
    df_labels = pd.read_csv(labels_path)
    # Ensure sorted by id for consistency
    df_labels = df_labels.sort_values('id').reset_index(drop=True)
    
    # Read Expressions (Long format)
    df_expr = pd.read_csv(expr_path)
    
    # Pivot to Wide Format: index=id, columns=gene_id, values=value
    # Assuming gene_id are 1..60
    X_df = df_expr.pivot(index='id', columns='gene_id', values='value').fillna(0.0)
    
    # Align labels with X
    # Intersection of IDs
    common_ids = sorted(list(set(df_labels['id']) & set(X_df.index)))
    
    df_labels = df_labels[df_labels['id'].isin(common_ids)].set_index('id')
    df_labels = df_labels.reindex(common_ids)
    
    X_df = X_df.loc[common_ids]
    
    # Data Structures for Solver
    ids = common_ids
    Y = df_labels['label'].to_dict() # {id: label}
    X = X_df.to_dict('index')      # {id: {gene_id: value}}
    
    # Feature list
    features = list(X_df.columns)
    
    # Calculate Class Weights
    n_pos = sum(1 for y in Y.values() if y == 1)
    n_neg = sum(1 for y in Y.values() if y == -1)
    
    w_pos = c_global / n_pos if n_pos > 0 else 0
    w_neg = c_global / n_neg if n_neg > 0 else 0
    
    weights = {i: (w_pos if Y[i] == 1 else w_neg) for i in ids}
    penalties = {i: cost_ratio_outlier * weights[i] for i in ids}
    
    M = 10000.0 # Big-M Constant
    
    # 3. Build Gurobi Model
    model = gp.Model("RobustSVM")
    
    # Set log file
    model.setParam('LogFile', log_file)
    model.setParam('LogToConsole', 1) 
    
    # Variables
    # u: weights for features (Must allow negative values)
    u = model.addVars(features, lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="u")
    # b: intercept (Must allow negative values)
    b = model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="b")
    # xi: hinge loss (Slack variables are always non-negative)
    # The original formulation had an upper bound of 2.0, adding it for consistency
    xi = model.addVars(ids, lb=0.0, ub=2.0, vtype=GRB.CONTINUOUS, name="xi")
    # z: outlier indicator (1 = outlier)
    z = model.addVars(ids, vtype=GRB.BINARY, name="z")
    # alpha: absolute value of u
    alpha = model.addVars(features, lb=0.0, vtype=GRB.CONTINUOUS, name="alpha")
    
    # Objective
    # Min sum(alpha) + sum(W_i * xi_i + P_i * z_i)
    obj_reg = gp.quicksum(alpha[j] for j in features)
    obj_loss = gp.quicksum(weights[i] * xi[i] + penalties[i] * z[i] for i in ids)
    
    model.setObjective(obj_reg + obj_loss, GRB.MINIMIZE)
    
    # Constraints
    # 1. Abs value constraints: -alpha <= u <= alpha
    for j in features:
        model.addConstr(u[j] <= alpha[j], name=f"abs_upper_{j}")
        model.addConstr(u[j] >= -alpha[j], name=f"abs_lower_{j}")
        
    # 2. Margin constraints with Big-M
    # y_i * (u^T x_i + b) >= 1 - xi_i - M * z_i
    for i in ids:
        # Dot product u^T x_i
        dot_prod = gp.quicksum(u[j] * X[i][j] for j in features)
        model.addConstr(
            Y[i] * (dot_prod + b) >= 1 - xi[i] - M * z[i],
            name=f"margin_{i}"
        )
        
    # 4. Solve
    model.optimize()
    
    # 5. Output Result
    # Append to log file
    with open(log_file, 'a') as f:
        f.write("\n" + "="*50 + "\n")
        f.write("Solution Summary\n")
        f.write("="*50 + "\n")
        
        if model.Status == GRB.OPTIMAL:
            f.write(f"Objective Value: {model.ObjVal:.8f}\n")
            f.write(f"Parameters:\n")
            f.write(f"  n_samples: {len(ids)}\n")
            f.write(f"  n_features: {len(features)}\n")
            f.write(f"  C_global: {c_global}\n")
            f.write(f"  cost_ratio_outlier: {cost_ratio_outlier}\n")
            f.write(f"  w_pos: {w_pos:.6f}\n")
            f.write(f"  w_neg: {w_neg:.6f}\n")
            
            # Identify Outliers
            outlier_ids = []
            for i in ids:
                if z[i].X > 0.5:
                    outlier_ids.append(i)
            
            f.write(f"Outlier Count: {len(outlier_ids)}\n")
            f.write(f"Outlier Sample IDs: {sorted(outlier_ids)}\n")
            
            # Optional: Feature Selection
            selected_features = [j for j in features if abs(u[j].X) > 1e-5]
            f.write(f"Selected Features Count: {len(selected_features)}\n")
            # f.write(f"Selected Features: {selected_features}\n")
            
        else:
            f.write("Optimization was not successful.\n")
            f.write(f"Status Code: {model.Status}\n")

if __name__ == "__main__":
    solve_gsvm()
