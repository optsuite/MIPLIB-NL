import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import numpy as np

# Create model
model = gp.Model("transport_timetabling")

# --- Data Reading ---
data_dir = "data/"

print("="*80)
print("READING DATA FILES")
print("="*80)

# 1. Read parameters
df_params = pd.read_csv(f"{data_dir}parameters.csv", header=None)
param_names = df_params.iloc[0].tolist()
param_values = df_params.iloc[1].tolist()
parameters = dict(zip(param_names, param_values))

num_services = int(parameters['num_services'])
num_frequencies = int(parameters['num_frequencies'])
num_constraints = int(parameters['num_constraints'])
freq_coefficient = float(parameters['frequency_coefficient'])

print(f"Parameters loaded:")
print(f"  - Number of services: {num_services}")
print(f"  - Number of frequencies: {num_frequencies}")
print(f"  - Number of constraints: {num_constraints}")
print(f"  - Frequency coefficient: {freq_coefficient}")

# 2. Read services (continuous variables)
df_services = pd.read_csv(f"{data_dir}services.csv")
print(f"\nServices loaded: {len(df_services)} service lines")

# 3. Read frequencies (integer variables)
df_frequencies = pd.read_csv(f"{data_dir}frequencies.csv")
print(f"Frequencies loaded: {len(df_frequencies)} frequency variables")

# 4. Read constraints
df_constraints = pd.read_csv(f"{data_dir}constraints.csv")
print(f"Constraints loaded: {len(df_constraints)} constraints")

# 5. Read service-constraint mapping
df_mapping = pd.read_csv(f"{data_dir}service_constraints.csv")
print(f"Constraint-variable mapping loaded: {len(df_mapping)} relations")

# Configure Gurobi logging
os.makedirs('logs', exist_ok=True)
model.setParam('LogFile', 'logs/solver.log')
model.setParam('OutputFlag', 1)

# --- Create Decision Variables ---
print("\n" + "="*80)
print("CREATING DECISION VARIABLES")
print("="*80)

# Service variables (continuous)
service_vars = {}
for _, row in df_services.iterrows():
    service_id = row['service_id']
    lb = row['lower_bound']
    ub = row['upper_bound']
    service_vars[service_id] = model.addVar(
        lb=lb, ub=ub, vtype=GRB.CONTINUOUS, name=service_id
    )
print(f"Created {len(service_vars)} service variables (continuous)")

# Frequency variables (integer)
freq_vars = {}
for _, row in df_frequencies.iterrows():
    freq_id = row['freq_id']
    lb = row['lower_bound']
    ub = row['upper_bound']
    freq_vars[freq_id] = model.addVar(
        lb=lb, ub=ub, vtype=GRB.INTEGER, name=freq_id
    )
print(f"Created {len(freq_vars)} frequency variables (integer)")

# Combine all variables for easy lookup
all_vars = {**service_vars, **freq_vars}

# --- Create Objective Function ---
print("\n" + "="*80)
print("CREATING OBJECTIVE FUNCTION")
print("="*80)

obj_expr = gp.LinExpr()
obj_count = 0

for _, row in df_services.iterrows():
    service_id = row['service_id']
    cost = row['cost']
    if cost != 0:
        obj_expr += cost * service_vars[service_id]
        obj_count += 1

model.setObjective(obj_expr, GRB.MINIMIZE)
print(f"Objective function: Minimize total cost")
print(f"  - Variables with non-zero cost: {obj_count}")

# --- Create Constraints ---
print("\n" + "="*80)
print("CREATING CONSTRAINTS")
print("="*80)

# Group mapping by constraint
constraint_vars = {}
for _, row in df_mapping.iterrows():
    constr_id = row['constraint_id']
    var_id = row['variable_id']
    coef = row['coefficient']
    
    if constr_id not in constraint_vars:
        constraint_vars[constr_id] = []
    
    constraint_vars[constr_id].append({
        'var': all_vars[var_id],
        'coef': coef
    })

# Create constraints
for _, row in df_constraints.iterrows():
    constr_id = row['constraint_id']
    sense = row['sense']
    rhs = row['rhs']
    
    # Build constraint expression
    expr = gp.LinExpr()
    if constr_id in constraint_vars:
        for item in constraint_vars[constr_id]:
            expr += item['coef'] * item['var']
    
    # Add constraint based on sense
    if sense == '=':
        model.addConstr(expr == rhs, name=constr_id)
    elif sense == '<':
        model.addConstr(expr <= rhs, name=constr_id)
    elif sense == '>':
        model.addConstr(expr >= rhs, name=constr_id)

print(f"Created {len(df_constraints)} constraints")

# --- Solve ---
print("\n" + "="*80)
print("SOLVING MODEL")
print("="*80)

model.optimize()

# --- Extract and Display Results ---
print("\n" + "="*80)
print("SOLUTION RESULTS")
print("="*80)

