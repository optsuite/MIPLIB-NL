import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import re


def solve():

    print("Reading data files...")
    # Load Data
    try:
        df_costs = pd.read_csv('data/variable_costs.csv')
        df_supply = pd.read_csv('data/supply_caps.csv')
        df_dist = pd.read_csv( 'data/distribution_caps.csv')
        df_lines = pd.read_csv('data/production_lines.csv')
        df_strat = pd.read_csv('data/strategic_contracts.csv')
        df_conv = pd.read_csv('data/conversion_ratios.csv')
    except FileNotFoundError as e:
        print(f"Error: Could not find file {e.filename}.")
        return

    # Initialize Model
    model = gp.Model("Neckar_Solver")

    # -------------------------------------------------------------
    # 1. Create Variables
    # -------------------------------------------------------------
    # We rely on variable_costs.csv to define the universe of variables.
    vars_dict = {}

    # Check if 'Type' column exists, otherwise infer
    has_type = 'Type' in df_costs.columns

    for _, row in df_costs.iterrows():
        var_id = row['Variable_ID']
        cost = row['Unit_Cost_Revenue']

        # Infer type if missing: C0157+ are typically Binary in this problem class
        if has_type:
            vtype = GRB.BINARY if 'Int' in str(row['Type']) or 'Bin' in str(row['Type']) else GRB.CONTINUOUS
        else:
            # Fallback inference based on ID
            # Extract number
            num = int(re.search(r'\d+', var_id).group())
            vtype = GRB.BINARY if num >= 157 else GRB.CONTINUOUS

        # Create variable
        # Objective is to Maximize Profit (or Minimize Negative Profit).
        # Data provides coefficients (e.g. -50). Minimize sum(coeff * var) works.
        vars_dict[var_id] = model.addVar(lb=0.0, obj=cost, vtype=vtype, name=var_id)

    model.update()
    print(f"Created {len(vars_dict)} variables.")

    # -------------------------------------------------------------
    # 2. Supply Constraints
    # -------------------------------------------------------------
    # Logic: 6 Groups.
    # Mapped to first block of continuous vars.
    # Total Supply Vars = 102 (C0001-C0102). Stride = 17.
    df_supply = df_supply.sort_values('Supply_Group_ID')
    for i, row in enumerate(df_supply.itertuples()):
        expr = gp.LinExpr()
        # Group i sums variables [1 + i*17 ... (i+1)*17]
        start_idx = 1 + i * 17
        for k in range(17):
            v_name = f"C{start_idx + k:04d}"
            if v_name in vars_dict:
                expr += vars_dict[v_name]

        model.addConstr(expr <= row.Max_Quantity, name=row.Supply_Group_ID)

    # -------------------------------------------------------------
    # 3. Distribution Constraints
    # -------------------------------------------------------------
    # Logic: 9 Zones.
    # Mapped to Dist Vars (C0103-C0156). Total 54. Stride 9 (interleaved).
    df_dist = df_dist.sort_values('Distribution_Zone_ID')
    for i, row in enumerate(df_dist.itertuples()):
        expr = gp.LinExpr()
        # Zone i sums variables [103+i, 103+i+9, ...]
        for k in range(6):  # 54/9 = 6 items per zone
            idx = 103 + i + (k * 9)
            v_name = f"C{idx:04d}"
            if v_name in vars_dict:
                expr += vars_dict[v_name]

        model.addConstr(expr <= row.Max_Volume, name=row.Distribution_Zone_ID)

    # -------------------------------------------------------------
    # 4. Strategic Contracts (C0157-C0162)
    # -------------------------------------------------------------
    # Logic: Map R0033..R0038 to C0157..C0162
    # Item Groups are standard for this problem ID: [0,1,2], [3,4], ...
    strategic_groups = [
        [0, 1, 2], [3, 4], [5, 6, 7], [8, 9, 10], [11, 12, 13], [14, 15, 16]
    ]

    df_strat = df_strat.sort_values('Contract_ID')
    # Get Strategic Vars (C0157...C0162)
    strat_vars = [f"C{i:04d}" for i in range(157, 163)]

    for k, row in enumerate(df_strat.itertuples()):
        if k >= len(strat_vars): break
        bin_var_name = strat_vars[k]
        if bin_var_name not in vars_dict: continue

        bin_var = vars_dict[bin_var_name]

        # Sum Flows for this contract group
        expr = gp.LinExpr()
        target_items = strategic_groups[k]

        # Sum flow of these items across ALL supply groups
        for item_idx in target_items:
            for g in range(6):  # 6 supply groups
                # Supply Var ID calculation
                s_idx = 1 + g * 17 + item_idx
                s_name = f"C{s_idx:04d}"
                if s_name in vars_dict:
                    expr += vars_dict[s_name]

        model.addConstr(expr <= row.Capacity_Requirement * bin_var, name=row.Contract_ID)

    # Global Limit: Max 4 contracts
    model.addConstr(gp.quicksum(vars_dict[v] for v in strat_vars if v in vars_dict) <= 4, "Global_Strategic_Limit")

    # -------------------------------------------------------------
    # 5. Production Lines (C0163...C0180) - Intelligent Mapping
    # -------------------------------------------------------------
    # We need to map 17 Constraints (Lines) to 18 Variables.
    # We use the Cost to align them.

    prod_vars = sorted([v for v in vars_dict.keys() if 163 <= int(re.search(r'\d+', v).group()) <= 180])
    df_lines = df_lines.sort_values('Line_ID')

    prod_var_idx = 0
    for row in df_lines.itertuples():
        # Find the next variable that matches the cost
        matched_var = None
        while prod_var_idx < len(prod_vars):
            candidate_name = prod_vars[prod_var_idx]
            candidate_var = vars_dict[candidate_name]
            prod_var_idx += 1

            # Check cost match (tolerance for float)
            if abs(candidate_var.Obj - row.Fixed_Cost_Bonus) < 1e-5:
                matched_var = candidate_var
                break
            else:
                # Assuming sequential order, if cost doesn't match, this variable
                # might be the "gap" variable (e.g. C0168). Skip it.
                print(
                    f"Skipping {candidate_name} (Cost {candidate_var.Obj}) - Does not match Line {row.Line_ID} (Cost {row.Fixed_Cost_Bonus})")

        if matched_var:
            # Construct Constraint: Sum(Item k) <= BigM * Binary
            # Line k corresponds to Item k (0..16)
            # We assume df_lines is sorted R0016..R0032 -> Item 0..16
            item_idx = int(re.search(r'\d+', row.Line_ID).group()) - 16  # R0016->0

            expr = gp.LinExpr()
            for g in range(6):
                s_idx = 1 + g * 17 + item_idx
                s_name = f"C{s_idx:04d}"
                if s_name in vars_dict:
                    expr += vars_dict[s_name]

            model.addConstr(expr <= row.Big_M_Capacity * matched_var, name=row.Line_ID)

    # -------------------------------------------------------------
    # 6. Conversion / Flow Balance
    # -------------------------------------------------------------
    # Build a map of Inputs -> Outputs/Yields
    # Group inputs that share the exact same output set

    # Pre-process conversion table
    # We need to group by "Item Type".
    # Observation: C0001, C0018... (Item 0s) all go to C0103, C0106...
    # We can group by Input Item Index (0..16).

    # Extract one representative per item type
    for k in range(17):
        rep_input = f"C{k + 1:04d}"  # C0001, C0002...

        # Find rows for this input
        subset = df_conv[df_conv['Input_Variable_ID'] == rep_input]
        if subset.empty: continue

        yield_val = subset.iloc[0]['Yield_Ratio']
        outputs = subset['Output_Variable_ID'].unique()

        # LHS: Sum of ALL inputs of this type (across all groups)
        lhs = gp.LinExpr()
        for g in range(6):
            s_idx = 1 + g * 17 + k
            s_name = f"C{s_idx:04d}"
            if s_name in vars_dict:
                lhs += yield_val * vars_dict[s_name]

        # RHS: Sum of Outputs
        rhs = gp.LinExpr()
        for out in outputs:
            if out in vars_dict:
                rhs += vars_dict[out]

        model.addConstr(lhs == rhs, name=f"Balance_Item_{k}")

    # -------------------------------------------------------------
    # 7. Solve
    # -------------------------------------------------------------
    print("Solving...")
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 40)
        print(f"Optimal Objective Value: {model.ObjVal}")
        print(f"Total Net Profit: {-model.ObjVal}")
        print("=" * 40)
    else:
        print(f"Solver ended with status {model.status}")


if __name__ == "__main__":
    solve()