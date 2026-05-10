"""
Market Sharing Problem Solver

Solves the Market Sharing optimization problem using Gurobi.
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
import sys
from typing import Dict, List, Optional

class MarketSharingSolver:
    """
    Market Sharing Solver
    
    Reads data from CSV files and solves the optimization problem.
    """
    
    def __init__(self, instance_dir: str = '.'):
        """
        Initialize solver
        
        Args:
            instance_dir: Directory containing instance.json and data/ folder
        """
        self.instance_dir = instance_dir
        self.model = gp.Model("MarketSharing")
        
        # Data
        self.markets_df = None
        self.packages_df = None
        self.parameters = {}
        
        # Model components
        self.x = {}  # Bundle selection variables
        self.u = {}  # Shortfall variables
        
    def load_data(self):
        """Load data from CSV and JSON files"""
        print(f"Loading data from {self.instance_dir}...")
        
        # 1. Load instance.json for parameters and validation
        json_path = os.path.join(self.instance_dir, 'instance.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                instance_data = json.load(f)
                self.parameters = instance_data.get('parameters', {})
                self.optimal_value = instance_data.get('optimal_value')
                print(f"  ✓ Loaded instance.json")
        else:
            print(f"  ⚠ instance.json not found at {json_path}")
            
        # 2. Load markets data
        markets_path = os.path.join(self.instance_dir, 'data', 'markets.csv')
        if not os.path.exists(markets_path):
            raise FileNotFoundError(f"Markets file not found: {markets_path}")
            
        self.markets_df = pd.read_csv(markets_path)
        print(f"  ✓ Loaded markets.csv ({len(self.markets_df)} markets)")
        
        # 3. Load packages data
        packages_path = os.path.join(self.instance_dir, 'data', 'packages.csv')
        if not os.path.exists(packages_path):
            raise FileNotFoundError(f"Packages file not found: {packages_path}")
            
        self.packages_df = pd.read_csv(packages_path)
        print(f"  ✓ Loaded packages.csv ({len(self.packages_df)} bundles)")
        
    def build_model(self):
        """Build the optimization model"""
        print("Building model...")
        
        # Parameters
        penalty_per_unit = float(self.parameters.get('penalty_per_unit', 1.0))
        
        # Variables
        # x_b: binary, select bundle b
        for _, row in self.packages_df.iterrows():
            pkg_id = row['package_id']
            self.x[pkg_id] = self.model.addVar(vtype=GRB.BINARY, name=f"x_{pkg_id}")
            
        # u_m: continuous >= 0, shortfall in market m
        for _, row in self.markets_df.iterrows():
            mkt_id = row['market_id']
            self.u[mkt_id] = self.model.addVar(lb=0.0, name=f"u_{mkt_id}")
            
        self.model.update()
        
        # Objective: Minimize total shortfall penalty
        # min sum(w * u_m)
        obj_expr = gp.LinExpr()
        for mkt_id in self.u:
            obj_expr += penalty_per_unit * self.u[mkt_id]
        self.model.setObjective(obj_expr, GRB.MINIMIZE)
        
        # Set Gurobi parameters
        self.model.setParam('MIPFocus', 1)  # Focus on finding feasible solutions
        self.model.setParam('TimeLimit', 300)  # 5 minutes time limit

        
        # Constraints
        # For each market: Delivered + Shortfall = Target
        for _, m_row in self.markets_df.iterrows():
            m_id = m_row['market_id']
            target = m_row['target_units']
            
            # Calculate delivered units from all bundles
            # Column name in packages.csv is market_{m_id}
            col_name = f"market_{m_id}"
            if col_name not in self.packages_df.columns:
                raise ValueError(f"Column {col_name} not found in packages.csv")
                
            delivered_expr = gp.LinExpr()
            for _, p_row in self.packages_df.iterrows():
                pkg_id = p_row['package_id']
                units = p_row[col_name]
                if units > 0:
                    delivered_expr += units * self.x[pkg_id]
            
            # Constraint: Delivered + Shortfall = Target
            # Note: This implies Delivered <= Target because Shortfall >= 0
            self.model.addConstr(delivered_expr + self.u[m_id] == target, name=f"balance_{m_id}")
            
        print("Model built successfully.")
        
    def solve(self):
        """Solve the model"""
        print("Solving...")
        self.model.optimize()
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"\n✓ Optimal solution found!")
            obj_val = self.model.ObjVal
            print(f"  Objective Value: {obj_val}")
            
            # Verify against optimal_value from instance.json
            if self.optimal_value is not None and self.optimal_value != "":
                try:
                    expected_val = float(self.optimal_value)
                    if abs(obj_val - expected_val) < 1e-4:
                        print(f"  ✓ Verified against instance.json (Matches {expected_val})")
                    else:
                        print(f"  ✗ Mismatch with instance.json (Expected {expected_val}, got {obj_val})")
                except ValueError:
                    print(f"  ⚠ Could not parse optimal_value from instance.json: {self.optimal_value}")
            
            return True
        else:
            print(f"\n✗ Solver ended with status {self.model.Status}")
            return False

    def print_solution(self):
        """Print solution details"""
        if self.model.Status == GRB.OPTIMAL:
            print("\nSolution Details:")
            print("-" * 40)
            
            # Selected bundles
            selected_bundles = []
            for pkg_id, var in self.x.items():
                if var.X > 0.5:
                    selected_bundles.append(pkg_id)
            print(f"Selected Bundles ({len(selected_bundles)}): {selected_bundles}")
            
            # Market status
            print("\nMarket Status:")
            total_shortfall = 0
            for _, row in self.markets_df.iterrows():
                m_id = row['market_id']
                target = row['target_units']
                shortfall = self.u[m_id].X
                delivered = target - shortfall
                total_shortfall += shortfall
                print(f"  Market {m_id}: Target={target}, Delivered={delivered:.1f}, Shortfall={shortfall:.1f}")
            
            print(f"\nTotal Shortfall: {total_shortfall:.1f}")

if __name__ == "__main__":
    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # If an argument is provided, treat it as a subdirectory of the script directory
    # unless it's an absolute path
    if len(sys.argv) > 1:
        arg_path = sys.argv[1]
        if os.path.isabs(arg_path):
            instance_dir = arg_path
        else:
            instance_dir = os.path.join(script_dir, arg_path)
    else:
        # Default to the script directory
        instance_dir = script_dir
    
    solver = MarketSharingSolver(instance_dir)
    try:
        solver.load_data()
        solver.build_model()
        solver.solve()
        solver.print_solution()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
