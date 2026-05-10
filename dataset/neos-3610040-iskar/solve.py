import gurobipy as gp
from gurobipy import GRB
import csv
import json
import os


def solve_optimization_problem():
    # 1. Read instance.json to get global parameters
    instance_file = 'instance.json'
    if not os.path.exists(instance_file):
        print(f"Error: Cannot find {instance_file}")
        return

    with open(instance_file, 'r', encoding='utf-8') as f:
        instance_data = json.load(f)

    # Get fixed cost
    c_fixed = instance_data.get('parameters', {}).get('C_fixed', 37.0)
    print(f"Global Fixed Cost: {c_fixed}")

    # 2. Initialize model
    model = gp.Model("EV_Energy_Management")

    # 3. Create variables
    # Dictionary to store variable objects
    vars_dict = {}

    # --- Read C1.csv: Create continuous variables (Battery State) ---
    # Format: Node_ID, Max_Capacity
    print("Loading continuous variables (C1.csv)...")
    with open('data/C1.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            node_id = row[0]
            max_cap = float(row[1])

            # Create continuous variable: lower bound=0, upper bound=Max_Capacity
            var = model.addVar(lb=0.0, ub=max_cap, vtype=GRB.CONTINUOUS, name=node_id)
            vars_dict[node_id] = var

    # --- Read C3.csv: Create binary variables (Charging Decision) ---
    # Format: Charging_Option_ID, Cost
    # We also need to store these costs to build the objective function
    print("Loading binary variables (C3.csv)...")
    charging_costs = {}
    with open('data/C3.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            bin_id = row[0]
            cost = float(row[1])

            # Create binary variable
            var = model.addVar(vtype=GRB.BINARY, name=bin_id)
            vars_dict[bin_id] = var
            charging_costs[bin_id] = cost

    # Update model to integrate variables
    model.update()

    # 4. Set objective function
    # Minimize Total Cost = Fixed_Cost + Sum(Charging_Cost * Bin_Var)
    obj_expr = c_fixed + gp.quicksum(charging_costs[bid] * vars_dict[bid] for bid in charging_costs)
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # 5. Add constraints

    # --- Read C2.csv: Energy dynamic constraints ---
    # Format: Prev_Node, Next_Node, Bin_Var, Coeff, RHS
    # Constraint: Next - Prev - (Coeff * Bin) <= RHS
    print("Adding energy dynamic constraints (C2.csv)...")
    with open('data/C2.csv', 'r') as f:
        reader = csv.reader(f)
        count_c2 = 0
        for row in reader:
            if not row: continue
            prev_node = row[0]
            next_node = row[1]
            bin_var_id = row[2]
            coeff = float(row[3])
            rhs = float(row[4])

            # Build expression: C_next - C_prev
            expr = vars_dict[next_node] - vars_dict[prev_node]

            # If there is an associated charging variable (bin_var_id is not '0' and not empty)
            if bin_var_id and bin_var_id != '0' and bin_var_id in vars_dict:
                # Subtract (Coeff * Bin_Var)
                expr -= coeff * vars_dict[bin_var_id]

            model.addConstr(expr <= rhs, name=f"Dyn_{prev_node}_{next_node}")
            count_c2 += 1
    print(f"Added {count_c2} energy dynamic constraints")

    # --- Read C4.csv: Phase linking constraints ---
    # Format: Prev_End_Node, Next_Start_Node
    # Constraint: Next_Start - Prev_End <= 0
    print("Adding phase linking constraints (C4.csv)...")
    with open('data/C4.csv', 'r') as f:
        reader = csv.reader(f)
        count_c4 = 0
        for row in reader:
            if not row: continue
            prev_end = row[0]
            next_start = row[1]

            model.addConstr(vars_dict[next_start] - vars_dict[prev_end] <= 0,
                            name=f"Link_{prev_end}_{next_start}")
            count_c4 += 1
    print(f"Added {count_c4} linking constraints")

    # 6. Solve model
    print("\nStarting optimization...")
    model.optimize()

    # 7. Output results
    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 30)
        print(f"Optimal solution found!")
        print(f"Minimum Total Cost: {model.objVal:.4f}")
        print("=" * 30)

        # Output charging strategy (which variables are set to 1)
        print("\nRecommended Charging Stations:")
        active_charging = []
        for bid in charging_costs:
            if vars_dict[bid].x > 0.5:
                print(f"  - {bid}: Cost {charging_costs[bid]}")
                active_charging.append(bid)

        if not active_charging:
            print("  (No charging needed throughout the journey)")

        # Optional: Output path battery level change sample
        # print("\nPartial node battery states:")
        # sample_nodes = list(vars_dict.keys())[:10]
        # for nid in sample_nodes:
        #     if nid.startswith('C') and nid not in charging_costs:
        #        print(f"  {nid}: {vars_dict[nid].x:.4f}")

    else:
        print("\nOptimal solution not found. Model status:", model.status)
        # If infeasible, compute IIS
        if model.status == GRB.INFEASIBLE:
            print("Model infeasible, computing IIS...")
            model.computeIIS()
            model.write("model.ilp")
            print("Conflicting constraints written to model.ilp")


if __name__ == "__main__":
    solve_optimization_problem()