import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import sys

def solve():
    # 1. Load Problem Configuration
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        sys.exit(1)
        
    with open(problem_path, "r", encoding="utf-8") as f:
        problem_config = json.load(f)
    
    # 2. Parse Parameters
    params = problem_config.get("parameters", {})
    C_global = params.get("C_global", 10000.0)
    M = params.get("M", 100.0)
    cost_ratio_outlier = params.get("cost_ratio_outlier", 2.0)
    
    # Files
    labels_path = problem_config["files"]["labels"]["path"] # "./data/patient_labels.csv"
    expressions_path = problem_config["files"]["expressions"]["path"] # "./data/gene_expressions.csv"
    
    # 3. Load and Preprocess Data
    print("Loading data...")
    df_labels = pd.read_csv(labels_path)
    df_expr = pd.read_csv(expressions_path)
    
    # Pivot expression data to (n_samples x n_features)
    # df_expr columns: id, gene_id, value. We want index=id, columns=gene_id, values=value
    X_df = df_expr.pivot(index="id", columns="gene_id", values="value").fillna(0)
    
    # Align labels with X
    # Ensure indices match
    df_labels = df_labels.set_index("id")
    common_ids = X_df.index.intersection(df_labels.index)
    
    X = X_df.loc[common_ids]
    y = df_labels.loc[common_ids, "label"]
    
    n_samples, n_features = X.shape
    print(f"Data shape: {n_samples} samples, {n_features} features")
    
    # Calculate Class Weights
    y_values = y.values
    pos_mask = (y_values == 1)
    neg_mask = (y_values == -1)
    n_pos = pos_mask.sum()
    n_neg = neg_mask.sum()
    
    C_pos = C_global / n_pos if n_pos > 0 else 0
    C_neg = C_global / n_neg if n_neg > 0 else 0
    
    # Vector of C_i for each sample
    sample_weights = []
    for label in y_values:
        if label == 1:
            sample_weights.append(C_pos)
        else:
            sample_weights.append(C_neg)
            
    # 4. Build Gurobi Model
    model = gp.Model("RobustSVM")
    
    # Logging Setup
    log_file = "./logs/log.txt"
    # Ensure spec dir exists (should exist if we are running this)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    model.setParam("LogFile", log_file)
    model.setParam("LogToConsole", 1)
    
    # Variables
    # u: feature weights (unrestricted)
    u = model.addVars(n_features, lb=-GRB.INFINITY, name="u")
    
    # b: bias (unrestricted)
    b = model.addVar(lb=-GRB.INFINITY, name="b")
    
    # xi: slack variables (non-negative)
    xi = model.addVars(n_samples, lb=0.0, name="xi")
    
    # z: outlier indicators (binary)
    z = model.addVars(n_samples, vtype=GRB.BINARY, name="z")
    
    # v: auxiliary for L1 norm |u|
    v = model.addVars(n_features, lb=0.0, name="v")
    
    # Objective
    # sum(v_j) + sum(C_i * xi_i) + sum(cost_ratio * C_i * z_i)
    obj_reg = gp.quicksum(v[j] for j in range(n_features))
    obj_hinge = gp.quicksum(sample_weights[i] * xi[i] for i in range(n_samples))
    obj_penalty = gp.quicksum(sample_weights[i] * cost_ratio_outlier * z[i] for i in range(n_samples))
    
    model.setObjective(obj_reg + obj_hinge + obj_penalty, GRB.MINIMIZE)
    
    # Constraints
    
    # L1 Norm linearization: -v_j <= u_j <= v_j
    for j in range(n_features):
        model.addConstr(u[j] <= v[j], name=f"abs_upper_{j}")
        model.addConstr(u[j] >= -v[j], name=f"abs_lower_{j}")
        
    # Margin constraints with Big-M
    # y_i * (u' x_i + b) >= 1 - xi_i - M * z_i
    # We can perform matrix multiplication efficiently
    # But since Gurobi python is efficient with quicksum or tupledict, let's iterate.
    # X is dataframe. Convert to numpy for faster access or list of lists
    X_matrix = X.values
    
    for i in range(n_samples):
        # dot product u * x_i
        # expr = sum(u[j]*x_ij)
        # To speed up, we can use LinExpr
        lhs = gp.LinExpr()
        for j in range(n_features):
            val = X_matrix[i, j]
            if val != 0:
                lhs.add(u[j], val)
        lhs.add(b)
        
        # y_i * (u*x + b)
        term = y_values[i] * lhs
        
        # Constraint: term >= 1 - xi[i] - M * z[i]
        # => term + xi[i] + M * z[i] >= 1
        model.addConstr(term + xi[i] + M * z[i] >= 1, name=f"margin_{i}")
        
    # 5. Solve
    print("Starting optimization...")
    model.optimize()
    
    # 6. Output Results
    if model.Status == GRB.OPTIMAL:
        print("Optimal solution found.")
        obj_val = model.ObjVal
        
        # Get outlier indices (where z=1)
        outlier_indices = []
        for i in range(n_samples):
            if z[i].X > 0.5:
                # Use the original ID from dataframe index
                outlier_indices.append(str(common_ids[i]))
        
        # Append info to log
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n--- Solution Info ---\n")
            f.write(f"Parameters: C_global={C_global}, M={M}, ratio={cost_ratio_outlier}\n")
            f.write(f"Data shapes: n_samples={n_samples}, n_features={n_features}\n")
            f.write(f"Objective Value: {obj_val}\n")
            f.write(f"Number of Outliers: {len(outlier_indices)}\n")
            f.write(f"Outlier IDs: {', '.join(outlier_indices)}\n")
            
        print(f"Log written to {log_file}")
    else:
        print(f"Optimization ended with status {model.Status}")
        with open(log_file, "a", encoding="utf-8") as f:
             f.write(f"\nOptimization failed or stopped. Status code: {model.Status}\n")

if __name__ == "__main__":
    solve()
