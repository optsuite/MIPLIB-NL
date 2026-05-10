"""
Market Sharing Problem Solver (Hard Version)

Solves the modified Market Sharing optimization problem using Gurobi.
Handles long-format data and string identifiers.
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
import sys

class MarketSharingSolver:
    def __init__(self, instance_dir: str = '.'):
        self.instance_dir = instance_dir
        self.model = gp.Model("MarketSharingHard")
        
        # Data
        self.markets_df = None
        self.contents_df = None
        self.parameters = {}
        self.optimal_value = None
        
        # Model components
        self.x = {}  # Bundle selection variables
        self.u = {}  # Shortfall variables
        
        # Mappings
        self.market_codes = []
        self.package_codes = []
        self.supply_map = {} # (package_code, market_code) -> units

    def load_data(self):
        print(f"Loading data from {self.instance_dir}...")
        
        # 1. Load instance.json
        json_path = os.path.join(self.instance_dir, 'instance.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                instance_data = json.load(f)
                self.parameters = instance_data.get('parameters', {})
                self.optimal_value = instance_data.get('optimal_value')
                print(f"  ✓ Loaded instance.json")
        
        # 2. Load markets
        markets_path = os.path.join(self.instance_dir, 'data', 'markets.csv')
        self.markets_df = pd.read_csv(markets_path)
        self.market_codes = self.markets_df['market_code'].tolist()
        print(f"  ✓ Loaded markets.csv ({len(self.markets_df)} zones)")
        
        # 3. Load package contents
        contents_path = os.path.join(self.instance_dir, 'data', 'package_contents.csv')
        self.contents_df = pd.read_csv(contents_path)
        self.package_codes = sorted(self.contents_df['package_code'].unique().tolist())
        
        # Build supply map
        for _, row in self.contents_df.iterrows():
            self.supply_map[(row['package_code'], row['market_code'])] = row['exposure_units']
            
        print(f"  ✓ Loaded package_contents.csv ({len(self.package_codes)} unique bundles)")

    def build_model(self):
        print("Building model...")
        
        # Variables
        # x[p]: Select package p
        for p_code in self.package_codes:
            self.x[p_code] = self.model.addVar(vtype=GRB.BINARY, name=f"x_{p_code}")
            
        # u[m]: Shortfall in market m
        for m_code in self.market_codes:
            self.u[m_code] = self.model.addVar(lb=0.0, name=f"u_{m_code}")
            
        self.model.update()
        
        # Objective: Maximize Total Utility (Service Fulfillment)
        # Total Utility = Total Demand - Total Shortfall
        # We use the slack formulation (Supply + u = Target) which is computationally efficient,
        # but set the objective to Maximize (Total Demand - sum(u)).
        
        total_demand = self.markets_df['target_units'].sum()
        print(f"  Total Demand: {total_demand}")
        
        obj_expr = total_demand - gp.quicksum(self.u[m] for m in self.market_codes)
        self.model.setObjective(obj_expr, GRB.MAXIMIZE)
        
        # Constraints
        # For each market: Delivered + Shortfall = Target
        for _, row in self.markets_df.iterrows():
            m_code = row['market_code']
            target = row['target_units']
            
            # Calculate delivered units
            # Sum over all packages that have content for this market
            delivered_expr = gp.LinExpr()
            
            # Iterate over packages that have supply for this market
            # (Optimization: could pre-build an adjacency list, but this is fast enough for verification)
            for p_code in self.package_codes:
                if (p_code, m_code) in self.supply_map:
                    units = self.supply_map[(p_code, m_code)]
                    delivered_expr += units * self.x[p_code]
            
            self.model.addConstr(delivered_expr + self.u[m_code] == target, name=f"bal_{m_code}")
            
        print("Model built successfully.")

    def solve(self):
        print("Solving...")
        self.model.optimize()
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"\\n✓ Optimal solution found!")
            obj_val = self.model.ObjVal
            print(f"  Objective Value (Total Utility): {obj_val}")
            
            if self.optimal_value is not None:
                try:
                    # instance.json contains the optimal *shortfall* (1.0)
                    # We need to convert it to optimal *utility* for comparison
                    optimal_shortfall = float(self.optimal_value)
                    total_demand = self.markets_df['target_units'].sum()
                    expected_val = total_demand - optimal_shortfall
                    
                    if abs(obj_val - expected_val) < 1e-4:
                        print(f"  ✓ Verified against instance.json (Matches {expected_val} [Derived from Demand {total_demand} - Shortfall {optimal_shortfall}])")
                    else:
                        print(f"  ✗ Mismatch (Expected {expected_val}, got {obj_val})")
                except:
                    pass
            return True
        else:
            print(f"Solver status: {self.model.Status}")
            return False

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Handle arguments if needed
    if len(sys.argv) > 1 and not os.path.isabs(sys.argv[1]):
         instance_dir = os.path.join(script_dir, sys.argv[1])
    elif len(sys.argv) > 1:
         instance_dir = sys.argv[1]
    else:
         instance_dir = script_dir
         
    solver = MarketSharingSolver(instance_dir)
    try:
        solver.load_data()
        solver.build_model()
        solver.solve()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
