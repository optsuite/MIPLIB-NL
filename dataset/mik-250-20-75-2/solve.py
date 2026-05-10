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
        # Load problem configuration
        with open(problem_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Extract parameters
        params = config['parameters']
        n = params['n']
        m = params['m']
        k = params['k']
        generator_capacity = params['generator_capacity']
        generator_cost = params['generator_cost']
        max_generators = params['max_generators']

        # Load data files
        files = config['files']
        stations_df = pd.read_csv(files['stations']['path'])
        products_df = pd.read_csv(files['products']['path'])
        prod_consumption_df = pd.read_csv(files['production_consumption']['path'])
        global_systems_df = pd.read_csv(files['global_systems']['path'])

        # Preprocess data for easier access
        # Stations
        stations = stations_df.set_index('id').to_dict('index')
        # Products
        products = products_df.set_index('id').to_dict('index')
        # Global Systems
        global_systems = global_systems_df.set_index('id').to_dict('index')
        
        # Production Consumption: Create a dictionary (station_id, product_id) -> load
        consumption = {}
        for _, row in prod_consumption_df.iterrows():
            consumption[(row['station_id'], row['product_id'])] = row['load']

        # Initialize Model
        model = gp.Model("SpaceStationScheduling")
        
        # Decision Variables
        # x[i]: Activate lab on station i (Binary)
        x = {}
        for i in stations:
            x[i] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}")
            
        # y[j]: Batches of product j (Integer)
        y = {}
        for j in products:
            y[j] = model.addVar(lb=0, ub=products[j]['max_batches'], vtype=GRB.INTEGER, name=f"y_{j}")
            
        # z[l]: Investment in global system l (Continuous)
        z = {}
        for l in global_systems:
            z[l] = model.addVar(lb=0, ub=global_systems[l]['max_level'], vtype=GRB.CONTINUOUS, name=f"z_{l}")
            
        # g[i]: Generators for station i (Integer)
        g = {}
        for i in stations:
            g[i] = model.addVar(lb=0, ub=max_generators, vtype=GRB.INTEGER, name=f"g_{i}")

        # Objective Function
        # Maximize: Lab Profit + Product Profit - Global System Cost - Generator Cost
        lab_profit = gp.quicksum(stations[i]['lab_value'] * x[i] for i in stations)
        product_profit = gp.quicksum(products[j]['unit_value'] * y[j] for j in products)
        system_cost = gp.quicksum(global_systems[l]['cost'] * z[l] for l in global_systems)
        gen_cost = gp.quicksum(generator_cost * g[i] for i in stations)
        
        model.setObjective(lab_profit + product_profit - system_cost - gen_cost, GRB.MAXIMIZE)

        # Constraints
        # Capacity Constraint per station
        # Lab Load + Product Load <= Base Capacity + Global System Capacity + Generator Capacity
        # Global System Capacity = sum(z_l) * 1 (since each unit increases capacity by 1)
        
        total_global_capacity = gp.quicksum(z[l] for l in global_systems)
        
        for i in stations:
            lab_load = stations[i]['lab_load'] * x[i]
            product_load = gp.quicksum(consumption.get((i, j), 0) * y[j] for j in products)
            base_cap = stations[i]['base_capacity']
            gen_cap = generator_capacity * g[i]
            
            model.addConstr(lab_load + product_load <= base_cap + total_global_capacity + gen_cap, name=f"Cap_{i}")

        # Optimize
        model.optimize()

        # Output Results
        print("\nOptimization Finished!")
        if model.status == GRB.OPTIMAL:
            print(f"Optimal Objective Value: {model.objVal}")
            
            print("\n--- Solution Details ---")
            
            print("\n[Station Lab Activation]")
            for i in stations:
                if x[i].x > 0.5:
                    print(f"Station {i}: Lab Activated")
                else:
                    print(f"Station {i}: Lab Not Activated")
                    
            print("\n[Product Production]")
            for j in products:
                val = int(round(y[j].x))
                if val > 0:
                    print(f"Product {j}: {val} batches")
                    
            print("\n[Global System Investment]")
            for l in global_systems:
                val = z[l].x
                if val > 1e-6:
                    print(f"System {l}: Level {val:.4f}")
                    
            print("\n[Generator Usage]")
            for i in stations:
                val = int(round(g[i].x))
                if val > 0:
                    print(f"Station {i}: {val} generators")
                    
        else:
            print("No optimal solution found.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    solve()
