import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import os


def solve_neos17():
    # 1. Set data paths
    # Assume code runs in the root directory containing the neos17 folder
    # If script is inside neos17 folder, adjust to current_dir = os.path.dirname(__file__)
    base_dir = os.path.join(os.path.expanduser("~"), "Desktop", "neos17")
    data_dir = os.path.join(base_dir, "data")

    print(f"Loading data from: {data_dir}")

    # 2. Read CSV files
    try:
        costs_df = pd.read_csv(os.path.join(data_dir, "misclassification_costs.csv"))
        features_df = pd.read_csv(os.path.join(data_dir, "customer_features.csv"))
        labels_df = pd.read_csv(os.path.join(data_dir, "customer_labels.csv"))
        norm_df = pd.read_csv(os.path.join(data_dir, "normalization_rule.csv"))
    except FileNotFoundError as e:
        print(f"Error loading CSV files: {e}")
        return

    # 3. Initialize Gurobi model
    model = gp.Model("neos17_CreditScoring")

    # --- Variable Definitions ---

    # A variables (feature weights): A01 - A25
    A_vars = {}
    for i in range(1, 26):
        var_name = f"A{i:02d}"
        A_vars[var_name] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=var_name)

    # B variable (threshold): B25 (Note: B01-B24 have bounds of 0 in the original problem, so ignored)
    B25 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="B25")

    # D variables (misclassification/slack variables): D0001 - D0485
    # According to neos17 definition: D0001-D0300 are Integer(Binary), D0301-D0485 are Continuous
    D_vars = {}
    for _, row in costs_df.iterrows():
        cust_id = int(row['Customer_ID'])
        var_name = f"D{cust_id:04d}"

        if cust_id <= 300:
            vtype = GRB.BINARY
        else:
            vtype = GRB.CONTINUOUS

        D_vars[cust_id] = model.addVar(lb=0.0, ub=1.0, vtype=vtype, name=var_name)

    model.update()

    # --- Objective Function ---
    # Minimize Sum(Cost_i * D_i)
    obj_expr = gp.LinExpr()
    for _, row in costs_df.iterrows():
        cust_id = int(row['Customer_ID'])
        cost = row['Penalty_Cost']
        obj_expr += cost * D_vars[cust_id]

    model.setObjective(obj_expr, GRB.MINIMIZE)

    # --- Constraints ---

    # 1. Normalization constraint (Normalization Rule)
    # Based on csv: usually Sum(A) + B25 = 1.0
    norm_expr = gp.LinExpr()
    for _, row in norm_df.iterrows():
        var_name = row['Variable']
        coeff = row['Coefficient']

        if var_name in A_vars:
            norm_expr += coeff * A_vars[var_name]
        elif var_name == "B25":
            norm_expr += coeff * B25

    model.addConstr(norm_expr == 1.0, name="EQCONST")

    # 2. Sample classification constraints (OBS Constraints)
    # Group features by customer for efficient construction
    # customer_features.csv: [Customer_ID, Feature_ID]
    cust_feat_map = features_df.groupby('Customer_ID')['Feature_ID'].apply(list).to_dict()

    for _, row in labels_df.iterrows():
        cust_id = int(row['Customer_ID'])
        label = row['Label']  # 1 (Good) or -1 (Bad)

        # Build score expression: Sum(A_j) - B25
        # Here -B25 is based on the original obs constraint where B25 coefficient is -1.0
        score_expr = gp.LinExpr()

        # Add feature A owned by the customer
        if cust_id in cust_feat_map:
            for feat_id in cust_feat_map[cust_id]:
                if feat_id in A_vars:
                    score_expr += 1.0 * A_vars[feat_id]

        # Subtract threshold
        score_expr += -1.0 * B25

        # Add constraint
        # Label 1 (Good): Score + 1.001*D >= 0.001
        # Label -1 (Bad): Score - 1.001*D <= -0.001
        if label == 1:
            model.addConstr(score_expr + 1.001 * D_vars[cust_id] >= 0.001, name=f"OBS{cust_id:04d}")
        elif label == -1:
            model.addConstr(score_expr - 1.001 * D_vars[cust_id] <= -0.001, name=f"OBS{cust_id:04d}")

    # --- Solve ---
    print("\nStarting Optimization...")
    model.optimize()

    # --- Output Results ---
    if model.status == GRB.OPTIMAL:
        print("\nOptimal Solution Found!")
        print(f"Objective Value (Total Cost): {model.objVal:.6f}")

        print("\n--- Key Variable Values ---")
        print(f"Threshold (B25): {B25.x:.4f}")

        print("Active Feature Weights (A > 0):")
        active_feats = []
        for name, var in A_vars.items():
            if var.x > 1e-6:
                active_feats.append((name, var.x))
                print(f"  {name}: {var.x:.4f}")

        if not active_feats:
            print("  (None)")

        # Count number of misclassifications
        misclassified_count = sum(1 for v in D_vars.values() if v.x > 0.5)
        print(f"\nNumber of Misclassified Samples (D > 0.5): {misclassified_count} / {len(costs_df)}")

    else:
        print(f"Optimization ended with status: {model.status}")


if __name__ == "__main__":
    solve_neos17()