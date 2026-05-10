import gurobipy as gp
from gurobipy import GRB
import csv
import os


def solve_optimization_problem():
    # Define data directory path
    data_dir = "data"

    # Check if data exists
    if not os.path.exists(data_dir):
        print(f"Error: Data directory '{data_dir}' not found.")
        return

    print("Loading data from CSV files...")

    # 1. Read objective function coefficients (C1.csv)
    # Format: [EquipmentID, ObjectiveCoefficient]
    obj_coeffs = {}
    var_names = []
    with open(os.path.join(data_dir, "C1.csv"), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            v_name, coeff = row[0], float(row[1])
            obj_coeffs[v_name] = coeff
            var_names.append(v_name)

    # 2. Read resource limit upper bounds (C3.csv)
    # Format: [ResourceID, Limit]
    res_limits = []
    with open(os.path.join(data_dir, "C3.csv"), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            res_limits.append((row[0], float(row[1])))

    # 3. Read resource consumption matrix (C2.csv)
    # Format: [EquipmentID, Val1, Val2, ...]
    # Note: Column order corresponds to row order in C3
    res_matrix = {}
    with open(os.path.join(data_dir, "C2.csv"), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            v_name = row[0]
            # row[1:] is the consumption of each resource by the equipment
            res_matrix[v_name] = [float(x) for x in row[1:]]

    # 4. Read performance target lower bounds (C5.csv)
    # Format: [PerformanceID, Target]
    perf_targets = []
    with open(os.path.join(data_dir, "C5.csv"), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            perf_targets.append((row[0], float(row[1])))

    # 5. Read performance contribution matrix (C4.csv)
    # Format: [EquipmentID, Val1, Val2, ...]
    # Note: Column order corresponds to row order in C5
    perf_matrix = {}
    with open(os.path.join(data_dir, "C4.csv"), 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row: continue
            v_name = row[0]
            # row[1:] is the contribution of the equipment to each performance metric
            perf_matrix[v_name] = [float(x) for x in row[1:]]

    # --- Build Gurobi Model ---
    print("Building Optimization Model...")

    try:
        model = gp.Model("PolarExpeditionSupply")

        # Create decision variables
        # Variables are integer (Integer), lower bound is 0
        vars_dict = {}
        for v in var_names:
            vars_dict[v] = model.addVar(vtype=GRB.INTEGER, lb=0.0, name=v)

        # Update model to integrate variables
        model.update()

        # Set objective function: Minimize sum(coeff * var)
        obj_expr = gp.quicksum(obj_coeffs[v] * vars_dict[v] for v in var_names)
        model.setObjective(obj_expr, GRB.MINIMIZE)

        # Add resource limit constraints (Upper Bounds: LHS <= Limit)
        # res_limits[j] corresponds to res_matrix[v][j]
        for j, (r_id, limit) in enumerate(res_limits):
            lhs = gp.quicksum(res_matrix[v][j] * vars_dict[v] for v in var_names)
            model.addConstr(lhs <= limit, name=f"Resource_{r_id}")

        # Add performance requirement constraints (Lower Bounds: LHS >= Target)
        # perf_targets[k] corresponds to perf_matrix[v][k]
        for k, (p_id, target) in enumerate(perf_targets):
            lhs = gp.quicksum(perf_matrix[v][k] * vars_dict[v] for v in var_names)
            model.addConstr(lhs >= target, name=f"Performance_{p_id}")

        # --- Solve ---
        print("Solving...")
        model.optimize()

        # --- Output Results ---
        if model.status == GRB.OPTIMAL:
            print("\n" + "=" * 30)
            print(f"Optimal Solution Found!")
            print(f"Objective Value (Total Scientific Cost/Value): {model.objVal:.4f}")
            print("=" * 30)
            print("Transport Plan:")
            for v in var_names:
                val = vars_dict[v].x
                if val > 0.5:  # Only print equipment with quantity greater than 0
                    print(f"  {v}: {int(round(val))}")
        else:
            print(f"\nModel Status: {model.status}")
            print("No optimal solution found.")

    except gp.GurobiError as e:
        print(f"Gurobi Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    solve_optimization_problem()