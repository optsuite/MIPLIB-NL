import sys
import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Paths
    problem_path = "./problem.json"
    log_path = "./logs/log.txt"
    
    # Read problem definition
    try:
        with open(problem_path, 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
    except Exception as e:
        print(f"Error reading problem.json: {e}")
        return

    # Extract parameters
    params = problem_data['parameters']
    n_shifts = params['n']
    num_states = params['num_states']
    prod_rates = {
        0: params['prod_rate_1'],
        1: params['prod_rate_2'],
        2: params['prod_rate_3']
    }
    demand_interval = params['demand_interval']
    demand_amount = params['demand_amount']
    max_inventory = params['max_inventory']
    
    files_config = problem_data['files']
    
    # helper for path resolution
    base_dir = os.path.dirname(os.path.abspath(problem_path))
    
    def resolve_path(rel_path):
        return os.path.join(base_dir, rel_path)

    # Load Data
    trans_cost_path = resolve_path(files_config['transition_costs']['path'])
    init_inv_cost_path = resolve_path(files_config['initial_inventory_costs']['path'])
    
    df_trans = pd.read_csv(trans_cost_path)
    df_inv = pd.read_csv(init_inv_cost_path)
    
    # Process Transition Costs into a dict: cost[(shift, state_in, state_out)]
    # Note: Shift in CSV is 1-based, consistent with n_shifts usually.
    cost_map = {}
    for _, row in df_trans.iterrows():
        t = int(row['shift'])
        s_in = int(row['state_in'])
        s_out = int(row['state_out'])
        c = float(row['cost'])
        cost_map[(t, s_in, s_out)] = c
        
    # Process Inventory Costs: cost[product_id]
    inv_cost_map = {}
    for _, row in df_inv.iterrows():
        pid = int(row['product_id'])
        c = float(row['unit_cost'])
        inv_cost_map[pid] = c
        
    # Model Setup
    model = gp.Model("ProductionParams")
    
    # Redirect log
    model.setParam('LogFile', log_path)
    model.setParam('LogToConsole', 1) 
    
    # Sets
    shifts = range(1, n_shifts + 1)
    states = range(num_states)
    products = [1, 2, 3] # P1, P2, P3
    # Map product to state: P1->State0, P2->State1, P3->State2
    # So Product p corresponds to State p-1
    product_state_map = {1: 0, 2: 1, 3: 2}

    # Variables
    # x[t, i, j] = 1 if shift t transitions i->j
    x = model.addVars(shifts, states, states, vtype=GRB.BINARY, name="x")
    
    # inv[p] = initial inventory of product p
    inv = model.addVars(products, lb=0, ub=max_inventory, vtype=GRB.INTEGER, name="inv")
    
    # Objective
    # sum(inventory cost) + sum(transition cost)
    obj_expr = gp.LinExpr()
    
    for p in products:
        obj_expr += inv[p] * inv_cost_map[p]
        
    for t in shifts:
        for i in states:
            for j in states:
                # Check if cost data exists, otherwise assume infinity or error
                # Based on problem, full matrix should be provided.
                c = cost_map.get((t, i, j), 1e9) 
                obj_expr += x[t, i, j] * c
                
    model.setObjective(obj_expr, GRB.MINIMIZE)
    
    # Constraint 1: One transition per shift
    for t in shifts:
        model.addConstr(gp.quicksum(x[t, i, j] for i in states for j in states) == 1, name=f"OneTransition_t{t}")
        
    # Constraint 2: Continuity
    # Line A: Odd shifts 1, 3, 5...
    # Output of t == Input of t+2
    odd_shifts = [t for t in shifts if t % 2 != 0]
    even_shifts = [t for t in shifts if t % 2 == 0]
    
    for t in odd_shifts:
        if t + 2 <= n_shifts:
            for s in states:
                # Flow out of 's' in shift t (as output) == Flow into 's' in shift t+2 (as input)
                # sum_k x[t, k, s] == sum_j x[t+2, s, j]
                lhs = gp.quicksum(x[t, k, s] for k in states)
                rhs = gp.quicksum(x[t+2, s, j] for j in states)
                model.addConstr(lhs == rhs, name=f"ContinuityA_t{t}_s{s}")

    for t in even_shifts:
        if t + 2 <= n_shifts:
            for s in states:
                lhs = gp.quicksum(x[t, k, s] for k in states)
                rhs = gp.quicksum(x[t+2, s, j] for j in states)
                model.addConstr(lhs == rhs, name=f"ContinuityB_t{t}_s{s}")
                
    # Constraint 3: Demand Satisfaction
    # Checkpoints: 2, 4, ..., n
    checkpoints = [t for t in shifts if t % demand_interval == 0]
    
    for t_idx, t_check in enumerate(checkpoints):
        # Current demand needed
        # Logic: "every demand_interval shifts... increase by demand_amount"
        # Shift 2: 5. Shift 4: 10.
        current_demand = (t_check // demand_interval) * demand_amount
        
        for p in products:
            target_s = product_state_map[p]
            rate = prod_rates[target_s]
            
            # Cumulative production up to t_check
            # Production in shift t for product p depends on reaching target_s
            prod_expr = gp.LinExpr()
            
            # Sum over all shifts tau <= t_check
            for tau in range(1, t_check + 1):
                # Production if output state is target_s
                prod_expr += gp.quicksum(x[tau, i, target_s] for i in states) * rate
            
            model.addConstr(inv[p] + prod_expr >= current_demand, name=f"Demand_t{t_check}_p{p}")
            
    # Solve
    model.optimize()
    
    # Output
    if model.Status == GRB.OPTIMAL:
        print(f"Optimal Objective: {model.ObjVal}")
        with open(log_path, 'a') as f:
            f.write(f"\nOptimization Finished.\n")
            f.write(f"Optimal Objective: {model.ObjVal}\n")
            f.write("Decisions:\n")
            f.write("Initial Inventory:\n")
            for p in products:
                val = inv[p].X
                msg = f"  Product {p}: {val}\n"
                print(msg.strip())
                f.write(msg)
            
            f.write("Schedule:\n")
            for t in shifts:
                for i in states:
                    for j in states:
                        if x[t, i, j].X > 0.5:
                            msg = f"  Shift {t}: State {i} -> {j} (Produces P{j+1})\n"
                            print(msg.strip())
                            f.write(msg)
    else:
        print("No optimal solution found.")
        with open(log_path, 'a') as f:
            f.write(f"\nNo optimal solution found. Status: {model.Status}\n")

if __name__ == "__main__":
    solve()
