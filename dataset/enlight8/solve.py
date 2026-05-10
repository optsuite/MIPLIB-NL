"""
EnLight Puzzle Solver

Solves the EnLight (Lights Out variant) puzzle using Gurobi.
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
import sys
from typing import Dict, List, Optional

class EnLightSolver:
    """
    EnLight Solver
    
    Reads data from CSV files and solves the optimization problem.
    """
    
    def __init__(self, instance_dir: str = '.'):
        """
        Initialize solver
        
        Args:
            instance_dir: Directory containing instance.json and data/ folder
        """
        self.instance_dir = instance_dir
        self.model = gp.Model("EnLight")
        
        # Data
        self.grid_df = None
        self.moves_df = None
        self.effects_df = None
        self.parameters = {}
        self.optimal_value = None
        
        # Model components
        self.x = {}  # Move variables (binary)
        self.y = {}  # Auxiliary variables for parity (integer)
        
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
            
        # 2. Load grid data
        grid_path = os.path.join(self.instance_dir, 'data', 'grid.csv')
        if not os.path.exists(grid_path):
            raise FileNotFoundError(f"Grid file not found: {grid_path}")
            
        self.grid_df = pd.read_csv(grid_path)
        print(f"  ✓ Loaded grid.csv ({len(self.grid_df)} cells)")
        
        # 3. Load moves data
        moves_path = os.path.join(self.instance_dir, 'data', 'moves.csv')
        if not os.path.exists(moves_path):
            raise FileNotFoundError(f"Moves file not found: {moves_path}")
            
        self.moves_df = pd.read_csv(moves_path)
        print(f"  ✓ Loaded moves.csv ({len(self.moves_df)} moves)")
        
        # 4. Load move effects data
        effects_path = os.path.join(self.instance_dir, 'data', 'move_effects.csv')
        if not os.path.exists(effects_path):
            raise FileNotFoundError(f"Move effects file not found: {effects_path}")
            
        self.effects_df = pd.read_csv(effects_path)
        print(f"  ✓ Loaded move_effects.csv ({len(self.effects_df)} effects)")
        
    def build_model(self):
        """Build the optimization model"""
        print("Building model...")
        
        # Variables
        # x_m: binary, use move m
        for _, row in self.moves_df.iterrows():
            move_id = row['move_id']
            self.x[move_id] = self.model.addVar(vtype=GRB.BINARY, name=f"x_{move_id}")
            
        # y_c: integer >= 0, auxiliary for parity constraint
        for _, row in self.grid_df.iterrows():
            cell_id = row['cell_id']
            self.y[cell_id] = self.model.addVar(vtype=GRB.INTEGER, lb=0, name=f"y_{cell_id}")
            
        self.model.update()
        
        # Objective: Minimize total moves
        self.model.setObjective(gp.quicksum(self.x.values()), GRB.MINIMIZE)
        
        # Constraints
        # For each cell: initial_state + sum(moves affecting cell) = 2 * k
        
        # Pre-process effects to map cell_id -> list of move_ids
        cell_to_moves = {}
        for _, row in self.effects_df.iterrows():
            cell_id = row['cell_id']
            move_id = row['move_id']
            if cell_id not in cell_to_moves:
                cell_to_moves[cell_id] = []
            cell_to_moves[cell_id].append(move_id)
            
        for _, row in self.grid_df.iterrows():
            cell_id = row['cell_id']
            initial_state = row['initial_state']
            
            # Sum of moves affecting this cell
            affecting_moves = cell_to_moves.get(cell_id, [])
            move_sum = gp.LinExpr()
            for move_id in affecting_moves:
                if move_id in self.x:
                    move_sum += self.x[move_id]
            
            # Constraint: initial + move_sum = 2 * y
            self.model.addConstr(initial_state + move_sum == 2 * self.y[cell_id], name=f"parity_{cell_id}")
            
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
            
            # Selected moves
            selected_moves = []
            for move_id, var in self.x.items():
                if var.X > 0.5:
                    selected_moves.append(move_id)
            
            print(f"Total Moves: {len(selected_moves)}")
            print(f"Selected Move IDs: {sorted(selected_moves)}")
            
            # Visualize grid
            # Create a grid of selected moves
            rows = self.grid_df['row'].max()
            cols = self.grid_df['col'].max()
            
            print("\nMove Grid (X = selected):")
            for r in range(1, rows + 1):
                row_str = ""
                for c in range(1, cols + 1):
                    # Find move_id for this r,c
                    # Assuming move_id maps to r,c as generated
                    # But better to look up in moves_df
                    move_row = self.moves_df[(self.moves_df['move_row'] == r) & (self.moves_df['move_col'] == c)]
                    if not move_row.empty:
                        move_id = move_row.iloc[0]['move_id']
                        if move_id in selected_moves:
                            row_str += " X "
                        else:
                            row_str += " . "
                    else:
                        row_str += " ? "
                print(row_str)

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
    
    solver = EnLightSolver(instance_dir)
    try:
        solver.load_data()
        solver.build_model()
        solver.solve()
        solver.print_solution()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
