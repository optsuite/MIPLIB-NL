import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import re
import os


def solve_optimization_problem():
    # ==========================
    # 1. Data Reading and Preprocessing
    # ==========================
    print("Reading data...")

    # Path configuration
    weight_path = 'data/weight.csv'
    b1_path = 'data/B1.csv'
    b2_path = 'data/B2.csv'

    # 1.1 Read order heat generation (Weight)
    # The first column is Order ID, the second column is Heat
    df_weight = pd.read_csv(weight_path)
    # Assuming order IDs are sequential 0..I-1, convert directly to dictionary {Order ID: Heat}
    weights = dict(zip(df_weight.iloc[:, 0], df_weight.iloc[:, 1]))
    num_orders = len(weights)
    print(f"Read heat data for {num_orders} orders.")

    # 1.2 Read process constraints (B1)
    # Row index is order (X0, X1...), column index is machine (0, 1...)
    # index_col=0 uses the first column (X0, X1...) as the row index
    df_b1 = pd.read_csv(b1_path, index_col=0)

    # Build feasible assignment set feasible_assignments = [(i, j), ...]
    # Can also use a dictionary for faster lookup
    feasible_pairs = set()

    # Iterate through DataFrame to get feasible solutions (positions with value 1)
    # df_b1.index is X0, X1... need to parse out numeric ID
    # df_b1.columns is '0', '1'... need to parse out numeric ID

    for row_label, row in df_b1.iterrows():
        # Extract order ID, e.g., "X0" -> 0
        order_id = int(re.search(r'\d+', str(row_label)).group())

        for col_label, val in row.items():
            if val == 1:
                machine_id = int(col_label)
                feasible_pairs.add((order_id, machine_id))

    print(f"Read {len(feasible_pairs)} feasible (order-machine) assignment pairs.")

    # 1.3 Read pipe connection relationships (B2)
    # This is a sparse matrix structure where each row represents a pipe, listing (order, machine) pairs connected to it
    # Since the number of columns per row is variable, it is recommended to use raw python file reading or pandas reading followed by processing

    pipe_connections = {}  # {pipe_id: [(order_id, machine_id), ...]}

    with open(b2_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        # Skip possible header if the first line is not data.
        # According to file description, the first line might be "Main pipe0,(0 0)..." format, or might have a Header.
        # Make a robust check here: look for lines containing "Main pipe"

        for line in lines:
            if "Main pipe" not in line:
                continue

            parts = line.strip().split(',')
            # The first part is the pipe name, e.g., "Main pipe0"
            pipe_name = parts[0]
            pipe_id = int(re.search(r'\d+', pipe_name).group())

            connections = []
            # The subsequent parts are (i j)
            for part in parts[1:]:
                part = part.strip()
                if not part: continue

                # Parse (i j) or (i, j)
                # Use regex to extract the two numbers inside
                match = re.findall(r'\d+', part)
                if len(match) >= 2:
                    o_id = int(match[0])
                    m_id = int(match[1])
                    connections.append((o_id, m_id))

            pipe_connections[pipe_id] = connections

    num_pipes = len(pipe_connections)
    print(f"Read connection information for {num_pipes} exhaust main pipes.")

    # ==========================
    # 2. Build Gurobi Model
    # ==========================
    print("Building optimization model...")
    model = gp.Model("Heat_Optimization")

    # 2.1 Define decision variables
    # x[i, j] = 1 if order i is assigned to machine j
    # Create variables only for (i, j) allowed in B1
    x = {}
    for i, j in feasible_pairs:
        x[i, j] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    # Auxiliary variable Z: represents the maximum heat load among all pipes
    z = model.addVar(vtype=GRB.CONTINUOUS, name="max_heat_load")

    # 2.2 Constraints

    # Constraint 1: Each order must be assigned to exactly one machine
    for i in range(num_orders):
        # Find all feasible machines j for order i
        possible_machines = [j for (o, j) in feasible_pairs if o == i]
        if not possible_machines:
            print(f"Warning: Order {i} has no available machines!")
            continue
        model.addConstr(gp.quicksum(x[i, j] for j in possible_machines) == 1, name=f"assign_order_{i}")

    # Constraint 2: Calculate heat load for each pipe and require it <= Z
    # Load_k = sum(weight[i] * x[i, j]) for all (i, j) connected to pipe k
    for pipe_id, pairs in pipe_connections.items():
        terms = []
        for (i, j) in pairs:
            # Note: (i, j) listed in B2 must be in B1's feasible set for us to have corresponding variable x[i,j]
            # If B2 has combinations not allowed by B1, ignore (since x[i,j] must be 0 or nonexistent)
            if (i, j) in x:
                heat_val = weights.get(i, 0)
                terms.append(heat_val * x[i, j])

        if terms:
            pipe_load = gp.quicksum(terms)
            model.addConstr(pipe_load <= z, name=f"pipe_load_limit_{pipe_id}")

    # 2.3 Set objective function
    # Minimize Z (i.e., minimize the maximum heat load)
    model.setObjective(z, GRB.MINIMIZE)

    # ==========================
    # 3. Solving and Output
    # ==========================
    print("Starting solve...")
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print("\n" + "=" * 30)
        print("Solved successfully!")
        print(f"Minimized maximum pipe heat load (Objective): {model.objVal}")
        print("=" * 30)

        # Print partial assignment results
        print("\nSpecific assignment plan:")
        assignments = []
        for (i, j), var in x.items():
            if var.x > 0.5:
                assignments.append((i, j))
                print(f"Order {i} -> Machine {j} (Heat: {weights[i]})")

        # Verify final load of each pipe
        print("\nFinal load for each pipe:")
        max_load = 0
        for pipe_id, pairs in pipe_connections.items():
            current_load = 0
            for (i, j) in pairs:
                # Check if this combination is selected
                if (i, j) in assignments:
                    current_load += weights.get(i, 0)
            print(f"Pipe {pipe_id}: {current_load}")
            if current_load > max_load:
                max_load = current_load

        print(f"\nVerified maximum load: {max_load}")

    else:
        print("Optimal solution not found.")


if __name__ == "__main__":
    solve_optimization_problem()