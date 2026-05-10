import json
import os
import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def solve_optimization():
    # 1. Read instance.json configuration
    instance_file = 'instance.json'
    if not os.path.exists(instance_file):
        print(f"Error: File not found {instance_file}")
        return

    with open(instance_file, 'r', encoding='utf-8') as f:
        instance_data = json.load(f)

    print(f"Loading problem instance: {instance_data['id']}...")

    # 2. Load CSV data
    # Assume paths in instance.json are relative (e.g., "data/T1_Variable_Properties.csv")
    def load_table(file_key):
        file_info = instance_data['files'].get(file_key)
        if not file_info:
            return None
        file_path = file_info['path']
        # Compatible with different system path separators
        file_path = file_path.replace('/', os.sep).replace('\\', os.sep)
        if not os.path.exists(file_path):
            print(f"Warning: Data file not found {file_path}")
            return None
        return pd.read_csv(file_path)

    df_vars = load_table('files_1')  # Variable properties
    df_cons_flow = load_table('files_2')  # T2: Flow conservation
    df_cons_link = load_table('files_3')  # T3: Logical linking
    df_cons_agg = load_table('files_4')  # T4: Aggregated capacity
    df_cons_demand = load_table('files_5')  # T5: Fixed demand

    if df_vars is None:
        print("Error: Unable to load variable table (files_1), cannot continue.")
        return

    # 3. Initialize Gurobi model
    model = gp.Model(instance_data['id'])

    # 4. Create decision variables
    print("Creating variables...")
    vars_dict = {}  # For quick lookup of variable objects by ID

    for _, row in df_vars.iterrows():
        v_id = row['Variable_ID']
        v_type_str = row['Type']

        # Determine variable type
        if 'Binary' in v_type_str or 'Integer' in v_type_str:
            v_type = GRB.BINARY
        else:
            v_type = GRB.CONTINUOUS

        # Determine bounds
        lb = row['Lower_Bound'] if pd.notna(row['Lower_Bound']) else 0.0
        ub = row['Upper_Bound'] if pd.notna(row['Upper_Bound']) else GRB.INFINITY

        # Determine objective coefficient
        obj = row['Obj_Coefficient']

        # Add variable
        vars_dict[v_id] = model.addVar(lb=lb, ub=ub, obj=obj, vtype=v_type, name=v_id)

    # Update model to integrate variables
    model.update()

    # 5. Add constraints
    print("Adding constraints...")

    # T2: Flow Conservation constraints
    # Formula: Sum(Coef * Var) = 0
    if df_cons_flow is not None:
        for c_id, group in df_cons_flow.groupby('Constraint_ID'):
            lhs = gp.quicksum(row['Coefficient'] * vars_dict[row['Variable_ID']] for _, row in group.iterrows())
            model.addConstr(lhs == 0, name=c_id)

    # T3: Logical Linking constraints
    # Formula: Flow_Coef * FlowVar + Fac_Coef * FacVar >= 0
    # (Typical structure: -Flow + Capacity * Binary >= 0)
    if df_cons_link is not None:
        for _, row in df_cons_link.iterrows():
            c_id = row['Constraint_ID']
            flow_var = vars_dict[row['Flow_Variable_ID']]
            fac_var = vars_dict[row['Facility_Variable_ID']]

            lhs = row['Flow_Coefficient'] * flow_var + row['Facility_Coefficient'] * fac_var
            model.addConstr(lhs >= 0, name=c_id)

    # T4: Aggregated Capacity constraints
    # Formula: Sum(Coef * Var) >= 0 (Assumed to be standard >= form)
    if df_cons_agg is not None:
        for c_id, group in df_cons_agg.groupby('Constraint_ID'):
            lhs = gp.quicksum(row['Coefficient'] * vars_dict[row['Variable_ID']] for _, row in group.iterrows())
            model.addConstr(lhs >= 0, name=c_id)

    # T5: Fixed Demand constraints
    # Formula: Sum(Coef * Var) = RHS_Value
    if df_cons_demand is not None:
        for c_id, group in df_cons_demand.groupby('Constraint_ID'):
            # The RHS for the same group should be identical, take the first one
            rhs_val = group.iloc[0]['RHS_Value']
            lhs = gp.quicksum(row['Coefficient'] * vars_dict[row['Variable_ID']] for _, row in group.iterrows())
            model.addConstr(lhs == rhs_val, name=c_id)

    # 6. Solve model
    print("Starting optimization...")
    model.optimize()

    # 7. Output results
    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 30)
        print(f"Optimization successful! Optimal objective value (Net Cost): {model.ObjVal:,.4f}")
        print("=" * 30)

        # Optional: Save solution to file
        # model.write("solution.sol")
    else:
        print(f"\nOptimization finished, status code: {model.status}")


if __name__ == "__main__":
    solve_optimization()