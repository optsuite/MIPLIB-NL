import gurobipy as gp
from gurobipy import GRB
import json
import pandas as pd
import os
import sys

def solve():
    # Paths
    problem_path = "./problem.json"
    log_path = "./logs/log.txt"
    
    # Ensure spec directory exists for log
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    # Redirect stdout to log file
    class Logger(object):
        def __init__(self):
            self.terminal = sys.stdout
            self.log = open(log_path, "w", encoding='utf-8')

        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)

        def flush(self):
            self.terminal.flush()
            self.log.flush()

    sys.stdout = Logger()

    try:
        # 1. Read Problem Data
        print("Reading problem configuration...")
        with open(problem_path, 'r', encoding='utf-8') as f:
            problem_data = json.load(f)

        n = problem_data['parameters']['n']
        p = problem_data['parameters']['p']
        chains_file_rel_path = problem_data['files']['chains']['path']
        
        # Handle path relative to problem.json location
        chains_path = os.path.normpath(os.path.join(os.path.dirname(problem_path), chains_file_rel_path))
        
        print(f"Reading chains data from {chains_path}...")
        chains_df = pd.read_csv(chains_path)

        # Preprocess chains data
        # Create a dictionary or list structure for efficient access
        # chains[i] = list of (service_city_id, order)
        chains = {}
        all_service_cities = set()
        
        for _, row in chains_df.iterrows():
            owner = int(row['chain_owner_city_id'])
            service = int(row['service_city_id'])
            order = int(row['order'])
            
            if owner not in chains:
                chains[owner] = []
            chains[owner].append((service, order))
            all_service_cities.add(service)

        # 2. Build Model
        print("Building Gurobi model...")
        model = gp.Model("WarehouseLocation")
        
        # Set log file for Gurobi internal logging
        model.setParam('LogFile', log_path)

        # Variables
        # y[j] = 1 if city j is selected as warehouse
        y = model.addVars(range(n), vtype=GRB.BINARY, name="y")
        
        # x[i, j] = 1 if city i is served by city j
        # Only create x variables for valid (i, j) pairs in chains
        x = {}
        for i in chains:
            for service_city, order in chains[i]:
                x[i, service_city] = model.addVar(vtype=GRB.BINARY, obj=order, name=f"x_{i}_{service_city}")

        # Constraints
        
        # 1. Select exactly p warehouses
        model.addConstr(y.sum() == p, "Select_p_warehouses")

        # 2. Each city i must be served by exactly one city in its chain
        for i in chains:
            model.addConstr(gp.quicksum(x[i, j] for j, _ in chains[i]) == 1, f"Serve_city_{i}")

        # 3. Service validity: x[i, j] <= y[j]
        for i in chains:
            for j, _ in chains[i]:
                model.addConstr(x[i, j] <= y[j], f"Link_{i}_{j}")

        # Objective is already set via obj parameter in addVar (Minimize by default)

        # 3. Solve
        print("Solving...")
        model.optimize()

        # 4. Output Results
        if model.Status == GRB.OPTIMAL:
            print("\nOptimal Solution Found!")
            print(f"Objective Value (Total Cost): {model.ObjVal}")
            
            selected_cities = []
            for j in range(n):
                if y[j].X > 0.5:
                    selected_cities.append(j)
            
            selected_cities.sort()
            print(f"Selected Cities (Warehouses): {selected_cities}")
            
            # Optional: Print detailed assignment
            # print("\nAssignments:")
            # for i in chains:
            #     for j, order in chains[i]:
            #         if x[i, j].X > 0.5:
            #             print(f"City {i} served by {j} (Cost: {order})")
            
        else:
            print("No optimal solution found.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    solve()
