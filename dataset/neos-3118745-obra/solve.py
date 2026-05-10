import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os


def solve_optimization_explicit_R0124():
    print("Reading data files...")

    # 1. Read data
    try:
        df_c1 = pd.read_csv('data/C1.csv')
        df_c2 = pd.read_csv('data/C2.csv', index_col='Task_ID')
        df_c3 = pd.read_csv('data/C3.csv', index_col='Task_ID')
        df_c4 = pd.read_csv('data/C4.csv', index_col='Task_ID')
        df_c5 = pd.read_csv('data/C5.csv')
    except FileNotFoundError as e:
        print(f"Error: File {e.filename} not found. Please ensure all CSV files are in the current directory.")
        return

    tasks = df_c2.index.tolist()
    subcontractors = [int(col) for col in df_c2.columns]

    capacity = df_c1.set_index('Subcontractor_ID')['Capacity'].to_dict()

    profit = {}
    global_usage = {}
    local_usage = {}

    for i in tasks:
        profit[i] = {}
        global_usage[i] = {}
        local_usage[i] = {}
        for j in subcontractors:
            col_name = str(j)
            profit[i][j] = df_c2.loc[i, col_name]
            global_usage[i][j] = df_c3.loc[i, col_name]
            local_usage[i][j] = df_c4.loc[i, col_name]

    # 2. Create model
    model = gp.Model("Construction_Project_Obra_Explicit")

    # 3. Decision variables
    # x[i, j] = 1 if task i is assigned to subcontractor j
    x = model.addVars(tasks, subcontractors, vtype=GRB.BINARY, name="x")

    # --- New: Explicitly define C0001 variable ---
    # C0001 represents "Unrealized Profit"
    C0001 = model.addVar(vtype=GRB.CONTINUOUS, name="C0001")

    # 4. Objective function
    # Original problem is Minimize C0001
    model.setObjective(C0001, GRB.MINIMIZE)

    # 5. Constraints

    # --- New: Explicitly add R0124 constraint ---
    # C0001 + Sum(Profit * x) = 1616.0
    # Note: 1616.0 here is read from the abstract_problem in instance.json, or hardcoded here
    # For generality, we write 1616.0 directly here, but it should actually be read from parameters
    TARGET_REVENUE = 1616.0

    total_profit_expr = gp.quicksum(profit[i][j] * x[i, j] for i in tasks for j in subcontractors)

    model.addConstr(C0001 + total_profit_expr == TARGET_REVENUE, name="R0124_ProfitDefinition")

    # (1) Task assignment constraints
    model.addConstrs(
        (gp.quicksum(x[i, j] for j in subcontractors) <= 1 for i in tasks),
        name="AssignOnce"
    )

    # (2) Global capacity constraints
    model.addConstrs(
        (gp.quicksum(global_usage[i][j] * x[i, j] for i in tasks) <= capacity[j]
         for j in subcontractors),
        name="GlobalCapacity"
    )

    # (3) Regional local resource constraints
    for _, row in df_c5.iterrows():
        zone_id = int(row['Zone_ID'])
        start_task = int(row['Start_Task_ID'])
        end_task = int(row['End_Task_ID'])
        limit = row['Local_Resource_Limit']

        zone_tasks = [t for t in tasks if start_task <= t <= end_task]

        if not zone_tasks: continue

        model.addConstr(
            gp.quicksum(local_usage[i][j] * x[i, j] for i in zone_tasks for j in subcontractors) <= limit,
            name=f"ZoneLimit_{zone_id}"
        )

    # 6. Solve
    model.optimize()

    # 7. Output results
    if model.status == GRB.OPTIMAL:
        print(f"\nOptimal solution found!")
        # The Objective Value here is C0001 (Unrealized Profit)
        print(f"Minimization objective (C0001/Unrealized Profit): {model.objVal}")

        # Calculate actual total profit
        actual_profit = total_profit_expr.getValue()
        print(f"Actual total profit (Calculated): {actual_profit}")
        print(f"Verify R0124: {model.objVal} + {actual_profit} = {model.objVal + actual_profit} (Should be 1616.0)")

        # Export results
        results = []
        for i in tasks:
            for j in subcontractors:
                if x[i, j].x > 0.5:
                    results.append({
                        'Task_ID': i,
                        'Subcontractor': j,
                        'Profit': profit[i][j]
                    })
        pd.DataFrame(results).to_csv('solution_explicit_R0124.csv', index=False)
        print("Results saved to solution_explicit_R0124.csv")


if __name__ == "__main__":
    solve_optimization_explicit_R0124()