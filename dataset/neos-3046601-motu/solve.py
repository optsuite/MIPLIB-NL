import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import json
import os


def solve_neos_problem_corrected():
    # ==========================================
    # 1. Set paths and read configuration
    # ==========================================
    desktop_path = os.path.join(os.path.expanduser("~"), 'Desktop')
    base_dir = os.path.join(desktop_path, 'neos-3046601-motu')
    data_dir = os.path.join(base_dir, 'data')
    instance_file = os.path.join(base_dir, 'instance.json')

    print(f"Reading data path: {base_dir}")

    with open(instance_file, 'r', encoding='utf-8') as f:
        instance_data = json.load(f)

    params = instance_data['parameters']
    N = params['N']
    K = params['K']  # 203.0

    # Read CSV
    df_loc = pd.read_csv(os.path.join(data_dir, 'locations.csv'))
    df_trans = pd.read_csv(os.path.join(data_dir, 'transitions.csv'))

    locations = df_loc['Location_ID'].tolist()
    min_arrival_dict = df_loc.set_index('Location_ID')['Min_Arrival_Time'].to_dict()
    deadline_dict = df_loc.set_index('Location_ID')['Deadline'].to_dict()

    arcs = []
    travel_times = {}
    total_travel_sum = 0
    for _, row in df_trans.iterrows():
        u = int(row['From_Location_ID'])
        v = int(row['To_Location_ID'])
        cost = float(row['Setup_Time'])
        arcs.append((u, v))
        travel_times[(u, v)] = cost
        total_travel_sum += cost

    # Estimate a tighter time upper bound
    tight_max_time = max(min_arrival_dict.values()) + total_travel_sum

    # ==========================================
    # 2. Build model (Open Path Formulation)
    # ==========================================
    model = gp.Model("neos-3046615-murg-path")

    # --- Variables ---
    x = model.addVars(arcs, vtype=GRB.BINARY, name="x")

    t = {}
    for i in locations:
        t[i] = model.addVar(lb=min_arrival_dict[i], ub=tight_max_time, vtype=GRB.CONTINUOUS, name=f"t_{i}")

    d = model.addVars(locations, lb=0.0, vtype=GRB.CONTINUOUS, name="d")

    # --- Constraints ---

    # 1. Path Constraints
    # This is a single machine scheduling problem (Hamiltonian Path), not a TSP cycle.
    # Features: N points, N-1 edges, each point entered at most once, left at most once.

    # Total edges must be N-1 (ensure all points are on the path)
    model.addConstr(gp.quicksum(x[i, j] for i, j in arcs) == N - 1, "TotalEdges")

    # Out-degree of each point <= 1 (end point out-degree is 0)
    model.addConstrs((gp.quicksum(x[i, j] for j in locations if (i, j) in arcs) <= 1 for i in locations), "OutDegree")

    # In-degree of each point <= 1 (start point in-degree is 0)
    model.addConstrs((gp.quicksum(x[i, j] for i in locations if (i, j) in arcs) <= 1 for j in locations), "InDegree")

    # 2. Time Continuity (Indicator Constraints)
    # If x[i,j] = 1, then t[j] >= t[i] + cost
    # Note: MTZ-like constraints combined with the above degree constraints can automatically eliminate subtours, ensuring a single chain
    for i, j in arcs:
        cost = travel_times[(i, j)]
        model.addGenConstrIndicator(x[i, j], 1, t[j] >= t[i] + cost, name=f"Time_{i}_{j}")

    # 3. Delay Calculation
    for i in locations:
        model.addConstr(d[i] >= t[i] - deadline_dict[i], name=f"Delay_{i}")

    # --- Objective ---
    model.setObjective(
        gp.quicksum(d[i] for i in locations) + gp.quicksum(t[i] for i in locations) - K,
        GRB.MINIMIZE
    )

    # ==========================================
    # 3. Solve Parameters
    # ==========================================
    model.Params.Presolve = 2
    model.Params.MIPFocus = 1  # Focus on finding feasible solutions quickly
    model.Params.TimeLimit = 3000

    print("\nStart solving the corrected model (Open Path)...")
    model.optimize()

    # ==========================================
    # 4. Result Output
    # ==========================================
    if model.status in [GRB.OPTIMAL, GRB.TIME_LIMIT] and model.SolCount > 0:
        print("\n" + "=" * 60)
        print(f"Optimal objective value: {model.ObjVal:.4f}")
        print("=" * 60)

        # Path reconstruction logic
        path_links = {i: j for i, j in arcs if x[i, j].X > 0.5}

        # Find the start point: the point with in-degree 0, or the point with the earliest time
        # Under numerical errors, directly finding the earliest time point is most robust
        start_node = min(locations, key=lambda i: t[i].X)

        print(f"\n{'Location':<10} | {'Arrival':<10} | {'Deadline':<10} | {'Delay':<10}")
        print("-" * 50)

        curr = start_node
        visited = set()
        while curr not in visited and len(visited) < N:
            visited.add(curr)
            arr = t[curr].X
            ddl = deadline_dict[curr]
            dly = d[curr].X
            print(f"{curr:<10} | {arr:<10.1f} | {ddl:<10.1f} | {dly:<10.1f}")

            if curr in path_links:
                curr = path_links[curr]
            else:
                break
    else:
        print("No optimal solution found.")


if __name__ == "__main__":
    solve_neos_problem_corrected()