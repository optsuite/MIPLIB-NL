import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json


def solve_gap_problem():
    # 1. Read data files
    try:
        c1_df = pd.read_csv('data/C1.csv')  # Employee salaries
        c2_df = pd.read_csv('data/C2.csv')  # Contribution matrix
        c3_df = pd.read_csv('data/C3.csv')  # Task thresholds

        # Read json for verification (optional)
        with open('instance.json', 'r', encoding='utf-8') as f:
            meta_info = json.load(f)

        print("Data loaded successfully.")
        print(f"Number of employees: {len(c1_df)}, Number of tasks: {len(c3_df)}")

    except FileNotFoundError as e:
        print(f"Error: File not found - {e}")
        return

    # 2. Initialize Gurobi model
    model = gp.Model("Housekeeping_Staffing_Optimization")

    # 3. Define decision variables
    # x[j] = 1 if employee j is hired, 0 otherwise
    # Variable type is Binary (0/1)
    employees = c1_df['Employee_ID'].tolist()
    x = model.addVars(employees, vtype=GRB.BINARY, name="x")

    # 4. Set objective function
    # Minimize total cost (Minimize Total Salary)
    # Z = sum(Salary_j * x_j)
    salaries = c1_df.set_index('Employee_ID')['Salary'].to_dict()
    model.setObjective(gp.quicksum(salaries[j] * x[j] for j in employees), GRB.MINIMIZE)

    # 5. Add constraints
    # For each task i, the sum of contributions from hired employees must be >= threshold
    # sum(Contribution_ji * x_j) >= Threshold_i

    tasks = c3_df['Task_ID'].tolist()
    thresholds = c3_df.set_index('Task_ID')['Threshold'].to_dict()

    # To speed up constraint building, preprocess C2 table
    # Convert C2 to DataFrame indexed by Employee_ID for easy lookup
    c2_indexed = c2_df.set_index('Employee_ID')

    print("Building constraints...")
    for t_id in tasks:
        task_col_name = f"Task_{t_id}"  # Corresponding column name in C2, e.g., Task_0
        required_threshold = thresholds[t_id]

        # Build linear expression for this task
        # Expression: sum(employee contribution to task * is employee hired)
        lhs_expr = gp.quicksum(c2_indexed.at[emp_id, task_col_name] * x[emp_id] for emp_id in employees)

        # Add constraint: contribution >= threshold
        model.addConstr(lhs_expr >= required_threshold, name=f"Constraint_Task_{t_id}")

    # 6. Solve the model
    print("Starting optimization...")
    model.optimize()

    # 7. Output results
    if model.status == GRB.OPTIMAL:
        print("\n=== Optimal solution found ===")
        print(f"Minimum total cost (Objective Value): {model.ObjVal}")

        # Count hired employees
        hired_count = sum(1 for j in employees if x[j].X > 0.5)
        print(f"Total hired employees: {hired_count}")

        # Uncomment below to see specifically who was hired
        # hired_employees = [j for j in employees if x[j].X > 0.5]
        # print(f"Hired employee IDs: {hired_employees}")

    else:
        print("\nOptimal solution not found. Status code:", model.status)


if __name__ == "__main__":
    solve_gap_problem()