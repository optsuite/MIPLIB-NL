"""
Cutting Stock Problem Solver

Build and solve cutting stock optimization model using Gurobi
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
from typing import Dict, List, Optional
import sys


class CuttingStockSolver:
    """
    Cutting Stock Problem Solver
    
    Read CSV data files and use Gurobi to build and solve the optimization model
    Strictly corresponds to the mathematical model in mas76.md
    """
    
    def __init__(self, data_folder: str):
        """
        Initialize solver
        
        Args:
            data_folder: Data folder path (containing CSV and JSON files)
        """
        self.data_folder = data_folder
        self.model = gp.Model("CuttingStockProblem")
        
        # Set definitions (corresponding to lines 9-11 in mas76.md)
        self.patterns = []  # P: Set of cutting patterns
        self.items = []     # I: Set of item types
        
        # Decision variables
        # x_p: Whether to use pattern p (binary variable)
        self.x = {}
        # z: Emergency supply quantity (continuous variable, replenishes all items at once)
        self.z = None
        
        # Parameters
        self.demands = {}
        self.pattern_productions = {}
        self.pattern_costs = {}
        self.max_rolls = 0
        self.regular_plan_cost = 0.0
        self.penalty_pattern_cost = 0.0
        
        # Solution results
        self.solution = None
        self.emergency_supply = 0.0
        self.objective_value = None
    
    def load_data(self):
        """
        Load all data files
        
        Read item demands, cutting patterns, and capacity parameters from CSV files
        """
        print("Loading data...")
        
        # 1. Load item demand information
        items_path = os.path.join(self.data_folder, 'items.csv')
        if not os.path.exists(items_path):
            raise FileNotFoundError(f"File not found: {items_path}")
        
        items_df = pd.read_csv(items_path)
        self.items = items_df['item_id'].tolist()
        
        for _, row in items_df.iterrows():
            self.demands[row['item_id']] = float(row['demand'])
        
        print(f"  ✓ Number of item types: {len(self.items)}")
        print(f"  ✓ Total demand: {sum(self.demands.values()):.2f}")
        
        # 2. Load cutting pattern information
        patterns_path = os.path.join(self.data_folder, 'patterns.csv')
        if not os.path.exists(patterns_path):
            raise FileNotFoundError(f"File not found: {patterns_path}")
        
        patterns_df = pd.read_csv(patterns_path)
        self.patterns = patterns_df['pattern_id'].tolist()
        
        # Extract production amount for each pattern
        for _, row in patterns_df.iterrows():
            pattern_id = row['pattern_id']
            for item_id in self.items:
                col_name = f'item_{item_id}'
                if col_name in row:
                    production = float(row[col_name])
                    self.pattern_productions[(pattern_id, item_id)] = production
                else:
                    self.pattern_productions[(pattern_id, item_id)] = 0.0
        
        print(f"  ✓ Number of cutting patterns: {len(self.patterns)}")
        
        # 3. Load parameter information
        params_path = os.path.join(self.data_folder, 'parameters.csv')
        if not os.path.exists(params_path):
            raise FileNotFoundError(f"File not found: {params_path}")
        
        params_df = pd.read_csv(params_path)
        for _, row in params_df.iterrows():
            param = row['parameter']
            value = float(row['value'])
            if param == 'R':
                self.max_rolls = int(value)
            elif param == 'regular_plan_cost':
                self.regular_plan_cost = value
            elif param == 'penalty_pattern_cost':
                self.penalty_pattern_cost = value
        
        print(f"  ✓ Max raw rolls: {self.max_rolls}")
        print(f"  ✓ Regular plan cost: {self.regular_plan_cost}")
        print(f"  ✓ Emergency supply cost: {self.penalty_pattern_cost}")
        print("Data loading completed!\n")
    
    def build_model(self):
        """
        Build optimization model
        
        Strictly corresponds to the mathematical model in mas74.md:
        - Decision variables: x_p ∈ Z+ (Lines 37-40)
        - Objective function: min Σc_p·x_p (Lines 44-52)
        - Constraint 1: Raw material capacity constraint (Lines 58-60)
        - Constraint 2: Demand satisfaction constraint (Lines 64-78)
        """
        print("Building optimization model...")
        
        # Set solver parameters
        self.model.setParam('OutputFlag', 1)  # Display solving process
        self.model.setParam('TimeLimit', 600)  # 10-minute time limit
        self.model.setParam('MIPGap', 0.01)  # 1% MIP gap
        
        # 1. Add decision variables
        print("  Adding decision variables...")
        # x_p: Whether to use pattern p
        for p in self.patterns:
            self.x[p] = self.model.addVar(
                vtype=GRB.BINARY,
                name=f"x_{p}"
            )
            
        # z: Emergency supply quantity
        self.z = self.model.addVar(
            vtype=GRB.CONTINUOUS,
            lb=0,
            name="z"
        )
        
        self.model.update()
        print(f"    - Number of binary variables: {len(self.x)}")
        print(f"    - Number of continuous variables: 1")
        
        # 2. Set objective function (corresponding to mas74.md Lines 44-52)
        self.set_objective()
        
        # 3. Add constraints
        self.add_constraints()
        
        print("Model building completed!\n")
    
    def set_objective(self):
        """
        Set objective function
        
        Objective function: min Z = regular_cost * Σ x_p + penalty_cost * z
        """
        print("  Setting objective function...")
        
        obj = gp.LinExpr()
        
        # Regular plan cost
        for p in self.patterns:
            obj += self.regular_plan_cost * self.x[p]
            
        # Emergency supply cost
        obj += self.penalty_pattern_cost * self.z
        
        self.model.setObjective(obj, GRB.MINIMIZE)
        print("    - Objective: Minimize total cost (regular + emergency)")
    
    def add_constraints(self):
        """
        Add all constraints (corresponding to mas74.md Lines 56-81)
        """
        print("  Adding constraints...")
        
        # Constraint 1: Raw material capacity constraint (corresponding to mas74.md Lines 58-60)
        # Σ_{p=1}^{150} x_p ≤ R (R = 20)
        self.model.addConstr(
            gp.quicksum(self.x[p] for p in self.patterns) <= self.max_rolls,
            name="capacity_constraint"
        )
        print(f"    - Raw material capacity constraint: 1")
        
        # Constraint 2: Demand satisfaction constraint (corresponding to mas74.md Lines 64-78)
        # For each item i: Σ_{p=1}^{150} a_{p,i} · x_p ≥ d_i
        demand_constraints = 0
        for i in self.items:
            demand = self.demands[i]
            
            # Collect production of item i from all patterns
            production_expr = gp.LinExpr()
            for p in self.patterns:
                production = self.pattern_productions.get((p, i), 0.0)
                if production > 0:
                    production_expr += production * self.x[p]
            
            # Add emergency supply (z replenishes all items)
            production_expr += self.z
            
            self.model.addConstr(
                production_expr >= demand,
                name=f"demand_item_{i}"
            )
            demand_constraints += 1
        
        print(f"    - Demand satisfaction constraints: {demand_constraints}")
        
        # Constraint 3: Non-negative integer constraint (corresponding to mas74.md Lines 81-83)
        # x_p ∈ Z+, ∀p (Set during variable definition)
        
        print(f"    - Total constraints: {self.model.NumConstrs}")
        print(f"    - Total variables: {self.model.NumVars}")
    
    def solve(self) -> bool:
        """
        Solve model
        
        Returns:
            True if solution found (optimal or feasible), False if infeasible
        """
        print("="*60)
        print("Starting solve...")
        print("="*60)
        
        # Export model for debugging
        self.model.write("debug.lp")
        print("Model exported to debug.lp")
        
        self.model.optimize()
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"\n✓ Optimal solution found!")
            print(f"  Objective value: {self.model.ObjVal:.6f}")
            print(f"  Solve time: {self.model.Runtime:.2f} seconds")
            self.objective_value = self.model.ObjVal
            self.extract_solution()
            return True
        
        elif self.model.Status == GRB.TIME_LIMIT:
            if self.model.SolCount > 0:
                print(f"\n⚠ Time limit reached, but found feasible solution")
                print(f"  Current best value: {self.model.ObjVal:.6f}")
                print(f"  MIP Gap: {self.model.MIPGap*100:.2f}%")
                self.objective_value = self.model.ObjVal
                self.extract_solution()
                return True
            else:
                print(f"\n⚠ Time limit reached, no feasible solution found")
                return False
        
        elif self.model.Status == GRB.INFEASIBLE:
            print(f"\n✗ Problem infeasible")
            print("  Attempting to compute IIS...")
            try:
                self.model.computeIIS()
                print("  Infeasible constraints:")
                for c in self.model.getConstrs():
                    if c.IISConstr:
                        print(f"    - {c.ConstrName}")
            except:
                print("  Cannot compute IIS")
            return False
        
        else:
            print(f"\n✗ Solve status: {self.model.Status}")
            return False
    
    def extract_solution(self):
        """Extract solution results"""
        if self.model.Status not in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
            return
        
        self.solution = {}
        for p in self.patterns:
            value = self.x[p].X
            if value > 0.5:  # Only record selected patterns
                self.solution[p] = 1
        
        self.emergency_supply = self.z.X
        
        self.emergency_supply = self.z.X
    
    def print_solution(self):
        """Print solution summary"""
        if self.solution is None:
            print("No solution to display")
            return
        
        print("\n" + "="*60)
        print("Solution Summary")
        print("="*60)
        
        # Calculate used raw material quantity
        total_rolls = sum(self.solution.values())
        print(f"\nTotal raw rolls used: {total_rolls} rolls (Max allowed: {self.max_rolls} rolls)")
        print(f"Number of different patterns used: {len(self.solution)} (Total {len(self.patterns)} available)")
        
        # Display used patterns
        print(f"\nUsed cutting patterns:")
        for p, count in sorted(self.solution.items(), key=lambda x: -x[1])[:10]:
            print(f"  Pattern {p}: {count} rolls")
            # Display items cut by this pattern
            productions = []
            for i in self.items:
                prod = self.pattern_productions.get((p, i), 0.0)
                if prod > 0:
                    productions.append(f"Item{i}:{prod:.1f}")
            if productions:
                print(f"    Output: {', '.join(productions[:5])}")
        
        if len(self.solution) > 10:
            print(f"  ... and {len(self.solution)-10} more patterns")
        
        # Display emergency supply
        if self.emergency_supply > 1e-6:
            print(f"\nEmergency supply (z): {self.emergency_supply:.2f}")
            print("  (Each unit of emergency supply provides 1 unit of supply for all items)")
        else:
            print(f"\nNo emergency supply")
            
        # Verify demand satisfaction
        print(f"\nDemand satisfaction status:")
        all_satisfied = True
        for i in self.items:
            demand = self.demands[i]
            actual_production = sum(
                self.pattern_productions.get((p, i), 0.0) * count
                for p, count in self.solution.items()
            )
            total_supply = actual_production + self.emergency_supply
            
            satisfied = total_supply >= demand - 1e-5
            status = "✓" if satisfied else "✗"
            print(f"  {status} Item {i}: Demand {demand:.2f}, Production {actual_production:.2f}, Emergency {self.emergency_supply:.2f}")
            if not satisfied:
                all_satisfied = False
        
        if all_satisfied:
            print(f"\n✓ All demands satisfied!")
        else:
            print(f"\n⚠ Unmet demands exist")
    
    def save_results(self, output_file: str = 'solution.txt'):
        """
        Save detailed results to file
        
        Args:
            output_file: Output filename
        """
        if self.solution is None:
            print("No solution to save")
            return
        
        output_path = os.path.join(self.data_folder, output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Cutting Stock Problem Solution Results\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Objective value: {self.objective_value:.6f}\n")
            f.write(f"Total raw rolls used: {sum(self.solution.values())} rolls\n")
            f.write(f"Number of different patterns used: {len(self.solution)}\n\n")
            
            f.write("Used cutting patterns:\n")
            f.write("-"*60 + "\n")
            for p, count in sorted(self.solution.items()):
                f.write(f"\nPattern {p}: {count} rolls\n")
                for i in self.items:
                    prod = self.pattern_productions.get((p, i), 0.0)
                    if prod > 0:
                        f.write(f"  Item {i}: {prod:.2f}\n")
            
            if self.emergency_supply > 1e-6:
                f.write(f"\nEmergency supply (z): {self.emergency_supply:.2f}\n")
            
            f.write("\n" + "="*60 + "\n")
            f.write("Demand satisfaction status:\n")
            f.write("-"*60 + "\n")
            for i in self.items:
                demand = self.demands[i]
                actual = sum(
                    self.pattern_productions.get((p, i), 0.0) * count
                    for p, count in self.solution.items()
                )
                total = actual + self.emergency_supply
                f.write(f"Item {i}: Demand {demand:.2f}, Production {actual:.2f}, Emergency {self.emergency_supply:.2f}, "
                       f"Diff {total-demand:.2f}\n")
        
        print(f"\nResults saved to: {output_path}")
    
    def get_solution_summary(self) -> Dict:
        """
        Get solution summary
        
        Returns:
            Dictionary containing key metrics
        """
        if self.solution is None:
            return {}
        
        return {
            'objective_value': self.objective_value,
            'total_rolls_used': sum(self.solution.values()),
            'max_rolls_allowed': self.max_rolls,
            'num_patterns_used': len(self.solution),
            'total_patterns_available': len(self.patterns),
            'utilization_rate': sum(self.solution.values()) / self.max_rolls,
            'emergency_supply': self.emergency_supply,
            'total_emergency_cost': self.emergency_supply * self.penalty_pattern_cost
        }


def main():
    """Main function: Demonstrate how to use the solver"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python solver.py <data_folder>")
        print("Example: python solver.py data_small")
        sys.exit(1)
    
    data_folder = sys.argv[1]
    
    if not os.path.exists(data_folder):
        print(f"Error: Data folder does not exist: {data_folder}")
        sys.exit(1)
    
    try:
        # Create solver
        solver = CuttingStockSolver(data_folder)
        
        # Load data
        solver.load_data()
        
        # Build model
        solver.build_model()
        
        # Solve
        success = solver.solve()
        
        if success:
            # Display results
            solver.print_solution()
            
            # Save results
            solver.save_results()
            
            # Get summary
            summary = solver.get_solution_summary()
            print(f"\nSolution summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
        else:
            print("\nSolve failed")
            sys.exit(1)
    
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()