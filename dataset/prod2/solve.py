#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate optimization problem from CSV files and solve using Gurobi
"""

import csv
import json
import gurobipy as gp
from gurobipy import GRB
import os


def load_data():
    """Load CSV data files"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    
    # Read instance.json to get parameters
    instance_path = os.path.join(base_dir, 'instance.json')
    with open(instance_path, 'r', encoding='utf-8') as f:
        instance = json.load(f)
    
    M = int(instance['parameters']['M'])  # Number of subsystems
    N = int(instance['parameters']['N'])  # Number of tests
    
    # Read system.csv: Subsystems and their options
    system_path = os.path.join(data_dir, 'system.csv')
    subsystems = {}  # {Subsystem Name: [List of Options]}
    all_options = []  # All options
    
    with open(system_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                subsystem_name = row[0]
                options = [opt for opt in row[1:] if opt]  # Filter empty values
                subsystems[subsystem_name] = options
                all_options.extend(options)
    
    # Read test.csv: Test coefficients
    test_path = os.path.join(data_dir, 'test.csv')
    test_coefficients = []  # List of coefficients for each test
    
    with open(test_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # First row is variable names
        for row in reader:
            if row:
                coeffs = [float(x) for x in row]
                test_coefficients.append(coeffs)
    
    # Read test2.csv: Test thresholds
    test2_path = os.path.join(data_dir, 'test2.csv')
    test_thresholds = {}  # {Test Name: Threshold}
    
    with open(test2_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                test_name = row[0]
                threshold = float(row[1])
                test_thresholds[test_name] = threshold
    
    # Get thresholds in test order
    thresholds = [test_thresholds[f'Test_{i+1}'] for i in range(N)]
    
    return subsystems, all_options, test_coefficients, thresholds, M, N


def create_optimization_model(subsystems, all_options, test_coefficients, thresholds, M, N):
    """Create Gurobi optimization model"""
    
    # Create model
    model = gp.Model("prod1")
    model.setParam('OutputFlag', 1)  # Display solution process
    model.setParam('LogToConsole', 1)  # Output to console
    
    print("=" * 80)
    print("Starting to build optimization model...")
    print("=" * 80)
    
    # Create variables
    # 1. Option variables (binary): C0000001, C0000002, ...
    option_vars = {}
    for i, option in enumerate(all_options, 1):
        var_name = f"C{i:08d}"
        option_vars[option] = model.addVar(vtype=GRB.BINARY, name=var_name, lb=0, ub=1)
    
    # 2. Test auxiliary variables (integer 0-1): C0000050, C0000051, ... C0000149
    test_aux1_vars = {}
    for i in range(N):
        var_name = f"C{i+50:08d}"
        test_aux1_vars[i] = model.addVar(vtype=GRB.BINARY, name=var_name, lb=0, ub=1)
    
    # 3. Test auxiliary variables (integer 0-1): C0000100, C0000101, ... C0000149
    test_aux2_vars = {}
    for i in range(N):
        var_name = f"C{i+100:08d}"
        test_aux2_vars[i] = model.addVar(vtype=GRB.BINARY, name=var_name, lb=0, ub=1)
    
    # 4. Test failure flag variables (binary): C0000150, C0000151, ... C0000249
    test_fail_vars = {}
    for i in range(N):
        var_name = f"C{i+150:08d}"
        test_fail_vars[i] = model.addVar(vtype=GRB.BINARY, name=var_name, lb=0, ub=1)
    
    # 4. Objective function variable: C0000250 (total number of failed tests)
    obj_var = model.addVar(vtype=GRB.CONTINUOUS, name="C00000250", lb=0)
    
    print(f"Variables created:")
    print(f"  - Option variables: {len(option_vars)}")
    print(f"  - Test auxiliary variables 1 (C0000050-C0000149): {len(test_aux1_vars)}")
    print(f"  - Test auxiliary variables 2 (C0000100-C0000149): {len(test_aux2_vars)}")
    print(f"  - Test failure variables (C0000150-C0000249): {len(test_fail_vars)}")
    print(f"  - Objective function variable: 1")
    
    # Update model to add variables
    model.update()
    
    # Add constraints
    constraint_count = 0
    
    # 1. Objective function constraint: C0000250 = sum(C0000150 + ... + C0000249)
    obj_expr = -obj_var
    for i in range(N):
        obj_expr += test_fail_vars[i]
    model.addConstr(obj_expr == 0, name="R0000001")
    constraint_count += 1
    
    # 2. Subsystem mutual exclusion constraint: Each subsystem must and can only select one option
    subsystem_list = list(subsystems.keys())
    for idx, subsystem_name in enumerate(subsystem_list, 2):
        options = subsystems[subsystem_name]
        expr = gp.LinExpr()
        for option in options:
            expr += option_vars[option]
        model.addConstr(expr == 1.0, name=f"R{idx:08d}")
        constraint_count += 1
    
    print(f"Added subsystem mutual exclusion constraints: {M}")
    
    # 3. Test constraints
    # According to constraint format in prod.json:
    # R0000009: sum(coeffs*vars) - 7.0*C0000050 <= -threshold
    # R0000109: 7.0*C0000100 + C0000200 <= 7.0
    #
    # Implemented using Big-M method: if sum(coeffs*vars) < threshold, then test_fail = 1
    big_M = 100.0  # Big-M value, should be larger than any possible linear combination value
    
    for test_idx in range(N):
        coeffs = test_coefficients[test_idx]
        threshold = thresholds[test_idx]
        
        # Calculate linear combination
        expr = gp.LinExpr()
        for i, option in enumerate(all_options):
            expr += coeffs[i] * option_vars[option]
        
        # Constraint 1: According to prod.json format: sum(coeffs*vars) - 7.0*C0000050 <= -threshold
        # i.e.: sum(coeffs*vars) + threshold <= 7.0*C0000050
        # Since C0000050 is a 0-1 integer, this constraint actually means:
        # If sum >= threshold, then C0000050 must >= (sum + threshold)/7.0
        # If sum < threshold, then C0000050 can be smaller
        # But for simplicity, we use the Big-M method
        model.addConstr(expr + 7.0 * test_aux1_vars[test_idx] >= threshold,
                       name=f"R{test_idx + M + 2:08d}")
        constraint_count += 1
        
        # Constraint 2: Use Big-M method to judge if qualified
        # If sum(coeffs*vars) < threshold, then test_fail = 1
        # Constraint: sum(coeffs*vars) >= threshold - big_M * test_fail
        model.addConstr(expr >= threshold - big_M * test_fail_vars[test_idx],
                       name=f"R{test_idx + M + N + 2:08d}")
        constraint_count += 1
        
        # Constraint 3: Establish relationship between C0000100 and test result
        # C0000100 = 1 - test_fail (1 means passed, 0 means failed)
        model.addConstr(test_aux2_vars[test_idx] == 1 - test_fail_vars[test_idx],
                       name=f"R{test_idx + M + N + N + 2:08d}")
        constraint_count += 1
        
        # Constraint 4: 7.0*C0000100 + C0000200 <= 7.0
        # If C0000100 < 1.0, then C0000200 can be 1 (failed)
        # If C0000100 = 1.0, then C0000200 must be 0 (passed)
        model.addConstr(7.0 * test_aux2_vars[test_idx] + test_fail_vars[test_idx] <= 7.0,
                       name=f"R{test_idx + M + N + N + N + 2:08d}")
        constraint_count += 1
    
    print(f"Added test pass/fail constraints: {N}")
    print(f"Total constraints: {constraint_count}")
    
    # Set objective function: Maximize number of passed tests
    model.setObjective(100-obj_var, GRB.MAXIMIZE)
    
    print("=" * 80)
    print("Model construction completed!")
    print("=" * 80)
    
    return model, option_vars, test_aux1_vars, test_aux2_vars, test_fail_vars, obj_var


def solve_model(model):
    """Solve model"""
    print("\n" + "=" * 80)
    print("Starting solution...")
    print("=" * 80 + "\n")
    
    # Optimize
    model.optimize()
    
    print("\n" + "=" * 80)
    print("Solution completed!")
    print("=" * 80)
    
    # Check solution status
    if model.status == GRB.OPTIMAL:
        print(f"\nOptimal objective value: {model.ObjVal}")
        print(f"Number of failed tests: {model.ObjVal}")
        
        # Display selected options
        print("\nSelected options:")
        for var in model.getVars():
            if var.VarName.startswith("C") and len(var.VarName) == 9:
                var_num = int(var.VarName[1:])
                if 1 <= var_num <= 49 and var.X > 0.5:
                    print(f"  {var.VarName}: {var.X}")
        
    elif model.status == GRB.INFEASIBLE:
        print("\nModel infeasible!")
        model.computeIIS()
        print("\nInfeasible constraints:")
        for c in model.getConstrs():
            if c.IISConstr:
                print(f"  {c.ConstrName}: {c}")
    elif model.status == GRB.UNBOUNDED:
        print("\nModel unbounded!")
    else:
        print(f"\nSolution status: {model.status}")
    
    return model


def main():
    """Main function"""
    try:
        # Load data
        print("Loading data files...")
        subsystems, all_options, test_coefficients, thresholds, M, N = load_data()
        print(f"Data loading completed:")
        print(f"  - Number of subsystems: {M}")
        print(f"  - Number of tests: {N}")
        print(f"  - Total options: {len(all_options)}")
        print(f"  - Test coefficient matrix: {len(test_coefficients)} x {len(test_coefficients[0]) if test_coefficients else 0}")
        
        # Create model
        model, option_vars, test_aux1_vars, test_aux2_vars, test_fail_vars, obj_var = \
            create_optimization_model(subsystems, all_options, test_coefficients, thresholds, M, N)
        
        # Solve model
        model = solve_model(model)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()