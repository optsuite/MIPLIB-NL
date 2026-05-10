import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os


def solve_pressure_control_problem():
    # 1. Set file paths
    data_dir = 'data'
    nodes_path = os.path.join(data_dir, 'nodes.csv')
    pumps_path = os.path.join(data_dir, 'pump_resources.csv')
    segments_path = os.path.join(data_dir, 'network_segments.csv')
    params_path = os.path.join(data_dir, 'global_params.csv')

    # 2. Read CSV data
    try:
        nodes_df = pd.read_csv(nodes_path)
        pumps_df = pd.read_csv(pumps_path)
        segments_df = pd.read_csv(segments_path)
        params_df = pd.read_csv(params_path)
        print("All data files read successfully.")
    except FileNotFoundError as e:
        print(f"Error: File not found. Please ensure the data folder and CSV files exist.\nDetails: {e}")
        return

    # 3. Initialize Gurobi model
    model = gp.Model("Chemical_Network_Pressure_Control")

    # 4. Create variables
    print("Creating variables...")

    # 4.1 Continuous variables: Pressure Nodes
    # Read nodes.csv: node_id, max_pressure
    pressure_vars = {}
    for _, row in nodes_df.iterrows():
        node_id = row['node_id']
        max_p = float(row['max_pressure'])
        # Create variable: lower bound=0.0 (default), upper bound=max_pressure
        pressure_vars[node_id] = model.addVar(
            lb=0.0,
            ub=max_p,
            vtype=GRB.CONTINUOUS,
            name=node_id
        )

    # 4.2 Binary variables: Pump activation (Pump Resources)
    # Read pump_resources.csv: pump_id, activation_cost
    pump_vars = {}
    pump_costs = {}  # Used for objective function
    for _, row in pumps_df.iterrows():
        pump_id = row['pump_id']
        cost = float(row['activation_cost'])

        pump_vars[pump_id] = model.addVar(
            vtype=GRB.BINARY,
            name=pump_id
        )
        pump_costs[pump_id] = cost

    # Update model to integrate variables
    model.update()

    # 5. Set objective function (Minimize Total Cost)
    print("Setting objective function...")

    # Get base construction cost (C_base)
    # global_params.csv: parameter, value
    base_cost_row = params_df[params_df['parameter'] == 'C_base']
    if not base_cost_row.empty:
        base_cost = float(base_cost_row['value'].iloc[0])
    else:
        base_cost = 0.0
        print("Warning: C_base not found in global_params.csv, defaulting to 0.0")

    # Construct total cost expression: Base Cost + Sum(Pump Cost * Pump Binary)
    total_cost_expr = base_cost + gp.quicksum(
        pump_costs[pid] * pump_vars[pid] for pid in pump_vars
    )

    model.setObjective(total_cost_expr, GRB.MINIMIZE)

    # 6. Add constraints
    print("Adding constraints...")

    # Read network_segments.csv:
    # segment_id, upstream_node, downstream_node, max_natural_diff, linked_pump_id, pump_boost_capacity

    count = 0
    for _, row in segments_df.iterrows():
        seg_id = row['segment_id']
        u_node = row['upstream_node']
        d_node = row['downstream_node']
        rhs_val = float(row['max_natural_diff'])
        pump_id = row['linked_pump_id']
        boost_cap = float(row['pump_boost_capacity'])

        # Ensure involved node variables exist
        if u_node not in pressure_vars or d_node not in pressure_vars:
            print(f"Warning: Constraint {seg_id} references non-existent node variables, skipped.")
            continue

        # Basic flow constraint: Downstream - Upstream <= RHS
        # Corresponds to original logic: 1.0*Down + -1.0*Up ... <= RHS
        expr = pressure_vars[d_node] - pressure_vars[u_node]

        # If a pump is linked, relax the constraint (subtract boost term)
        # Corresponds to original logic: ... + -4.0*Pump <= RHS
        # If Pump=1, then Down - Up - 4.0 <= RHS => Down - Up <= RHS + 4.0 (allows larger pressure difference/drop compensation)
        if pd.notna(pump_id) and pump_id != 'None':
            if pump_id in pump_vars:
                expr -= boost_cap * pump_vars[pump_id]
            else:
                print(f"Warning: Constraint {seg_id} references non-existent pump variable {pump_id}")

        model.addConstr(expr <= rhs_val, name=seg_id)
        count += 1

    print(f"Added {count} pipeline segment constraints.")

    # 7. Solve
    print("\nStarting solution...")
    model.optimize()

    # 8. Output results
    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 30)
        print("Optimization successful (Optimal Solution Found)")
        print(f"Minimum Total Cost (Objective Value): {model.objVal:,.2f}")
        print("=" * 30)

        # Print activated pumps
        print("\n[Activated Pump Resources]:")
        active_pumps = []
        for pid, var in pump_vars.items():
            if var.X > 0.5:  # Check if binary variable is 1
                active_pumps.append((pid, pump_costs[pid]))

        if active_pumps:
            for pid, cost in active_pumps:
                print(f"  - {pid}: Cost {cost}")
            print(f"  Activated {len(active_pumps)} pumps.")
        else:
            print("  No pumps activated.")

        # Optional: Export results to file
        # model.write("solution.sol")

    else:
        print(f"\nSolution ended, status code: {model.status}")
        if model.status == GRB.INFEASIBLE:
            print("Model is infeasible.")
            # model.computeIIS()
            # model.write("model.ilp")


if __name__ == "__main__":
    solve_pressure_control_problem()