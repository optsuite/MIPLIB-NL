"""
Swath Solver
Solves the Radar Surveillance Plan problem using Gurobi
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
import sys

class SwathSolver:
    def __init__(self, instance_path: str = '.'):
        self.instance_path = instance_path
        self.model = gp.Model("Swath")
        self.params = {}
        self.objective_terms = {}
        self.coverage_options = {}
        self.configuration_options = {}
        self.x = {} # Action variables

    def load_data(self):
        # Use relative path from script location
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        instance_path = self.instance_path if os.path.isabs(self.instance_path) else os.path.join(script_dir, self.instance_path)
        
        # Load instance.json
        with open(os.path.join(instance_path, 'instance.json'), 'r', encoding='utf-8') as f:
            instance = json.load(f)
            self.params = instance['parameters']
        
        # Load CSVs
        data_dir = os.path.join(instance_path, 'data')
        
        obj_df = pd.read_csv(os.path.join(data_dir, 'objective_terms.csv'))
        self.objective_terms = dict(zip(obj_df['action_id'], obj_df['score_weight']))
        
        cov_df = pd.read_csv(os.path.join(data_dir, 'coverage_package_options.csv'))
        self.coverage_options = cov_df.groupby('coverage_package_id')['action_id'].apply(list).to_dict()
        
        cfg_df = pd.read_csv(os.path.join(data_dir, 'configuration_package_options.csv'))
        self.configuration_options = cfg_df.groupby('configuration_package_id')['action_id'].apply(list).to_dict()

    def build_model(self):
        p = self.params
        n_actions = int(p["N_ACTIONS"])
        
        # 1. Variables
        # Actions have different types (Quantity, Share, Commitment)
        # But for MIP, we can model them as Continuous (0 to infinity or 0 to 1) or Binary
        # Based on description:
        # Quantity: [1, 80] -> Continuous >= 0
        # Share: [81, 4498] -> Continuous [0, 1]
        # Commitment: [4499, 6804] -> Binary
        
        quantity_end = int(p["QUANTITY_ACTION_START"]) + 80 - 1 # Assuming 1-80 based on params
        share_end = int(p["SHARE_ACTION_END"])
        
        for i in range(1, n_actions + 1):
            if i <= 80: # Quantity
                self.x[i] = self.model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{i}")
            elif i <= share_end: # Share
                self.x[i] = self.model.addVar(lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name=f"x_{i}")
            else: # Commitment
                self.x[i] = self.model.addVar(vtype=GRB.BINARY, name=f"x_{i}")
        
        # 2. Objective
        obj_expr = gp.quicksum(self.x[i] * w for i, w in self.objective_terms.items())
        self.model.setObjective(obj_expr, GRB.MINIMIZE)
        
        # 3. Constraints
        
        # 3.1 Coverage Packages
        for pkg_id, options in self.coverage_options.items():
            self.model.addConstr(gp.quicksum(self.x[i] for i in options) == 1.0, name=f"Cov_{pkg_id}")
            
        # 3.2 Configuration Packages
        for pkg_id, options in self.configuration_options.items():
            self.model.addConstr(gp.quicksum(self.x[i] for i in options) == 1.0, name=f"Cfg_{pkg_id}")
            
        # 3.3 Checkpoints
        n_checkpoints = int(p["N_PATH_CHECKPOINTS"])
        checkpoints_per_lane = int(p["CHECKPOINTS_PER_LANE"])
        checkpoint_singleton_first = int(p["CHECKPOINT_SINGLETON_FIRST_ACTION_ID"])
        checkpoint_leave_first = int(p["CHECKPOINT_LEAVE_WINDOW_FIRST_ACTION_ID"])
        checkpoint_leave_step = int(p["CHECKPOINT_LEAVE_WINDOW_STEP"])
        checkpoint_leave_len = int(p["CHECKPOINT_LEAVE_WINDOW_LENGTH"])
        disabled_block_size = int(p["DISABLED_BLOCK_SIZE"])
        disabled_block_lane_shift = int(p["DISABLED_BLOCK_SHIFT_PER_LANE"])
        checkpoint_enter_ap_first = int(p["CHECKPOINT_ENTER_AP_FIRST_ACTION_ID"])
        checkpoint_enter_ap_step = int(p["CHECKPOINT_ENTER_AP_STEP"])
        checkpoint_enter_ap_len = int(p["CHECKPOINT_ENTER_AP_LENGTH"])
        checkpoint_enter_repl_base = int(p["CHECKPOINT_ENTER_REPLACEMENT_BASE_ACTION_ID"])
        checkpoint_enter_repl_step = int(p["CHECKPOINT_ENTER_REPLACEMENT_STEP"])
        
        # Track disabled actions to fix them to 0 later
        disabled_actions = set()
        
        for checkpoint_id in range(1, n_checkpoints + 1):
            checkpoint_index = checkpoint_id - 1
            lane_index = checkpoint_index // checkpoints_per_lane
            offset_in_lane = checkpoint_index % checkpoints_per_lane
            
            # Leaving side
            leave_start = checkpoint_leave_first + checkpoint_index * checkpoint_leave_step
            disabled_block_start = leave_start + lane_index * disabled_block_lane_shift
            disabled_block = set(range(disabled_block_start, disabled_block_start + disabled_block_size))
            disabled_actions.update(disabled_block)
            
            leave_expr = gp.LinExpr()
            for aid in range(leave_start, leave_start + checkpoint_leave_len):
                if aid not in disabled_block:
                    leave_expr += self.x[aid]
            
            # Entering side
            enter_expr = gp.LinExpr()
            enter_expr += self.x[checkpoint_singleton_first + checkpoint_index]
            
            ap_terms = [checkpoint_enter_ap_first + checkpoint_index + checkpoint_enter_ap_step * t for t in range(checkpoint_enter_ap_len)]
            if lane_index == 0:
                for aid in ap_terms:
                    enter_expr += self.x[aid]
            else:
                t0 = 4 * (lane_index - 1)
                t1 = 4 * lane_index - 1
                drop = set(ap_terms[t0 : t1 + 1])
                for aid in ap_terms:
                    if aid not in drop:
                        enter_expr += self.x[aid]
                repl_start = checkpoint_enter_repl_base + 4 * (lane_index - 1) + offset_in_lane
                for j in range(4):
                    enter_expr += self.x[repl_start + checkpoint_enter_repl_step * j]
            
            self.model.addConstr(leave_expr == enter_expr, name=f"Chk_{checkpoint_id}")
            
        # 3.4 Time Windows
        n_time_blocks = int(p["N_TIME_BLOCKS"])
        time_block_first = int(p["TIME_BLOCK_FIRST_ACTION_ID"])
        time_block_size = int(p["TIME_BLOCK_SIZE"])
        time_block_step = int(p["TIME_BLOCK_STEP"])
        coarse_base = int(p["TIME_WINDOW_COARSE_BASE_ACTION_ID"])
        coarse_block_count = int(p["TIME_WINDOW_COARSE_BLOCK_COUNT"])
        coarse_block_size = int(p["TIME_WINDOW_COARSE_BLOCK_SIZE"])
        coarse_block_stride = int(p["TIME_WINDOW_COARSE_BLOCK_STRIDE"])
        coarse_plus_stride = int(p["TIME_WINDOW_COARSE_PLUS_STRIDE"])
        unit_weight = float(p["UNIT_WEIGHT"])
        coarse_weight = float(p["COARSE_WEIGHT"])
        time_window_rhs = float(p["TIME_WINDOW_RHS"])

        def time_block_actions(block_id):
            start = time_block_first + (block_id - 1) * time_block_step
            return list(range(start, start + time_block_size))

        rule_id = 1
        for plus_block in range(1, n_time_blocks + 1):
            for minus_block in range(1, n_time_blocks + 1):
                if plus_block == minus_block:
                    continue
                
                expr = gp.LinExpr()
                for aid in time_block_actions(plus_block):
                    expr += unit_weight * self.x[aid]
                for aid in time_block_actions(minus_block):
                    expr -= unit_weight * self.x[aid]
                
                base = coarse_base + (minus_block - 1) * time_block_size + (plus_block - 1) * coarse_plus_stride
                for coarse_block_index in range(coarse_block_count):
                    start = base + coarse_block_index * coarse_block_stride
                    for k in range(coarse_block_size):
                        expr += coarse_weight * self.x[start + k]
                
                self.model.addConstr(expr <= time_window_rhs, name=f"TimeWin_{rule_id}")
                rule_id += 1
        
        # 3.5 Disabled Actions
        disabled_tail_start = int(p["DISABLED_TAIL_START_ACTION_ID"])
        disabled_tail_end = int(p["DISABLED_TAIL_END_ACTION_ID"])
        disabled_actions.update(range(disabled_tail_start, disabled_tail_end + 1))
        
        for aid in disabled_actions:
            self.model.addConstr(self.x[aid] == 0, name=f"Disabled_{aid}")

    def solve(self):
        self.model.setParam('OutputFlag', 1)
        self.model.optimize()
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"Optimal Objective: {self.model.ObjVal}")
            return self.model.ObjVal
        else:
            print("No optimal solution found")
            return None

if __name__ == "__main__":
    solver = SwathSolver()
    solver.load_data()
    solver.build_model()
    solver.solve()
