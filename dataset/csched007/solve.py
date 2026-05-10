"""
Cumulative Scheduling Problem Solver

Solves the cumulative scheduling problem using the Gurobi solver
"""

import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import json
import os
from typing import Dict, List, Set, Tuple
import time


class CumulativeSchedulingSolver:
    """
    Cumulative Scheduling Problem Solver
    
    Reads CSV data files and builds/solves the optimization model using Gurobi
    Implementation based on the mathematical modeling in csched007.md
    """
    
    def __init__(self, data_folder: str, time_limit: int = 300):
        """
        Initialize the solver
        
        Args:
            data_folder: Path to data folder (containing CSV and JSON files)
            time_limit: Solving time limit (seconds)
        """
        self.data_folder = data_folder
        self.time_limit = time_limit
        self.model = gp.Model("CumulativeScheduling")
        
        # Data containers (corresponding to sets in modeling document)
        self.tasks = []  # J: Set of tasks
        self.time_points = []  # T: Set of time points
        
        # Parameters (corresponding to parameters in modeling document)
        self.task_info = {}  # Task info: duration, resource_demand, release_time, deadline
        self.capacity = 0  # C: Resource capacity
        self.horizon = 0  # Time horizon
        
        # Decision variables (corresponding to decision variables in modeling document)
        self.x = {}  # x_{j,t}: Whether task j starts at time t
        self.s = {}  # s_j: Start time of task j
        self.delay = {}  # delay_j: Delay of task j
        self.z = {}  # z_t: Cumulative resource usage at time t
        
        # Solving results
        self.solution = None
        self.objective_value = None
    
    def load_data(self):
        """Load all data files"""
        print("Loading data...")
        
        # 1. Load task information
        tasks_df = pd.read_csv(os.path.join(self.data_folder, 'tasks.csv'))
        self.tasks = tasks_df['task_id'].tolist()
        
        for _, row in tasks_df.iterrows():
            task_id = row['task_id']
            self.task_info[task_id] = {
                'duration': int(row['duration']),
                'resource_demand': int(row['resource_demand']),
                'release_time': int(row['release_time']),
                'latest_start': int(row['latest_start']),
                'target_start': int(row['target_start'])
            }
        
        print(f"  ✓ Number of tasks: {len(self.tasks)}")
        
        # 2. Load global parameters
        params_df = pd.read_csv(os.path.join(self.data_folder, 'parameters.csv'))
        params_dict = dict(zip(params_df['parameter'], params_df['value']))
        
        self.capacity = int(params_dict['resource_capacity'])
        self.horizon = int(params_dict['max_time'])
        
        print(f"  ✓ Resource capacity: {self.capacity}")
        print(f"  ✓ Time horizon: 0-{self.horizon}")
        
        # 3. Build time points set
        # Time range from 0 to horizon
        min_release = min(info['release_time'] for info in self.task_info.values())
        max_deadline = max(info['latest_start'] + info['duration'] - 1 for info in self.task_info.values())
        
        # Extend time horizon to accommodate potential delays
        extended_horizon = max(self.horizon, max_deadline + 50)
        self.time_points = list(range(0, extended_horizon + 1))
        
        print(f"  ✓ Number of time points: {len(self.time_points)}")
        print("Data loading complete!\n")
    
    def build_model(self):
        """Build optimization model (strictly corresponding to csched007.md)"""
        print("Building optimization model...")
        
        # Set solver parameters
        self.model.setParam('OutputFlag', 1)
        self.model.setParam('TimeLimit', self.time_limit)
        self.model.setParam('MIPGap', 0.01)  # 1% gap
        
        # 1. Add decision variables
        self._add_variables()
        
        # 2. Set objective function
        self._set_objective()
        
        # 3. Add constraints
        self._add_constraints()
        
        print("Model building complete!\n")
        print(f"  Total variables: {self.model.NumVars}")
        print(f"  Total constraints: {self.model.NumConstrs}")
        print()
    
    def _add_variables(self):
        """Add decision variables"""
        print("  Adding decision variables...")
        
        # 1. Main decision variable x_{j,t}: whether task j starts at time t (binary variable)
        # Corresponding to decision variable 1 in modeling document
        for j in self.tasks:
            release_time = self.task_info[j]['release_time']
            latest_start = self.task_info[j]['latest_start']
            duration = self.task_info[j]['duration']
            
            # Create variables only for valid start times
            # Task can start at latest at deadline - duration
            latest_start = min(latest_start, len(self.time_points) - duration - 1)
            
            for t in range(release_time, latest_start + 1):
                self.x[j, t] = self.model.addVar(
                    vtype=GRB.BINARY,
                    name=f"x_j{j}_t{t}"
                )
        
        # 2. Start time variable s_j (integer variable)
        # Corresponding to decision variable 2 in modeling document
        for j in self.tasks:
            release_time = self.task_info[j]['release_time']
            latest_start = self.task_info[j]['latest_start']
            self.s[j] = self.model.addVar(
                vtype=GRB.INTEGER,
                lb=release_time,
                ub=latest_start,
                name=f"s_j{j}"
            )
        
        # 3. Delay variable delay_j (continuous variable, >=0)
        # Corresponding to decision variable 3 in modeling document
        for j in self.tasks:
            self.delay[j] = self.model.addVar(
                vtype=GRB.CONTINUOUS,
                lb=0.0,
                name=f"delay_j{j}"
            )
        
        # 4. Cumulative resource variable z_t (continuous variable, [0, C])
        # Corresponding to decision variable 4 in modeling document
        for t in self.time_points:
            self.z[t] = self.model.addVar(
                vtype=GRB.CONTINUOUS,
                lb=0.0,
                ub=self.capacity,
                name=f"z_t{t}"
            )
        
        self.model.update()
    
    def _set_objective(self):
        """Set objective function"""
        print("  Setting objective function...")
        
        # Objective function: Minimize total delay
        # Corresponding to objective function in modeling document (lines 52-55)
        obj = gp.LinExpr()
        
        for j in self.tasks:
            obj += self.delay[j]
        
        self.model.setObjective(obj, GRB.MINIMIZE)
    
    def _add_constraints(self):
        """Add all constraints"""
        print("  Adding constraints...")
        
        # Constraint 1: Task must start constraint
        # Corresponding to constraint 1 in modeling document (lines 60-63)
        # Σ_t x_{j,t} = 1, ∀j ∈ J
        for j in self.tasks:
            self.model.addConstr(
                gp.quicksum(self.x.get((j, t), 0) 
                           for t in self.time_points) == 1,
                name=f"task_must_start_j{j}"
            )
        
        # Constraint 2: Start time definition constraint
        # Corresponding to constraint 2 in modeling document (lines 65-68)
        # s_j = Σ_t (t · x_{j,t}), ∀j ∈ J
        for j in self.tasks:
            self.model.addConstr(
                self.s[j] == gp.quicksum(t * self.x.get((j, t), 0) 
                                        for t in self.time_points),
                name=f"start_time_def_j{j}"
            )
        
        # Constraint 3: Delay definition constraint
        # Corresponding to constraint 3 in modeling document (lines 70-73)
        # delay_j = s_j - d_j, ∀j ∈ J
        for j in self.tasks:
            target_start = self.task_info[j]['target_start']
            self.model.addConstr(
                self.delay[j] >= self.s[j] - target_start,
                name=f"delay_def_j{j}"
            )
            # Note: delay already has lb=0 constraint, so it automatically satisfies max(0, s_j - d_j)
        
        # Constraint 4: Cumulative resource constraint (initial condition)
        # Corresponding to constraint 4 in modeling document (lines 75-78)
        # z_0 = 0
        self.model.addConstr(
            self.z[0] == 0,
            name="initial_resource"
        )
        
        # Constraint 5: Cumulative resource recurrence constraint
        # Corresponding to constraint 5 in modeling document (lines 80-86)
        # z_t - z_{t-1} = Σ_j Σ_τ (r_j · x_{j,τ})
        # Where tau satisfies: tau ≤ t < tau + p_j (task is executing at time t)
        for t in range(1, len(self.time_points)):
            resource_change = gp.LinExpr()
            
            for j in self.tasks:
                duration = self.task_info[j]['duration']
                resource = self.task_info[j]['resource_demand']
                
                # Find all start times that affect resource usage at time t
                # If task starts at tau, it consumes resources during [tau, tau+duration-1]
                # So at time t, consider all starts tau in [max(0, t-duration+1), t]
                for tau in range(max(0, t - duration + 1), t + 1):
                    if (j, tau) in self.x:
                        # If task j starts at tau, it is executing at time t
                        # But we need to calculate resource change at time t relative to t-1
                        # If tau = t, task starts, resources increase
                        # If tau + duration = t, task ends, resources decrease
                        if tau == t:
                            # Task starts at time t, resources increase
                            resource_change += resource * self.x[j, tau]
                        if tau + duration == t:
                            # Task ends at time t, resources decrease
                            resource_change -= resource * self.x[j, tau]
            
            self.model.addConstr(
                self.z[t] - self.z[t-1] == resource_change,
                name=f"resource_balance_t{t}"
            )
        
        # Constraint 6: Resource capacity upper limit constraint
        # Corresponding to constraint 6 in modeling document (lines 88-91)
        # z_t ≤ C, ∀t ∈ T
        # Note: This constraint is already automatically satisfied by the variable upper bound ub=self.capacity
        # But for clarity, we still add it
        for t in self.time_points:
            self.model.addConstr(
                self.z[t] <= self.capacity,
                name=f"capacity_limit_t{t}"
            )
    
    def solve(self) -> bool:
        """Solve the model"""
        print("="*60)
        print("Starting solve...")
        print("="*60)
        print()
        
        start_time = time.time()
        self.model.optimize()
        solve_time = time.time() - start_time
        
        if self.model.Status == GRB.OPTIMAL:
            print(f"\n✓ Optimal solution found!")
            print(f"  Objective value (total delay): {self.model.ObjVal:.2f}")
            print(f"  Solve time: {solve_time:.2f} seconds")
            self.objective_value = self.model.ObjVal
            return True
        elif self.model.Status == GRB.TIME_LIMIT:
            if self.model.SolCount > 0:
                print(f"\n⚠ Time limit reached (feasible solution found)")
                print(f"  Current best value: {self.model.ObjVal:.2f}")
                print(f"  Optimality gap: {self.model.MIPGap*100:.2f}%")
                self.objective_value = self.model.ObjVal
                return True
            else:
                print(f"\n⚠ Time limit reached (no feasible solution found)")
                return False
        elif self.model.Status == GRB.INFEASIBLE:
            print(f"\n✗ Problem is infeasible")
            print("  Computing IIS (Irreducible Inconsistent Subsystem)...")
            self.model.computeIIS()
            print("  Infeasible constraints:")
            for c in self.model.getConstrs():
                if c.IISConstr:
                    print(f"    - {c.ConstrName}")
            return False
        else:
            print(f"\n✗ Solve status: {self.model.Status}")
            return False
    
    def print_solution(self):
        """Print solution summary"""
        if self.model.Status not in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
            return
        
        if self.model.SolCount == 0:
            return
        
        print("\n" + "="*60)
        print("Solution Summary")
        print("="*60)
        
        # Extract solution
        schedule = []
        total_delay = 0
        on_time_tasks = 0
        delayed_tasks = 0
        
        for j in self.tasks:
            start_time = self.s[j].X
            delay = self.delay[j].X
            duration = self.task_info[j]['duration']
            deadline = self.task_info[j]['target_start']
            completion_time = start_time + duration
            
            schedule.append({
                'task_id': j,
                'start_time': int(start_time),
                'duration': duration,
                'completion_time': int(completion_time),
                'target_start': deadline,
                'delay': delay
            })
            
            total_delay += delay
            if delay < 0.01:
                on_time_tasks += 1
            else:
                delayed_tasks += 1
        
        # Sort by start time
        schedule.sort(key=lambda x: x['start_time'])
        
        # Statistics
        print(f"\nTotal delay: {total_delay:.2f}")
        print(f"Tasks completed on time: {on_time_tasks}/{len(self.tasks)}")
        print(f"Delayed tasks: {delayed_tasks}/{len(self.tasks)}")
        
        if delayed_tasks > 0:
            avg_delay = total_delay / delayed_tasks
            max_delay = max(s['delay'] for s in schedule)
            print(f"Average delay (delayed tasks only): {avg_delay:.2f}")
            print(f"Max delay: {max_delay:.2f}")
        
        # Print partial schedule
        print(f"\nSchedule (first 20 tasks):")
        print(f"{'Task':<8} {'Start':<8} {'Dur':<8} {'End':<8} {'Due':<8} {'Delay':<8}")
        print("-" * 60)
        
        for s in schedule[:20]:
            print(f"{s['task_id']:<8} {s['start_time']:<8} {s['duration']:<8} "
                  f"{s['completion_time']:<8} {s['target_start']:<8} {s['delay']:<8.1f}")
        
        if len(schedule) > 20:
            print(f"... and {len(schedule) - 20} more tasks")
        
        # Resource usage
        print(f"\nResource usage:")
        max_resource_usage = max(self.z[t].X for t in self.time_points)
        print(f"  Max resource usage: {max_resource_usage:.2f} / {self.capacity}")
        print(f"  Resource utilization: {max_resource_usage / self.capacity * 100:.1f}%")
        
        self.solution = schedule
    
    def save_results(self, output_file: str = 'solution.csv'):
        """Save detailed results to file"""
        if self.solution is None:
            print("No solution to save")
            return
        
        # Save schedule
        solution_df = pd.DataFrame(self.solution)
        solution_path = os.path.join(self.data_folder, output_file)
        solution_df.to_csv(solution_path, index=False, encoding='utf-8')
        print(f"\nSolution saved to: {solution_path}")


def main():
    """Main function: Demonstrate solver usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python solver.py <data_folder>")
        print("Example: python solver.py data_small")
        sys.exit(1)
    
    data_folder = sys.argv[1]
    
    if not os.path.exists(data_folder):
        print(f"Error: Data folder does not exist: {data_folder}")
        sys.exit(1)
    
    # Create solver
    solver = CumulativeSchedulingSolver(data_folder, time_limit=300)
    
    # Load data
    solver.load_data()
    
    # Build model
    solver.build_model()
    
    # Solve
    success = solver.solve()
    
    if success:
        # Print results
        solver.print_solution()
        
        # Save results
        solver.save_results()


if __name__ == "__main__":
    main()