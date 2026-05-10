"""
Graph Drawing Solver

Solves the Graph Drawing (Phase 1) optimization problem using Gurobi.
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
import sys
from typing import Dict, List, Optional

class GraphDrawSolver:
    """
    Graph Drawing Solver
    """
    
    def __init__(self, instance_dir: str = '.'):
        """
        Initialize solver
        """
        self.instance_dir = instance_dir
        self.model = gp.Model("GraphDraw")
        
        # Data
        self.entities_df = None
        self.edges_df = None
        self.pairs_df = None
        self.params_df = None
        self.parameters = {}
        self.optimal_value = None
        
        # Model components
        self.row_vars = {}
        self.col_vars = {}
        self.z_vars = {} # (pair_id, type) -> var
        self.d_vars = {} # (edge_id, axis) -> var
        self.c_vars = {} # (entity_id, axis) -> var
        
    def load_data(self):
        """Load data from CSV and JSON files"""
        print(f"Loading data from {self.instance_dir}...")
        
        # 1. Load instance.json
        json_path = os.path.join(self.instance_dir, 'instance.json')
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                instance_data = json.load(f)
                self.parameters = instance_data.get('parameters', {})
                self.optimal_value = instance_data.get('optimal_value')
                print(f"  ✓ Loaded instance.json")
        else:
            print(f"  ⚠ instance.json not found at {json_path}")
            
        # 2. Load CSVs
        data_dir = os.path.join(self.instance_dir, 'data')
        self.entities_df = pd.read_csv(os.path.join(data_dir, 'entities.csv'))
        self.edges_df = pd.read_csv(os.path.join(data_dir, 'edges.csv'))
        self.pairs_df = pd.read_csv(os.path.join(data_dir, 'pairs.csv'))
        self.params_df = pd.read_csv(os.path.join(data_dir, 'edge_distance_params.csv'))
        
        print(f"  ✓ Loaded entities ({len(self.entities_df)})")
        print(f"  ✓ Loaded edges ({len(self.edges_df)})")
        print(f"  ✓ Loaded pairs ({len(self.pairs_df)})")
        
    def build_model(self):
        """Build the optimization model"""
        print("Building model...")
        
        # Parameters
        # edge_weight = float(self.parameters.get('edge_weight', 1.0)) # Not used, weights in CSV
        center_weight = float(self.parameters.get('center_weight', 1.0))
        center_sum_lb = float(self.parameters.get('center_sum_lb', 0.0))
        
        # 1. Entity Placement Variables
        for _, row in self.entities_df.iterrows():
            eid = row['entity_id']
            self.row_vars[eid] = self.model.addVar(lb=row['row_min'], ub=row['row_max'], vtype=GRB.INTEGER, name=f"row_{eid}")
            self.col_vars[eid] = self.model.addVar(lb=row['col_min'], ub=row['col_max'], vtype=GRB.INTEGER, name=f"col_{eid}")
            
            # Anchor deviation variables
            self.c_vars[(eid, 'row')] = self.model.addVar(lb=0, name=f"c_row_{eid}")
            self.c_vars[(eid, 'col')] = self.model.addVar(lb=0, name=f"c_col_{eid}")
            
            # Anchor constraints
            # c >= pos - anchor  =>  c - pos >= -anchor
            # c >= anchor - pos  =>  c + pos >= anchor
            self.model.addConstr(self.c_vars[(eid, 'row')] >= self.row_vars[eid] - row['anchor_row'])
            self.model.addConstr(self.c_vars[(eid, 'row')] >= row['anchor_row'] - self.row_vars[eid])
            self.model.addConstr(self.c_vars[(eid, 'col')] >= self.col_vars[eid] - row['anchor_col'])
            self.model.addConstr(self.c_vars[(eid, 'col')] >= row['anchor_col'] - self.col_vars[eid])
            
        # Total anchor deviation lower bound
        self.model.addConstr(gp.quicksum(self.c_vars.values()) >= center_sum_lb, name="center_sum_lb")
        
        # 2. Pair Selection Variables and Constraints
        # Map (u, v) -> (pair_id, is_u_before_v_in_pair_def)
        pair_map = {} 
        
        for _, row in self.pairs_df.iterrows():
            pid = row['pair_id']
            i_id = row['i_id']
            j_id = row['j_id']
            
            pair_map[(i_id, j_id)] = (pid, True)
            pair_map[(j_id, i_id)] = (pid, False)
            
            # 4 options: row_i_j (i before j), row_j_i, col_i_j, col_j_i
            z_rij = self.model.addVar(vtype=GRB.BINARY, name=f"z_row_{i_id}_{j_id}")
            z_rji = self.model.addVar(vtype=GRB.BINARY, name=f"z_row_{j_id}_{i_id}")
            z_cij = self.model.addVar(vtype=GRB.BINARY, name=f"z_col_{i_id}_{j_id}")
            z_cji = self.model.addVar(vtype=GRB.BINARY, name=f"z_col_{j_id}_{i_id}")
            
            self.z_vars[(pid, 'row_i_j')] = z_rij
            self.z_vars[(pid, 'row_j_i')] = z_rji
            self.z_vars[(pid, 'col_i_j')] = z_cij
            self.z_vars[(pid, 'col_j_i')] = z_cji
            
            # Exactly one option chosen
            self.model.addConstr(z_rij + z_rji + z_cij + z_cji == 1, name=f"pair_select_{pid}")
            
            # Separation constraints (Indicator constraints)
            # If row_i_j selected, row_j - row_i >= gap
            self.model.addGenConstrIndicator(z_rij, 1, self.row_vars[j_id] - self.row_vars[i_id] >= row['row_gap_i_before_j'])
            self.model.addGenConstrIndicator(z_rji, 1, self.row_vars[i_id] - self.row_vars[j_id] >= row['row_gap_j_before_i'])
            self.model.addGenConstrIndicator(z_cij, 1, self.col_vars[j_id] - self.col_vars[i_id] >= row['col_gap_i_before_j'])
            self.model.addGenConstrIndicator(z_cji, 1, self.col_vars[i_id] - self.col_vars[j_id] >= row['col_gap_j_before_i'])
            
        # 3. Consistency Constraints
        entities = sorted(self.entities_df['entity_id'].unique())
        
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                for k in range(j + 1, len(entities)):
                    u, v, w = entities[i], entities[j], entities[k]
                    
                    # Helper to get z_{a->b} variable for a specific axis
                    def get_z(a, b, axis):
                        pid, is_a_before_b = pair_map[(a, b)]
                        if axis == 'row':
                            key = 'row_i_j' if is_a_before_b else 'row_j_i'
                        else:
                            key = 'col_i_j' if is_a_before_b else 'col_j_i'
                        return self.z_vars[(pid, key)]

                    # Row axis consistency
                    # Cycle: u->v->w->u
                    self.model.addConstr(get_z(u, v, 'row') + get_z(v, w, 'row') + get_z(w, u, 'row') <= 2)
                    # Cycle: u->w->v->u
                    self.model.addConstr(get_z(u, w, 'row') + get_z(w, v, 'row') + get_z(v, u, 'row') <= 2)
                    
                    # Col axis consistency
                    self.model.addConstr(get_z(u, v, 'col') + get_z(v, w, 'col') + get_z(w, u, 'col') <= 2)
                    self.model.addConstr(get_z(u, w, 'col') + get_z(w, v, 'col') + get_z(v, u, 'col') <= 2)

        # 4. Edge Distances
        for _, row in self.edges_df.iterrows():
            eid = row['edge_id']
            u, v = row['u_id'], row['v_id']
            
            d_row = self.model.addVar(lb=0, name=f"d_row_{eid}")
            d_col = self.model.addVar(lb=0, name=f"d_col_{eid}")
            self.d_vars[(eid, 'row')] = d_row
            self.d_vars[(eid, 'col')] = d_col
            
            # Manhattan lower bound
            self.model.addConstr(d_row + d_col >= row['manhattan_lb'])
            
            # Linearization params
            # Get params for this edge
            edge_params = self.params_df[self.params_df['edge_id'] == eid]
            
            for _, p_row in edge_params.iterrows():
                axis = p_row['axis']
                d_var = d_row if axis == 'row' else d_col
                pos_u = self.row_vars[u] if axis == 'row' else self.col_vars[u]
                pos_v = self.row_vars[v] if axis == 'row' else self.col_vars[v]
                
                # d + (pos_v - pos_u) >= rhs1
                self.model.addConstr(d_var + pos_v - pos_u >= p_row['rhs_for_v_minus_u'])
                # d + (pos_u - pos_v) >= rhs2
                self.model.addConstr(d_var + pos_u - pos_v >= p_row['rhs_for_u_minus_v'])
                
                # Conditional min distance
                # If axis is chosen for separation, d_axis >= min_dist
                # We need to know if the pair (u,v) is separated on this axis
                pid, is_u_before_v = pair_map[(u, v)]
                
                # d_axis >= min_dist * z_axis
                # z_axis is sum of two binary vars. We add indicator for each.
                if axis == 'row':
                    self.model.addGenConstrIndicator(self.z_vars[(pid, 'row_i_j')], 1, d_var >= p_row['min_axis_distance_if_axis_chosen'])
                    self.model.addGenConstrIndicator(self.z_vars[(pid, 'row_j_i')], 1, d_var >= p_row['min_axis_distance_if_axis_chosen'])
                else:
                    self.model.addGenConstrIndicator(self.z_vars[(pid, 'col_i_j')], 1, d_var >= p_row['min_axis_distance_if_axis_chosen'])
                    self.model.addGenConstrIndicator(self.z_vars[(pid, 'col_j_i')], 1, d_var >= p_row['min_axis_distance_if_axis_chosen'])
                
                # Upper bound on distance (optional but good for tightening)
                self.model.addConstr(d_var <= p_row['distance_ub'])

        self.model.update()
        
        # Objective
        obj_expr = gp.LinExpr()
        
        # Edge weights
        for _, row in self.edges_df.iterrows():
            eid = row['edge_id']
            weight = row['weight'] # Use weight from CSV directly
            obj_expr += weight * (self.d_vars[(eid, 'row')] + self.d_vars[(eid, 'col')])
            
        # Center weights
        for _, row in self.entities_df.iterrows():
            eid = row['entity_id']
            # center_weight is global multiplier
            obj_expr += center_weight * (self.c_vars[(eid, 'row')] + self.c_vars[(eid, 'col')])
            
        self.model.setObjective(obj_expr, GRB.MINIMIZE)
        
        # Parameters
        self.model.setParam('MIPFocus', 1)
        self.model.setParam('TimeLimit', 600)
        self.model.setParam('IntegralityFocus', 1) # Avoid integer tolerance issues
        self.model.setParam('FeasibilityTol', 1e-9)
        self.model.setParam('OptimalityTol', 1e-9)
        
        print("Model built successfully.")
        
    def solve(self):
        """Solve the model"""
        print("Solving...")
        self.model.optimize()
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"\n✓ Optimal solution found!")
            obj_val = self.model.ObjVal
            print(f"  Objective Value: {obj_val}")
            
            if self.optimal_value is not None and self.optimal_value != "":
                try:
                    expected_val = float(self.optimal_value)
                    # Allow some tolerance
                    if abs(obj_val - expected_val) < 1e-2:
                        print(f"  ✓ Verified against instance.json (Matches {expected_val})")
                    else:
                        print(f"  ✗ Mismatch with instance.json (Expected {expected_val}, got {obj_val})")
                except ValueError:
                    pass
            
            return True
        else:
            print(f"\n✗ Solver ended with status {self.model.Status}")
            return False

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
    
    solver = GraphDrawSolver(instance_dir)
    try:
        solver.load_data()
        solver.build_model()
        solver.solve()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
