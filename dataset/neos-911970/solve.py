import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB

# 1. Load Data
with open('instance.json', 'r') as f:
    instance_data = json.load(f)

N1 = instance_data['parameters']['N1']  # Number of Employees (35)
N2 = instance_data['parameters']['N2']  # Number of Shifts (24)

c1_df = pd.read_csv('data/C1.csv')
c2_df = pd.read_csv('data/C2.csv')
c3_df = pd.read_csv('data/C3.csv')

# Prepare data structures (using 0-based indexing for i in 0..N1-1, j in 0..N2-1)
# Workload coefficients w[j][i]
w = {}
for j in range(N2):
    shift_row = c1_df[c1_df['ShiftID'] == j + 1].iloc[0]
    for i in range(N1):
        w[j, i] = shift_row[f'Emp{i + 1}']

# Cost coefficients c[j][i]
c = {}
for j in range(N2):
    shift_row = c2_df[c2_df['ShiftID'] == j + 1].iloc[0]
    for i in range(N1):
        c[j, i] = shift_row[f'Emp{i + 1}']

# Limits W[j], C_limit[j]
W_limit = {}
C_limit = {}
for j in range(N2):
    row = c3_df[c3_df['ShiftID'] == j + 1].iloc[0]
    W_limit[j] = row['MaxWorkload']
    C_limit[j] = row['MaxCost']

# 2. Create Model
model = gp.Model("Personnel_Rostering")

# 3. Create Variables
# x[i, j] = 1 if employee i is assigned to shift j
x = model.addVars(N1, N2, vtype=GRB.BINARY, name="x")

# Slack variables for Workload violation
s_w = model.addVars(N2, vtype=GRB.CONTINUOUS, lb=0.0, name="s_w")

# Slack variables for Cost violation
s_c = model.addVars(N2, vtype=GRB.CONTINUOUS, lb=0.0, name="s_c")

# 4. Set Objective
# Minimize sum of violations
model.setObjective(gp.quicksum(s_w[j] + s_c[j] for j in range(N2)), GRB.MINIMIZE)

# 5. Add Constraints

# Constraint 1: Employee Assignment (Each employee exactly one shift)
for i in range(N1):
    model.addConstr(gp.quicksum(x[i, j] for j in range(N2)) == 1, name=f"Assign_Emp_{i}")

# Constraint 2: Shift Coverage (Each shift at least one employee)
for j in range(N2):
    model.addConstr(gp.quicksum(x[i, j] for i in range(N1)) >= 1, name=f"Cover_Shift_{j}")

# Constraint 3: Workload Soft Constraint
# sum(w_ij * x_ij) <= W_limit_j + s_w_j
for j in range(N2):
    model.addConstr(
        gp.quicksum(w[j, i] * x[i, j] for i in range(N1)) - s_w[j] <= W_limit[j],
        name=f"Workload_Limit_{j}"
    )

# Constraint 4: Cost Soft Constraint
# sum(c_ij * x_ij) <= C_limit_j + s_c_j
for j in range(N2):
    model.addConstr(
        gp.quicksum(c[j, i] * x[i, j] for i in range(N1)) - s_c[j] <= C_limit[j],
        name=f"Cost_Limit_{j}"
    )

# 6. Optimize
model.optimize()

# 7. Output Results
if model.status == GRB.OPTIMAL:
    print(f"Optimal Objective Value: {model.objVal}")

    # Optional: Print assignments
    # print("\nAssignments:")
    # for i in range(N1):
    #     for j in range(N2):
    #         if x[i, j].x > 0.5:
    #             print(f"Employee {i+1} assigned to Shift {j+1}")

    # Optional: Print violations
    total_w_viol = sum(s_w[j].x for j in range(N2))
    total_c_viol = sum(s_c[j].x for j in range(N2))
    print(f"Total Workload Violation: {total_w_viol}")
    print(f"Total Cost Violation: {total_c_viol}")
else:
    print("No optimal solution found.")