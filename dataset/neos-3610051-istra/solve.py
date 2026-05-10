import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os


def solve_optimization_problem():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')

    # Read data
    df_drift = pd.read_csv(os.path.join(data_dir, 'drift_limits.csv'))
    df_interv = pd.read_csv(os.path.join(data_dir, 'intervention_config.csv'))
    df_links = pd.read_csv(os.path.join(data_dir, 'stage_links.csv'))
    df_obj = pd.read_csv(os.path.join(data_dir, 'objective_constants.csv'))
    df_bounds = pd.read_csv(os.path.join(data_dir, 'variable_bounds.csv'))  # <--- Read bounds

    base_offset = float(df_obj['Base_Offset'].iloc[0])
    model = gp.Model("Process_Monitoring_Optimization")

    # --- Create variables (with bounds) ---
    c_vars = {}
    # First create all state variables based on variable_bounds.csv
    for _, row in df_bounds.iterrows():
        var_id = row['Variable_ID']
        lb = row['LowerBound']
        ub = row['UpperBound']
        # Note: if csv contains null or inf, Gurobi defaults to infinite, but data here is usually complete
        c_vars[var_id] = model.addVar(lb=lb, ub=ub, vtype=GRB.CONTINUOUS, name=var_id)

    # Binary variables
    bin_vars_set = set(df_interv['Binary_Variable_ID'].unique())
    b_vars = model.addVars(bin_vars_set, vtype=GRB.BINARY, name="Intervention")

    # --- Add constraints ---
    # 1. Drift constraints
    interventions_map = {}
    for _, row in df_interv.iterrows():
        interventions_map.setdefault(row['Step_ID'], []).append((row['Binary_Variable_ID'], row['Relaxation_Factor']))

    for _, row in df_drift.iterrows():
        step_id = row['Step_ID']
        prev_var, next_var = step_id.split('->')

        # Ensure variables are created (prevent mismatch between bounds file and drift file)
        if prev_var not in c_vars: c_vars[prev_var] = model.addVar(name=prev_var)
        if next_var not in c_vars: c_vars[next_var] = model.addVar(name=next_var)

        relax_expr = 0
        if step_id in interventions_map:
            for bin_name, factor in interventions_map[step_id]:
                relax_expr += factor * b_vars[bin_name]

        if pd.notna(row['Max_Natural_Increase']):
            model.addConstr(c_vars[next_var] - c_vars[prev_var] <= row['Max_Natural_Increase'] + relax_expr)
        if pd.notna(row['Max_Natural_Decrease']):
            model.addConstr(c_vars[prev_var] - c_vars[next_var] <= row['Max_Natural_Decrease'] + relax_expr)

    # 2. Stage linking constraints
    for _, row in df_links.iterrows():
        src, tgt = row['Source_State_ID'], row['Target_State_ID']
        model.addConstr(c_vars[tgt] <= c_vars[src])

    # --- Objective function ---
    model.setObjective(gp.quicksum(b_vars) + base_offset, GRB.MINIMIZE)

    # --- Solve ---
    print("Starting optimization...")
    model.optimize()

    if model.status == GRB.OPTIMAL:
        interventions_count = sum(1 for v in b_vars.values() if v.X > 0.5)
        print("-" * 30)
        print(f"Base Constant (Offset): {base_offset}")
        print(f"Interventions Required: {interventions_count}")
        print(f"Total Objective Value : {model.ObjVal}")
        print("-" * 30)
    else:
        print("No optimal solution found.")


if __name__ == "__main__":
    solve_optimization_problem()