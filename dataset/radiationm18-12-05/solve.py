"""
IMRT Solver - Simplified Q-Variable Formulation
Based on instance.json and data/*.csv only

Uses Q[i,j,b] variables to represent segment coverage
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import sys


class IMRTSimplifiedSolver:
    """
    IMRT Solver using simplified Q-variable formulation
    
    Variables:
    - Q[i,j,b]: How many segments at intensity b expose cell (i,j)
    - N_b[b]: Number of segments at intensity b
    """
    
    def __init__(self, data_folder='data'):
        script_dir = os.path.dirname(os.path.abspath(__file__))  # Get the absolute path of the script
        self.data_folder = os.path.join(script_dir, data_folder)  # Join the data folder with script directory
        self.model = gp.Model("IMRT_Simplified")
        
        # Data
        self.intensity_map = {}
        self.num_rows = 0
        self.num_cols = 0
        self.max_intensity = 0
        
        # Decision variables
        self.Q = {}
        self.N_b = {}
        self.Beamtime = None
        self.K = None
        
        # Solution
        self.objective_value = None
    
    def load_data(self):
        """Load data files"""
        print("Loading data...")
        
        # Load parameters
        params_df = pd.read_csv(os.path.join(self.data_folder, 'parameters.csv'))
        for _, row in params_df.iterrows():
            if row['parameter'] == 'num_rows':
                self.num_rows = int(row['value'])
            elif row['parameter'] == 'num_cols':
                self.num_cols = int(row['value'])
            elif row['parameter'] == 'max_intensity':
                self.max_intensity = int(row['value'])
        
        print(f"  Grid: {self.num_rows} x {self.num_cols}")
        print(f"  Max intensity: {self.max_intensity}")
        
        # Load intensity requirements
        intensity_df = pd.read_csv(os.path.join(self.data_folder, 'intensity.csv'))
        for _, row in intensity_df.iterrows():
            i, j = int(row['row']), int(row['col'])
            self.intensity_map[(i, j)] = int(row['required_intensity'])
        
        print(f"  Loaded {len(self.intensity_map)} cell requirements")
        print("Data loading complete!\n")
    
    def build_model(self):
        """Build optimization model"""
        print("Building optimization model...")
        
        self.model.setParam('OutputFlag', 1)
        self.model.setParam('TimeLimit', 600)
        self.model.setParam('MIPGap', 0.001)
        
        # 1. Q variables: how many segments at intensity b expose cell (i,j)
        print("  Adding Q variables...")
        for i in range(1, self.num_rows + 1):
            for j in range(1, self.num_cols + 1):
                for b in range(1, self.max_intensity + 1):
                    self.Q[i, j, b] = self.model.addVar(
                        vtype=GRB.INTEGER,
                        lb=0,
                        ub=self.max_intensity,
                        name=f"Q_{i}_{j}_{b}"
                    )
        
        # 2. N_b variables: number of segments at each intensity
        print("  Adding N_b variables...")
        for b in range(1, self.max_intensity + 1):
            self.N_b[b] = self.model.addVar(
                vtype=GRB.INTEGER,
                lb=0,
                ub=100,  # Relaxed bound (was max_intensity)
                name=f"N_{b}"
            )
        
        # 3. Beamtime and K
        self.Beamtime = self.model.addVar(vtype=GRB.INTEGER, lb=0, name="Beamtime")
        self.K = self.model.addVar(vtype=GRB.INTEGER, lb=0, name="K")
        
        self.model.update()
        print(f"    Total variables: {self.model.NumVars}")
        
        # Set objective
        self.set_objective()
        
        # Add constraints
        self.add_constraints()
        
        print("Model building complete!\n")
    
    def set_objective(self):
        """Set objective: minimize 325*Beamtime + K"""
        print("  Setting objective...")
        weight = self.num_rows * self.num_cols + 1  # 325
        self.model.setObjective(weight * self.Beamtime + self.K, GRB.MINIMIZE)
        print(f"    Objective: {weight} * Beamtime + K")
    
    def add_constraints(self):
        """Add all constraints"""
        print("  Adding constraints...")
        
        # 1. Intensity matching: sum of (b * Q[i,j,b]) = required_intensity[i,j]
        print("    Adding intensity matching constraints...")
        for (i, j), req_intensity in self.intensity_map.items():
            self.model.addConstr(
                gp.quicksum(b * self.Q[i, j, b] for b in range(1, self.max_intensity + 1))
                == req_intensity,
                name=f"intensity_{i}_{j}"
            )
        
        # 2. Consecutive-ones: Q[i,j,b] <= N_b[b] for all cells
        print("    Adding segment count constraints...")
        for i in range(1, self.num_rows + 1):
            for j in range(1, self.num_cols + 1):
                for b in range(1, self.max_intensity + 1):
                    self.model.addConstr(
                        self.Q[i, j, b] <= self.N_b[b],
                        name=f"Q_bound_{i}_{j}_{b}"
                    )
        
        # 3. Segment counting: N_b[b] = sum over rows of (number of segments at intensity b)
        # Number of segments in row i at intensity b = sum_j max(0, Q[i,j,b] - Q[i,j-1,b])
        print("    Adding segment counting constraints...")
        
        # Create p variables: p[i,j,b] >= Q[i,j,b] - Q[i,j-1,b] and p >= 0
        self.p = {}
        for i in range(1, self.num_rows + 1):
            for b in range(1, self.max_intensity + 1):
                for j in range(1, self.num_cols + 1):
                    self.p[i, j, b] = self.model.addVar(
                        vtype=GRB.INTEGER, # p is integer because Q is integer
                        lb=0,
                        name=f"p_{i}_{j}_{b}"
                    )
                    
                    # Q[i,0,b] is 0
                    q_prev = self.Q[i, j-1, b] if j > 1 else 0
                    q_curr = self.Q[i, j, b]
                    
                    self.model.addConstr(self.p[i, j, b] >= q_curr - q_prev)
        
        # Link N_b to p
        # N_b[b] >= number of segments in row i = sum_j p[i,j,b]
        # Since we minimize N_b, this acts as N_b = max_i (segments in row i)
        for b in range(1, self.max_intensity + 1):
            for i in range(1, self.num_rows + 1):
                self.model.addConstr(
                    self.N_b[b] >= gp.quicksum(
                        self.p[i, j, b] 
                        for j in range(1, self.num_cols + 1)
                    ),
                    name=f"Nb_bound_{b}_{i}"
                )
        
        # 4. Beamtime definition
        print("    Adding Beamtime definition...")
        self.model.addConstr(
            self.Beamtime == gp.quicksum(
                b * self.N_b[b] for b in range(1, self.max_intensity + 1)
            ),
            name="beamtime_def"
        )
        
        # 5. K definition
        print("    Adding K definition...")
        self.model.addConstr(
            self.K == gp.quicksum(self.N_b[b] for b in range(1, self.max_intensity + 1)),
            name="K_def"
        )
        
        print(f"    Total constraints: {self.model.NumConstrs}")
    
    def solve(self):
        """Solve the model"""
        print("=" * 70)
        print("Solving...")
        print("=" * 70)
        
        self.model.optimize()
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"\nOptimal solution found!")
            print(f"  Objective: {self.model.ObjVal:.0f}")
            print(f"  Solve time: {self.model.Runtime:.2f} seconds")
            self.objective_value = self.model.ObjVal
            self.print_solution()
            return True
        elif self.model.Status == GRB.TIME_LIMIT:
            if self.model.SolCount > 0:
                print(f"\nTime limit, found solution")
                print(f"  Best objective: {self.model.ObjVal:.0f}")
                self.objective_value = self.model.ObjVal
                self.print_solution()
                return True
        else:
            print(f"\nSolve failed: Status = {self.model.Status}")
            return False
    
    def print_solution(self):
        """Print solution details"""
        beamtime = int(round(self.Beamtime.X))
        k = int(round(self.K.X))
        
        print(f"\n  Beamtime = {beamtime}")
        print(f"  K = {k}")
        
        print(f"\n  Segments by intensity:")
        for b in range(1, self.max_intensity + 1):
            nb = int(round(self.N_b[b].X))
            if nb > 0:
                contrib = b * nb
                print(f"    Intensity {b:2d}: {nb:2d} segments (contributes {contrib:3d} to beamtime)")


def main():
    """Main execution"""
    data_folder = sys.argv[1] if len(sys.argv) > 1 else 'data'
    
    try:
        solver = IMRTSimplifiedSolver(data_folder)
        solver.load_data()
        solver.build_model()
        success = solver.solve()
        
        if success:
            expected = 17574
            if abs(solver.objective_value - expected) < 0.5:
                print(f"\n" + "=" * 70)
                print(f"SUCCESS: Achieved expected value {expected}!")
                print("=" * 70)
            else:
                print(f"\nObjective {solver.objective_value:.0f} vs expected {expected}")
    
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
