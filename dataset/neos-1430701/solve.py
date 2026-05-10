import gurobipy as gp
from gurobipy import GRB
import csv
import ast
import os


def solve_network_optimization():
    # Define data folder path (assumes data folder is in the same directory as this script)
    data_dir = "data"

    if not os.path.exists(data_dir):
        print(f"Error: Folder {data_dir} not found. Please ensure the script and the data folder are in the same directory.")
        return

    # Initialize model
    model = gp.Model("Wireless_Network_Optimization")

    # -------------------------------------------------------------
    # 1. Variable Definition (Read channel_hardware_specs.csv)
    # -------------------------------------------------------------
    # x[id]: Continuous variable, channel power (Power Level)
    # y[id]: Binary variable, channel activation status (Activation Status, 0/1)
    x = {}
    y = {}

    hardware_file = os.path.join(data_dir, 'channel_hardware_specs.csv')
    print(f"Reading variable definitions: {hardware_file} ...")

    if not os.path.exists(hardware_file):
        print(f"Error: File not found {hardware_file}")
        return

    with open(hardware_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ch_id = row['Channel_ID']
            max_power = float(row['Max_Power'])

            # Create binary switch variable (y)
            y[ch_id] = model.addVar(vtype=GRB.BINARY, name=f"Active_{ch_id}")

            # Create continuous power variable (x), lower bound is 0
            x[ch_id] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"Power_{ch_id}")

            # Hardware constraint: x_i <= 3.0 * y_i
            model.addConstr(x[ch_id] <= max_power * y[ch_id], name=f"Link_Hardware_{ch_id}")

    # Update model to include variables
    model.update()

    # -------------------------------------------------------------
    # 2. Regional Capacity Limits (Read capacity_constraints.csv)
    # -------------------------------------------------------------
    capacity_file = os.path.join(data_dir, 'capacity_constraints.csv')
    print(f"Loading capacity limits: {capacity_file} ...")

    with open(capacity_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            c_id = row['Constraint_ID']
            limit = float(row['Limit_Value'])
            ch_ids = ast.literal_eval(row['Channel_IDs'])

            # [Correction 1] Use gp.quicksum (all lowercase)
            expr = gp.quicksum(x[ch] for ch in ch_ids if ch in x)
            model.addConstr(expr <= limit, name=c_id)

    # -------------------------------------------------------------
    # 3. Interference Conflict Constraints (Read interference_pairs.csv)
    # -------------------------------------------------------------
    interf_file = os.path.join(data_dir, 'interference_pairs.csv')
    print(f"Loading interference conflicts: {interf_file} ...")

    with open(interf_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ch_a = row['Channel_A_ID']
            ch_b = row['Channel_B_ID']

            if ch_a in y and ch_b in y:
                model.addConstr(y[ch_a] + y[ch_b] <= 1, name=f"Conflict_{ch_a}_{ch_b}")

    # -------------------------------------------------------------
    # 4. Conditional Regulations/Master-Slave Constraints (Read conditional_regulations.csv)
    # -------------------------------------------------------------
    cond_file = os.path.join(data_dir, 'conditional_regulations.csv')
    print(f"Loading conditional regulations: {cond_file} ...")

    with open(cond_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            master_id = row['Master_Channel_ID']
            slave_ids = ast.literal_eval(row['Slave_Channel_IDs'])

            if master_id in x:
                vars_in_sum = [x[master_id]]
                vars_in_sum.extend(x[s] for s in slave_ids if s in x)

                # [Correction 2] Use gp.quicksum
                expr = gp.quicksum(vars_in_sum) + 4092.0 * y[master_id]
                model.addConstr(expr <= 4096.0, name=f"BigM_Rule_{master_id}")

    # -------------------------------------------------------------
    # 5. Set objective function and solve
    # -------------------------------------------------------------
    print("Solving...")
    # [Correction 3] Use gp.quicksum
    model.setObjective(gp.quicksum(x[ch] for ch in x), GRB.MAXIMIZE)

    model.optimize()

    # -------------------------------------------------------------
    # 6. Output results
    # -------------------------------------------------------------
    if model.status == GRB.OPTIMAL:
        print("\n=== Optimization Complete: Optimal Solution Found ===")
        print(f"Maximum Total Throughput (Total Power): {model.ObjVal:.4f}")

        active_channels = [ch for ch in y if y[ch].X > 0.5]
        print(f"Number of active channels: {len(active_channels)} / {len(y)}")

        print("\nActive Channel Details (Top 10):")
        sorted_active = sorted(active_channels)
        for ch in sorted_active[:10]:
            print(f"  Channel {ch}: Power = {x[ch].X:.4f}")

    else:
        print(f"\nOptimal solution not found. Status code: {model.status}")


if __name__ == "__main__":
    solve_network_optimization()