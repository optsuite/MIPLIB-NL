import json
import gurobipy as gp
from gurobipy import GRB
import os

def solve_wachplan(problem_path="./instance.json"):
    # Read problem data
    with open(problem_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    params = data['parameters']
    n_crew = params['n_crew']
    n_slots = params['n_slots']
    min_on_duty = params['min_on_duty']
    max_on_duty = params['max_on_duty']
    window_size = params['window_size']
    max_shifts_in_window = params['max_shifts_in_window']

    # Create model
    model = gp.Model("Wachplan")
    
    # Decision Variables
    # x[i, t] = 1 if crew i is on duty at slot t
    # Indices: crew 0..n_crew-1, slot 0..n_slots-1
    x = model.addVars(n_crew, n_slots, vtype=GRB.BINARY, name="x")
    
    # Z: Total shifts per person
    Z = model.addVar(vtype=GRB.INTEGER, name="Z")

    # Objective: Maximize Z
    model.setObjective(Z, GRB.MAXIMIZE)

    # Constraints

    # 1. Crew Size per Slot
    for t in range(n_slots):
        model.addConstr(gp.quicksum(x[i, t] for i in range(n_crew)) >= min_on_duty, name=f"min_duty_{t}")
        model.addConstr(gp.quicksum(x[i, t] for i in range(n_crew)) <= max_on_duty, name=f"max_duty_{t}")

    # 2. No Consecutive Shifts (Cyclic)
    for i in range(n_crew):
        for t in range(n_slots):
            next_t = (t + 1) % n_slots
            model.addConstr(x[i, t] + x[i, next_t] <= 1, name=f"no_consecutive_{i}_{t}")

    # 3. Rolling Window Constraint (Cyclic)
    for i in range(n_crew):
        for t in range(n_slots):
            # Window starting at t: t, t+1, ..., t+window_size-1
            window_slots = [(t + k) % n_slots for k in range(window_size)]
            model.addConstr(gp.quicksum(x[i, ws] for ws in window_slots) <= max_shifts_in_window, 
                            name=f"window_{i}_{t}")

    # 4. Fairness (Equal Shifts)
    for i in range(n_crew):
        model.addConstr(gp.quicksum(x[i, t] for t in range(n_slots)) == Z, name=f"fairness_{i}")

    # 5. Social Goal: Every pair together at least once
    # We use auxiliary variables z[i,j,t] to linearize x[i,t] * x[j,t]
    # Since we only need sum(z) >= 1, we can use a simpler approach or Gurobi's quadratic constraints.
    # However, to be explicit and safe, let's use linearization or General Constraints if available.
    # Here we use standard linearization for robustness.
    for i in range(n_crew):
        for j in range(i + 1, n_crew):
            # z_ijt = 1 iff x_it=1 and x_jt=1
            # We need sum_t z_ijt >= 1
            
            # Create z variables for this pair
            z_pair = model.addVars(n_slots, vtype=GRB.BINARY, name=f"z_{i}_{j}")
            
            for t in range(n_slots):
                # z <= x_i
                model.addConstr(z_pair[t] <= x[i, t])
                # z <= x_j
                model.addConstr(z_pair[t] <= x[j, t])
                # z >= x_i + x_j - 1
                model.addConstr(z_pair[t] >= x[i, t] + x[j, t] - 1)
            
            model.addConstr(gp.quicksum(z_pair[t] for t in range(n_slots)) >= 1, name=f"social_{i}_{j}")

    # 6. Pre-assignments
    # Slot 1 (index 0): Crew 1, 2, 3 (indices 0, 1, 2)
    # Slot 2 (index 1): Crew 4, 5 (indices 3, 4)
    # Note: Problem description uses 1-based indexing for crew and slots.
    
    # Slot 1: Crew 1, 2, 3
    model.addConstr(x[0, 0] == 1, name="pre_1_1")
    model.addConstr(x[1, 0] == 1, name="pre_2_1")
    model.addConstr(x[2, 0] == 1, name="pre_3_1")
    
    # Slot 2: Crew 4, 5
    model.addConstr(x[3, 1] == 1, name="pre_4_2")
    model.addConstr(x[4, 1] == 1, name="pre_5_2")

    # Output logging
    log_path = os.path.join(os.path.dirname(problem_path), "logs", "log.txt")
    model.setParam("LogFile", log_path)

    # Solve
    model.optimize()

    with open(log_path, "a", encoding='utf-8') as log_file:
        log_file.write("\n" + "="*30 + "\n")
        # Write Gurobi status
        log_file.write(f"Status: {model.Status}\n")
        
        if model.Status == GRB.OPTIMAL:
            log_file.write(f"Objective Value (Max Shifts per Person): {model.ObjVal}\n")
            log_file.write(f"Total Shifts per Person (Z): {Z.X}\n\n")
            
            log_file.write("Schedule:\n")
            for t in range(n_slots):
                on_duty = []
                for i in range(n_crew):
                    if x[i, t].X > 0.5:
                        on_duty.append(i + 1) # Convert back to 1-based index
                log_file.write(f"Slot {t + 1}: Crew {on_duty}\n")
        else:
            log_file.write("No optimal solution found.\n")

if __name__ == "__main__":
    solve_wachplan()
