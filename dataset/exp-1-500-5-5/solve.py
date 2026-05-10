import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Read problem.json
    # The script is expected to be run from the problem root directory
    problem_path = "./problem.json"
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    params = problem_data['parameters']
    num_products = params['num_products']
    num_periods = params['num_periods']
    capacities = params['capacities']
    
    # Read data files
    demand_file = problem_data['files']['demand']['path']
    costs_file = problem_data['files']['costs']['path']
    
    demand_df = pd.read_csv(demand_file)
    costs_df = pd.read_csv(costs_file)
    
    # Pre-process data into dictionaries for easy access
    demands = {}
    for _, row in demand_df.iterrows():
        demands[(int(row['product_id']), int(row['period']))] = row['demand']
        
    prod_costs = {}
    setup_costs = {}
    hold_costs = {}
    back_costs = {}
    for _, row in costs_df.iterrows():
        key = (int(row['product_id']), int(row['period']))
        prod_costs[key] = row['production_cost']
        setup_costs[key] = row['setup_cost']
        hold_costs[key] = row['holding_cost']
        back_costs[key] = row['backlog_cost']
        
    # Create model
    model = gp.Model("ProductionScheduling")
    
    # Log to file
    log_file_path = "./logs/log.txt"
    # Ensure directory exists
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    
    # Set Gurobi log file
    model.setParam('LogFile', log_file_path)
    
    # Variables
    products = range(1, num_products + 1)
    periods = range(1, num_periods + 1)
    
    x = model.addVars(products, periods, lb=0, name="x")
    y = model.addVars(products, periods, vtype=GRB.BINARY, name="y")
    inv = model.addVars(products, periods, lb=0, name="inv")
    back = model.addVars(products, periods, lb=0, name="back")
    
    # Objective
    obj = gp.quicksum(
        prod_costs[i, t] * x[i, t] + 
        setup_costs[i, t] * y[i, t] + 
        hold_costs[i, t] * inv[i, t] + 
        back_costs[i, t] * back[i, t]
        for i in products for t in periods
    )
    model.setObjective(obj, GRB.MINIMIZE)
    
    # Constraints
    # 1. Inventory Balance
    for i in products:
        for t in periods:
            prev_inv = inv[i, t-1] if t > 1 else 0
            prev_back = back[i, t-1] if t > 1 else 0
            model.addConstr(prev_inv - prev_back + x[i, t] - demands[i, t] == inv[i, t] - back[i, t], name=f"balance_{i}_{t}")
            
    # 2. Capacity and Setup
    for i in products:
        cap = capacities[i-1]
        for t in periods:
            model.addConstr(x[i, t] <= cap * y[i, t], name=f"cap_{i}_{t}")
            
    # 3. Single Machine Constraint
    for t in periods:
        model.addConstr(gp.quicksum(y[i, t] for i in products) <= 1, name=f"single_machine_{t}")
        
    # 4. Terminal Condition
    for i in products:
        model.addConstr(inv[i, num_periods] == 0, name=f"final_inv_{i}")
        model.addConstr(back[i, num_periods] == 0, name=f"final_back_{i}")
        
    # Solve
    model.optimize()
    
    # Append key information to log.txt
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*30 + "\n")
        f.write("Optimization Results:\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Total Cost: {model.objVal}\n\n")
            f.write(f"{'Period':<10}{'Product':<15}{'Quantity':<10}{'Inventory/Backlog (All Products)':<40}\n")
            for t in periods:
                produced_product = "None"
                produced_qty = 0.0
                for i in products:
                    if y[i, t].X > 0.5:
                        produced_product = f"Product {i}"
                        produced_qty = x[i, t].X
                        break
                
                inv_back_details = []
                for i in products:
                    inv_back_details.append(f"P{i}(I:{inv[i, t].X:.1f}, B:{back[i, t].X:.1f})")
                inv_back_info = ", ".join(inv_back_details)
                
                f.write(f"{t:<10}{produced_product:<15}{produced_qty:<10.2f}{inv_back_info}\n")
        else:
            f.write("No optimal solution found.\n")

if __name__ == "__main__":
    solve()
