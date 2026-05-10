"""
Square tiling problem solver (Square37)
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
import sys


class SquareTilingSolver:
    def __init__(self, instance_folder: str):
        self.instance_folder = instance_folder
        self.model = gp.Model("SquareTiling")
        self.grid_size = 0
        self.x = {}
        self.solution = None
        self.objective_value = None
    
    def load_data(self):
        print("Loading data...")
        
        json_path = os.path.join(self.instance_folder, 'instance.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        params = config.get('parameters', {})
        self.grid_size = int(params.get('courtyard_side', 0))
        
        # Key insight: all sizes from 1 to n-1 are available
        # The CSV only shows samples, not the complete list
        self.block_sizes = list(range(1, self.grid_size))
        
        print(f"  ✓ Courtyard size: {self.grid_size} × {self.grid_size}")
        print(f"  ✓ Inferred available sizes: 1 ~ {self.grid_size - 1}")
        print("Data loading completed!\n")
    
    def build_model(self):
        print("Building optimization model...")
        
        self.model.setParam('OutputFlag', 1)
        self.model.setParam('TimeLimit', 3600)
        self.model.setParam('MIPGap', 0.0001)
        
        n = self.grid_size
        
        print("  Adding decision variables...")
        valid_count = 0
        for s in self.block_sizes:
            max_pos = n - s + 1
            for i in range(1, max_pos + 1):
                for j in range(1, max_pos + 1):
                    self.x[i, j, s] = self.model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}_{s}")
                    valid_count += 1
        
        self.model.update()
        print(f"    - Valid placement variables: {valid_count}")
        
        obj = gp.quicksum(self.x[i, j, s] for (i, j, s) in self.x.keys())
        self.model.setObjective(obj, GRB.MINIMIZE)
        
        print("  Adding covering constraints...")
        for r in range(1, n + 1):
            for c in range(1, n + 1):
                covering = []
                for s in self.block_sizes:
                    for i in range(max(1, r - s + 1), min(r, n - s + 1) + 1):
                        for j in range(max(1, c - s + 1), min(c, n - s + 1) + 1):
                            if (i, j, s) in self.x:
                                covering.append(self.x[i, j, s])
                if covering:
                    self.model.addConstr(gp.quicksum(covering) == 1)
        
        print(f"    - Number of constraints: {self.model.NumConstrs}")
        print("Model building completed!\n")
    
    def solve(self) -> bool:
        print("=" * 60)
        print("Starting to solve...")
        print("=" * 60)
        
        self.model.optimize()
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"\n✓ Optimal solution found: {int(self.model.ObjVal)}")
            self.objective_value = self.model.ObjVal
            self.solution = [(i,j,s) for (i,j,s),v in self.x.items() if v.X > 0.5]
            return True
        elif self.model.Status == GRB.TIME_LIMIT and self.model.SolCount > 0:
            print(f"\n⚠ Time limit reached, current solution: {int(self.model.ObjVal)}")
            self.objective_value = self.model.ObjVal
            return True
        return False
    
    def print_solution(self):
        if not self.solution:
            return
        print(f"\nTiles used: {len(self.solution)}")
        sizes = {}
        for (i,j,s) in self.solution:
            sizes[s] = sizes.get(s, 0) + 1
        for s in sorted(sizes.keys(), reverse=True):
            print(f"  Size {s}: {sizes[s]}")


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    solver = SquareTilingSolver(folder)
    solver.load_data()
    solver.build_model()
    if solver.solve():
        solver.print_solution()


if __name__ == "__main__":
    main()