import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import json
import os
import ast


def solve_bin_packing():
    # ---------------------------
    # 1. Paths and Configuration
    # ---------------------------
    data_dir = 'data'
    instance_file = 'instance.json'

    # Check if file exists
    if not os.path.exists(instance_file):
        print(f"Error: {instance_file} not found in current directory.")
        return

    weight_path = os.path.join(data_dir, 'weight.csv')
    b1_path = os.path.join(data_dir, 'B1.csv')
    b2_path = os.path.join(data_dir, 'B2.csv')

    # ---------------------------
    # 2. Load Data
    # ---------------------------
    print("Loading data...")

    # Read instance.json to get the target optimal value
    with open(instance_file, 'r', encoding='utf-8') as f:
        instance_data = json.load(f)
        target_optimal = instance_data.get('optimal_value', None)
        print(f"Target Optimal Value from instance: {target_optimal}")

    # Read weights from weight.csv
    # Assuming columns are: Item ID, Weight
    df_weight = pd.read_csv(weight_path)
    # Build dict: item_id (int) -> weight (float)
    # Note: Use directly if item ID is number, process if string
    weights = dict(zip(df_weight['Item Number'], df_weight['Weight']))
    all_items = list(weights.keys())

    # Read B1.csv (Feasibility of items and bins)
    # Each row represents an item, columns represent bins
    df_b1 = pd.read_csv(b1_path)
    allowed_bins = {}  # item_id -> list of allowed bin_ids

    for _, row in df_b1.iterrows():
        # Parse item ID, assuming format like 'X0', 'X1', need to remove 'X'
        item_str = str(row['Item Number'])
        if item_str.startswith('X'):
            item_id = int(item_str[1:])
        else:
            item_id = int(item_str)

        if item_id not in weights:
            continue

        # Iterate over columns to find bins with value 1
        valid_bins = []
        for col in df_b1.columns:
            if col == 'Item Number':
                continue
            # Try converting column name to bin ID
            try:
                bin_id = int(col)
                if row[col] == 1:
                    valid_bins.append(bin_id)
            except ValueError:
                continue
        allowed_bins[item_id] = valid_bins

    # Read B2.csv (Combination requirement constraints)
    # Each row is a requirement containing multiple (item, bin) pairs
    df_b2 = pd.read_csv(b2_path)
    requirements = []

    for _, row in df_b2.iterrows():
        req_pairs = []
        for col in df_b2.columns:
            if col == 'Requirement k':  # Skip ID column
                continue

            val = row[col]
            if pd.isna(val):
                continue

            # Parse string "(item, bin)"
            val_str = str(val).strip()
            if not val_str:
                continue

            try:
                # Use ast.literal_eval to safely parse tuple
                # Assuming format like "(0, 0)"
                pair = ast.literal_eval(val_str)
                if isinstance(pair, tuple) and len(pair) == 2:
                    req_pairs.append(pair)
            except:
                print(f"Warning: Could not parse '{val_str}' in B2")

        if req_pairs:
            requirements.append(req_pairs)

    print(f"Data loaded. {len(weights)} items, {len(requirements)} requirements.")

    # ---------------------------
    # 3. Build Gurobi Model
    # ---------------------------
    m = gp.Model("BinPackingOptim")

    # Variable: x[i, j] = 1 means item i is put into bin j
    x = {}
    for i in all_items:
        if i in allowed_bins:
            for j in allowed_bins[i]:
                x[i, j] = m.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    # Variable: h (standard weight), we need to minimize it
    h = m.addVar(vtype=GRB.CONTINUOUS, name="h")

    # Objective: Minimize h
    m.setObjective(h, GRB.MINIMIZE)

    # Constraint 1: Each item must be placed into exactly one allowed bin
    for i in all_items:
        if i in allowed_bins and allowed_bins[i]:
            m.addConstr(gp.quicksum(x[i, j] for j in allowed_bins[i]) == 1, name=f"assign_item_{i}")
        else:
            print(f"Warning: Item {i} has no allowed bins!")
            # The model might be infeasible unless this item is not involved in any calculation

    # Constraint 2: Each requirement in B2
    # Meaning of requirement: if pair (i, j) is selected, its weight counts, sum <= h
    for k, pairs in enumerate(requirements):
        expr = gp.LinExpr()
        for (i, j) in pairs:
            # Add constraint only if variable x[i, j] exists (i.e., within B1 allowed range)
            if (i, j) in x:
                expr.add(x[i, j] * weights[i])
        m.addConstr(expr <= h, name=f"requirement_{k}")

    # ---------------------------
    # 4. Set solver parameters and solve
    # ---------------------------
    # Set stop condition: once found objective value <= optimal_value in instance
    if target_optimal is not None:
        print(f"Setting BestObjStop to {target_optimal}")
        m.setParam('BestObjStop', target_optimal)

    # Set time limit (optional, e.g., 300 seconds)
    # m.setParam('TimeLimit', 300)

    print("Starting optimization...")
    m.optimize()

    # ---------------------------
    # 5. Output Results
    # ---------------------------
    if m.status == GRB.OPTIMAL:
        print(f"\nOptimal solution found: h = {m.objVal}")
    elif m.status == GRB.USER_OBJ_LIMIT:
        print(f"\nStopped early because solution reached target: h = {m.objVal}")
    elif m.solCount > 0:
        print(f"\nSolution found (not proven optimal): h = {m.objVal}")
    else:
        print("\nNo solution found.")

    # Save specific solution to file if needed
    if m.solCount > 0:
        solution = []
        for (i, j), var in x.items():
            if var.X > 0.5:
                solution.append({'Item': i, 'Bin': j})
        sol_df = pd.DataFrame(solution)
        sol_df.to_csv('solution.csv', index=False)
        print("Solution saved to solution.csv")


if __name__ == "__main__":
    solve_bin_packing()