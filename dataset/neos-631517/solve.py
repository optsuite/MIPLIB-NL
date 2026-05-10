import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os


def solve_optimization_problem():
    # ----------------------------------------------------------------
    # 1. Load Data
    # ----------------------------------------------------------------
    data_dir = 'data'

    print("Loading data...")
    # Read Task-Mode mappings
    # Schema: [Task_ID, Mode_ID]
    df_task_modes = pd.read_csv(os.path.join(data_dir, 'Task_Modes.csv'))

    # Read Global Resource Limits
    # Schema: [Global_Resource_ID, Limit]
    df_global_limits = pd.read_csv(os.path.join(data_dir, 'Global_Resource_Limits.csv'))

    # Read Local Resource Limits
    # Schema: [Local_Resource_ID, Limit]
    df_local_limits = pd.read_csv(os.path.join(data_dir, 'Local_Resource_Limits.csv'))

    # Read Global Consumption Matrix
    # Schema: [Mode_ID, Global_Resource_ID, Amount]
    df_global_consump = pd.read_csv(os.path.join(data_dir, 'Global_Consumption_Matrix.csv'))

    # Read Local Consumption Matrix
    # Schema: [Mode_ID, Local_Resource_ID, Amount]
    df_local_consump = pd.read_csv(os.path.join(data_dir, 'Local_Consumption_Matrix.csv'))

    # ----------------------------------------------------------------
    # 2. Data Preprocessing
    # ----------------------------------------------------------------
    # Get unique sets for indexing
    tasks = df_task_modes['Task_ID'].unique()
    modes = df_task_modes['Mode_ID'].unique()  # All available modes

    # Group modes by task for easier constraint creation (R0001 - R0167)
    task_to_modes = df_task_modes.groupby('Task_ID')['Mode_ID'].apply(list).to_dict()

    # Prepare global consumption lookup: (Mode_ID, Global_Res_ID) -> Amount
    # Using a dictionary for fast lookup O(1)
    global_consump_dict = df_global_consump.set_index(['Mode_ID', 'Global_Resource_ID'])['Amount'].to_dict()

    # Prepare local consumption lookup: (Mode_ID, Local_Res_ID) -> Amount
    local_consump_dict = df_local_consump.set_index(['Mode_ID', 'Local_Resource_ID'])['Amount'].to_dict()

    # ----------------------------------------------------------------
    # 3. Build Model
    # ----------------------------------------------------------------
    print("Building model...")
    model = gp.Model("neos-631517")

    # --- Decision Variables ---

    # x[m]: Binary variable, 1 if Mode m is selected
    x = model.addVars(modes, vtype=GRB.BINARY, name="x")

    # s_global[r]: Slack variable for Global Resource r
    # Constraint logic: Usage - 1000 * s_global <= Limit  --> s_global >= (Usage - Limit)/1000
    # Since we minimize cost, s_global will be as small as possible (0 if not exceeded).
    global_res_ids = df_global_limits['Global_Resource_ID'].values
    s_global = model.addVars(global_res_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="s_global")

    # s_local[r]: Slack variable for Local Resource r
    # Constraint logic: Usage - s_local <= Limit
    local_res_ids = df_local_limits['Local_Resource_ID'].values
    s_local = model.addVars(local_res_ids, lb=0.0, vtype=GRB.CONTINUOUS, name="s_local")

    # --- Constraints ---

    # 1. Task Assignment Constraints: Exactly one mode per task
    # Corresponds to R0001 - R0167 in original problem
    for t in tasks:
        relevant_modes = task_to_modes[t]
        model.addConstr(gp.quicksum(x[m] for m in relevant_modes) == 1.0, name=f"Task_{t}")

    # 2. Global Resource Constraints
    # Formula: sum(Consumption * x) - 1000 * s_global <= Limit
    # Corresponds to R0168 - R0185
    # To optimize building time, we iterate over resources

    # First, invert the consumption map to access by Resource ID
    # This is faster than filtering the dataframe 18 times inside the loop if N is large,
    # but given the problem size, direct filtering or iteration is fine.
    # Let's use the DataFrame structure for clarity.

    # Group global consumption by Resource ID to build sums efficiently
    grp_global = df_global_consump.groupby('Global_Resource_ID')

    for r_id, limit in zip(df_global_limits['Global_Resource_ID'], df_global_limits['Limit']):
        if r_id in grp_global.groups:
            # Get all modes that consume this resource
            group = grp_global.get_group(r_id)

            expr = gp.quicksum(row.Amount * x[row.Mode_ID] for row in group.itertuples(index=False))

            # Constraint: Expr - 1000 * Slack <= Limit
            model.addConstr(expr - 1000.0 * s_global[r_id] <= limit, name=f"Global_Res_{r_id}")
        else:
            # Even if no consumption, the constraint technically exists: 0 <= Limit + 1000*s
            pass

    # 3. Local Resource Constraints
    # Formula: sum(Consumption * x) - 1.0 * s_local <= Limit
    # Corresponds to R0186 - R0351
    grp_local = df_local_consump.groupby('Local_Resource_ID')

    for r_id, limit in zip(df_local_limits['Local_Resource_ID'], df_local_limits['Limit']):
        if r_id in grp_local.groups:
            group = grp_local.get_group(r_id)
            expr = gp.quicksum(row.Amount * x[row.Mode_ID] for row in group.itertuples(index=False))

            # Constraint: Expr - 1.0 * Slack <= Limit
            model.addConstr(expr - 1.0 * s_local[r_id] <= limit, name=f"Local_Res_{r_id}")

    # --- Objective Function ---
    # Minimize: 2000 * sum(s_global) + 10 * sum(s_local)
    obj_expr = 2000.0 * gp.quicksum(s_global) + 10.0 * gp.quicksum(s_local)
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # ----------------------------------------------------------------
    # 4. Solve and Output
    # ----------------------------------------------------------------
    print("Solving...")
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print(f"\nOptimization Successful!")
        print(f"Optimal Objective Value (Total Penalty): {model.objVal}")

        # Determine strict violations (optional, for verification)
        global_violations = sum(1 for v in s_global.values() if v.X > 1e-6)
        local_violations = sum(1 for v in s_local.values() if v.X > 1e-6)

        print(f"Number of Global Resource Violations: {global_violations}")
        print(f"Number of Local Resource Violations: {local_violations}")

        # You can save the solution to a file if needed
        # model.write("solution.sol")

    else:
        print(f"Optimization ended with status {model.status}")


if __name__ == "__main__":
    solve_optimization_problem()