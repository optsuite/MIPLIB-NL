import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os


def solve_optimization():
    # -----------------------------------------------------------
    # 1. Read instance.json configuration
    # -----------------------------------------------------------
    instance_file = 'instance.json'
    if not os.path.exists(instance_file):
        print(f"Error: {instance_file} file not found.")
        return

    print(f"Reading {instance_file} ...")
    with open(instance_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Extract scalar parameters
    params = config['parameters']
    N = int(params['N'])
    M = float(params['M'])

    # Cost parameters
    Cost_P1 = float(params['Cost_P1'])
    Cost_P2 = float(params['Cost_P2'])
    Cost_Base = float(params['Cost_Base'])

    # RHS constraints
    RHS_Res = float(params['RHS_Resource'])
    RHS_Qual = float(params['RHS_Quality'])

    # -----------------------------------------------------------
    # 2. Read CSV data
    # -----------------------------------------------------------
    data_dir = 'data'
    fit_csv = os.path.join(data_dir, 'fitting_constraints_coeffs.csv')
    obj_csv = os.path.join(data_dir, 'objective_function_coeffs.csv')
    glob_csv = os.path.join(data_dir, 'global_constraints_weights.csv')

    print("Reading CSV data files...")
    try:
        df_fit = pd.read_csv(fit_csv)
        df_obj = pd.read_csv(obj_csv)
        df_glob = pd.read_csv(glob_csv)
    except FileNotFoundError as e:
        print(f"Error: Cannot find data file: {e}")
        return

    # -----------------------------------------------------------
    # 3. Build Gurobi model
    # -----------------------------------------------------------
    print("Building optimization model...")
    model = gp.Model("RobustRegression")

    # Enable log output
    model.setParam('OutputFlag', 1)

    # --- Add variables ---
    # Global variables (P1, P2, Base) - Assume non-negative continuous variables
    P1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="P1")
    P2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="P2")
    Base = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="Base")

    # Sample related variables (array variables)
    Error1 = model.addVars(N, lb=0.0, vtype=GRB.CONTINUOUS, name="Error1")
    Error2 = model.addVars(N, lb=0.0, vtype=GRB.CONTINUOUS, name="Error2")
    Aux1 = model.addVars(N, lb=0.0, vtype=GRB.CONTINUOUS, name="Aux1")
    Aux2 = model.addVars(N, lb=0.0, vtype=GRB.CONTINUOUS, name="Aux2")
    Bin = model.addVars(N, vtype=GRB.BINARY, name="Bin")

    model.update()

    # --- Build objective function ---
    # Global part
    obj_expr = Cost_P1 * P1 + Cost_P2 * P2 + Cost_Base * Base

    # Sample part (summation)
    for i in range(N):
        # Fitting error (Cost=1.0)
        obj_expr += Error1[i] + Error2[i]

        # Auxiliary variable and binary variable costs (from objective_function_coeffs.csv)
        # Note: CSV column names must match the file
        obj_expr += df_obj.loc[i, 'Col_Obj_Aux_1'] * Aux1[i]
        obj_expr += df_obj.loc[i, 'Col_Obj_Aux_2'] * Aux2[i]
        obj_expr += df_obj.loc[i, 'Col_Obj_Bin'] * Bin[i]

    model.setObjective(obj_expr, GRB.MINIMIZE)

    # --- Add constraints ---

    # 1. Global aggregation constraints (Global Constraints) - from global_constraints_weights.csv
    # Resource limit
    model.addConstr(
        gp.quicksum(df_glob.loc[i, 'Col_Res_W'] * Bin[i] for i in range(N)) <= RHS_Res,
        name="Global_Resource"
    )
    # Quality limit
    model.addConstr(
        gp.quicksum(df_glob.loc[i, 'Col_Qual_W'] * Bin[i] for i in range(N)) <= RHS_Qual,
        name="Global_Quality"
    )

    # 2. Sample-wise constraints
    for i in range(N):
        # Extract fitting coefficients
        A = df_fit.loc[i, 'Col_A_P2']
        B = df_fit.loc[i, 'Col_B_Aux1']
        C = df_fit.loc[i, 'Col_C_Bin']
        D = df_fit.loc[i, 'Col_D_RHS']

        # (a) Fitting Lower Bound
        # Rule: -A*P1 + A*P2 + Base + Error1 + B*Aux1 - B*Aux2 + C*Bin >= D
        model.addConstr(
            -A * P1 + A * P2 + Base + Error1[i] + B * Aux1[i] - B * Aux2[i] + C * Bin[i] >= D,
            name=f"Fit_LB_{i}"
        )

        # (b) Fitting Upper Bound
        # Rule: A*P1 - A*P2 + Base + Error2 - B*Aux1 + B*Aux2 - C*Bin >= -D
        # Note: Base remains +1 (according to instance.json description)
        model.addConstr(
            A * P1 - A * P2 + Base + Error2[i] - B * Aux1[i] + B * Aux2[i] - C * Bin[i] >= -D,
            name=f"Fit_UB_{i}"
        )

        # (c) Big-M linearization logic (Aux1 corresponds to P1)
        # 1. P1 - Aux1 + M*Bin <= M
        model.addConstr(P1 - Aux1[i] + M * Bin[i] <= M, name=f"BigM_P1_1_{i}")
        # 2. -P1 + Aux1 <= 0
        model.addConstr(-P1 + Aux1[i] <= 0, name=f"BigM_P1_2_{i}")
        # 3. Aux1 - M*Bin <= 0
        model.addConstr(Aux1[i] - M * Bin[i] <= 0, name=f"BigM_P1_3_{i}")

        # (d) Big-M linearization logic (Aux2 corresponds to P2)
        # 1. P2 - Aux2 + M*Bin <= M
        model.addConstr(P2 - Aux2[i] + M * Bin[i] <= M, name=f"BigM_P2_1_{i}")
        # 2. -P2 + Aux2 <= 0
        model.addConstr(-P2 + Aux2[i] <= 0, name=f"BigM_P2_2_{i}")
        # 3. Aux2 - M*Bin <= 0
        model.addConstr(Aux2[i] - M * Bin[i] <= 0, name=f"BigM_P2_3_{i}")

    # -----------------------------------------------------------
    # 4. Solve
    # -----------------------------------------------------------
    print("\nStarting solve...")
    model.optimize()

    # -----------------------------------------------------------
    # 5. Output results
    # -----------------------------------------------------------
    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 40)
        print(f"Optimal Solution Found")
        print(f"Objective Value: {model.objVal:g}")
        print("-" * 40)
        print(f"Global Variables:")
        print(f"  P1   = {P1.x:g}")
        print(f"  P2   = {P2.x:g}")
        print(f"  Base = {Base.x:g}")
        print("-" * 40)

        # Count excluded samples (Bin=1)
        excluded_samples = [i for i in range(N) if Bin[i].x > 0.5]
        print(f"Number of excluded samples: {len(excluded_samples)}")
        print(f"Indices of excluded samples: {excluded_samples}")
        print("=" * 40)
    else:
        print(f"\nSolve finished, status code: {model.status}")
        if model.status == GRB.INFEASIBLE:
            print("Model is Infeasible")
        elif model.status == GRB.UNBOUNDED:
            print("Model is Unbounded")


if __name__ == "__main__":
    solve_optimization()