import pandas as pd
import gurobipy as gp
from gurobipy import GRB


def solve_tsp_gurobi(locations_file, cost_matrix_file):
    # 1. Read data
    print("Reading data...")
    df_loc = pd.read_csv(locations_file)
    df_cost = pd.read_csv(cost_matrix_file)

    # Extract node list (assuming location_id is 1 to N)
    # Ensure node IDs are integers
    nodes = df_loc['location_id'].tolist()
    N = len(nodes)
    print(f"Number of nodes: {N}")

    # Build cost dictionary {(i, j): cost}
    # The first column of cost_matrix.csv is 'From/To', the remaining column headers are target node IDs
    cost = {}

    # Ensure 'From/To' column is used as index, if it isn't already
    if 'From/To' in df_cost.columns:
        df_cost.set_index('From/To', inplace=True)

    for i in nodes:
        for j in nodes:
            if i != j:
                # Note: Column names in CSV might be strings, index might be integer or string, need to match
                # Here we assume column names are string forms of numbers ('1', '2', ...)
                try:
                    c = df_cost.loc[i, str(j)]
                except KeyError:
                    # Try using integer index
                    c = df_cost.loc[i, j]

                cost[i, j] = float(c)

    # 2. Create Gurobi model
    print("Building model...")
    m = gp.Model("TSP_MTZ")

    # 3. Create variables
    # x[i,j] = 1 if moving directly from node i to node j, otherwise 0
    x = m.addVars(cost.keys(), vtype=GRB.BINARY, name="x")

    # u[i] is auxiliary variable for subtour elimination (representing visit order)
    # Defined on 2 to N (assuming node 1 is the start node)
    # Here nodes list is [1, 2, ..., 14]
    start_node = nodes[0]  # Usually 1
    u_nodes = nodes[1:]  # [2, ..., 14]
    u = m.addVars(u_nodes, vtype=GRB.CONTINUOUS, lb=1, ub=N - 1, name="u")

    # 4. Set objective function: minimize total cost
    m.setObjective(gp.quicksum(cost[i, j] * x[i, j] for i, j in cost.keys()), GRB.MINIMIZE)

    # 5. Add constraints

    # (1) Outflow of each node is 1
    m.addConstrs((gp.quicksum(x[i, j] for j in nodes if i != j) == 1 for i in nodes), name="Leave")

    # (2) Inflow of each node is 1
    m.addConstrs((gp.quicksum(x[i, j] for i in nodes if i != j) == 1 for j in nodes), name="Enter")

    # (3) MTZ subtour elimination constraints
    # u_i - u_j + N * x_ij <= N - 1 for all i, j != start_node and i != j
    for i in u_nodes:
        for j in u_nodes:
            if i != j:
                m.addConstr(u[i] - u[j] + N * x[i, j] <= N - 1, name=f"MTZ_{i}_{j}")

    # 6. Solve
    print("Starting solve...")
    m.optimize()

    # 7. Output results
    if m.status == GRB.OPTIMAL:
        print("\nOptimal solution found!")
        print(f"Minimum total cost: {m.objVal}")

        # Extract path
        solution_x = m.getAttr('x', x)
        tour = []
        curr = start_node
        while True:
            tour.append(curr)
            # Find the next node that current node curr points to
            next_node = None
            for j in nodes:
                if curr != j and solution_x[curr, j] > 0.5:
                    next_node = j
                    break

            if next_node is None or next_node == start_node:
                break
            curr = next_node

        # Add closing loop back to start node for display
        tour.append(start_node)
        print("Optimal path: " + " -> ".join(map(str, tour)))

        # Verification: print cost of each segment
        print("\nDetailed path costs:")
        total_check = 0
        for k in range(len(tour) - 1):
            u, v = tour[k], tour[k + 1]
            c = cost[u, v]
            total_check += c
            print(f"{u} -> {v}: {c}")
        print(f"Verified total cost: {total_check}")

    else:
        print("No optimal solution found.")


if __name__ == "__main__":
    # Ensure filenames match what you uploaded
    solve_tsp_gurobi('data/locations.csv', 'data/cost_matrix.csv')