if model.Status == GRB.OPTIMAL:
    print(f"Optimal solution found!")
    print(f"Optimal objective value: {model.ObjVal:.2f}")
    
    # Save solution summary to file
    with open('logs/solution_summary.txt', 'w') as f:
        f.write("="*80 + "\n")
        f.write("TRANSPORT TIMETABLING SOLUTION SUMMARY\n")
        f.write("="*80 + "\n\n")
        f.write(f"Status: OPTIMAL\n")
        f.write(f"Objective Value: {model.ObjVal:.2f}\n")
        f.write(f"Solution Time: {model.Runtime:.2f} seconds\n")
        f.write(f"MIP Gap: {model.MIPGap:.6f}\n\n")
        
        f.write("="*80 + "\n")
        f.write("SERVICE VARIABLES (Non-zero values)\n")
        f.write("="*80 + "\n")
        f.write(f"{'Service ID':<15} {'Value':<15} {'Cost':<15} {'Total Cost':<15}\n")
        f.write("-"*80 + "\n")
        
        service_data = []
        total_service_cost = 0
        
        for service_id, var in service_vars.items():
            if var.X > 1e-6:
                cost = df_services[df_services['service_id'] == service_id]['cost'].values[0]
                total_cost = var.X * cost
                f.write(f"{service_id:<15} {var.X:<15.2f} {cost:<15.2f} {total_cost:<15.2f}\n")
                service_data.append({
                    'service_id': service_id,
                    'value': var.X,
                    'cost': cost,
                    'total_cost': total_cost
                })
                total_service_cost += total_cost
        
        f.write("\n" + "="*80 + "\n")
        f.write("FREQUENCY VARIABLES (Non-zero values)\n")
        f.write("="*80 + "\n")
        f.write(f"{'Frequency ID':<15} {'Value':<15}\n")
        f.write("-"*80 + "\n")
        
        freq_data = []
        for freq_id, var in freq_vars.items():
            if var.X > 1e-6:
                f.write(f"{freq_id:<15} {var.X:<15.0f}\n")
                freq_data.append({
                    'freq_id': freq_id,
                    'value': int(var.X)
                })
        
        f.write("\n" + "="*80 + "\n")
        f.write("SUMMARY STATISTICS\n")
        f.write("="*80 + "\n")
        f.write(f"Total service cost: {total_service_cost:.2f}\n")
        f.write(f"Active services: {len(service_data)}\n")
        f.write(f"Active frequencies: {len(freq_data)}\n")
    
    print(f"\nSolution summary saved to: logs/solution_summary.txt")
    
    # Save service variables to CSV
    if service_data:
        df_service_solution = pd.DataFrame(service_data)
        df_service_solution.to_csv('logs/service_solution.csv', index=False)
        print(f"Service solution saved to: logs/service_solution.csv")
    
    # Save frequency variables to CSV
    if freq_data:
        df_freq_solution = pd.DataFrame(freq_data)
        df_freq_solution.to_csv('logs/frequency_solution.csv', index=False)
        print(f"Frequency solution saved to: logs/frequency_solution.csv")
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    print(f"Objective value: {model.ObjVal:.2f}")
    print(f"Solution time: {model.Runtime:.2f} seconds")
    print(f"Active services: {len(service_data)}/{len(service_vars)}")
    print(f"Active frequencies: {len(freq_data)}/{len(freq_vars)}")
    
    # Print some sample non-zero variables
    print("\n" + "="*80)
    print("SAMPLE SOLUTION VALUES")
    print("="*80)
    print("\nService variables (first 10 non-zero):")
    print(f"{'Service ID':<15} {'Value':<15} {'Cost':<15}")
    print("-"*50)
    for i, item in enumerate(service_data[:10]):
        print(f"{item['service_id']:<15} {item['value']:<15.2f} {item['cost']:<15.2f}")
    if len(service_data) > 10:
        print(f"... and {len(service_data) - 10} more")
    
    print("\nFrequency variables (first 10 non-zero):")
    print(f"{'Frequency ID':<15} {'Value':<15}")
    print("-"*30)
    for i, item in enumerate(freq_data[:10]):
        print(f"{item['freq_id']:<15} {item['value']:<15}")
    if len(freq_data) > 10:
        print(f"... and {len(freq_data) - 10} more")
    
    print("\n" + "="*80)
    print(f"optimal_value = {model.ObjVal}")
    print(f"objective = {model.ObjVal}")
    print(f"result = {model.ObjVal}")
    print("="*80)

elif model.Status == GRB.INFEASIBLE:
    print("Model is INFEASIBLE")
    print("Computing IIS...")
    model.computeIIS()
    model.write("logs/infeasible.ilp")
    print("IIS written to logs/infeasible.ilp")
    print("optimal_value = INFEASIBLE")
    
elif model.Status == GRB.UNBOUNDED:
    print("Model is UNBOUNDED")
    print("optimal_value = UNBOUNDED")
    
else:
    print(f"Optimization ended with status {model.Status}")
    print("optimal_value = ERROR")

print("\n" + "="*80)
print("OPTIMIZATION COMPLETE")
print("="*80)

