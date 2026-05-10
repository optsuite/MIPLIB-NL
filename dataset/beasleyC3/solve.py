import csv
import os
import gurobipy as gp
from gurobipy import GRB
import sys

class FixedChargeNetworkSolver:
    """Fixed-Charge Network Flow Problem Solver"""

    def __init__(self, data_dir: str = 'data/'):
        """
        Initialize the solver with data directory

        Args:
            data_dir: Directory containing CSV data files
        """
        self.data_dir = data_dir
        self.model = None
        self.x_vars = {}
        self.y_vars = {}
        self.load_data()

    def load_data(self):
        """Load data from CSV files"""
        try:
            # Load parameters
            with open(f'{self.data_dir}/parameter.csv', 'r') as f:
                reader = csv.DictReader(f)
                self.params = {row['parameter']: float(row['value']) for row in reader}

            # Load arcs
            with open(f'{self.data_dir}/arcs.csv', 'r') as f:
                reader = csv.DictReader(f)
                self.arcs = list(reader)

            # Load costs
            with open(f'{self.data_dir}/costs.csv', 'r') as f:
                reader = csv.DictReader(f)
                self.costs = list(reader)

            # Load flow balance
            with open(f'{self.data_dir}/flow_balance.csv', 'r') as f:
                reader = csv.DictReader(f)
                self.flow_balance = list(reader)

            print(f"Loaded {len(self.arcs)} arcs, {len(self.costs)} costs, {len(self.flow_balance)} flow constraints")

        except FileNotFoundError as e:
            print(f"Error: Data file not found - {e}")
            print("Please run generator.py first to generate the data files.")
            sys.exit(1)

    def build_model(self):
        """Build the optimization model"""
        # Create model
        self.model = gp.Model("FixedChargeNetworkFlow")

        # Create variables (FINAL CORRECTION: x is continuous, y is binary)
        print("Creating variables...")
        for cost in self.costs:
            x_var = self.model.addVar(
                lb=0,
                ub=self.params['capacity_per_arc'],
                vtype=GRB.CONTINUOUS,
                name=cost['x_var']
            )
            y_var = self.model.addVar(
                vtype=GRB.BINARY,
                name=cost['y_var']
            )
            self.x_vars[cost['x_var']] = x_var
            self.y_vars[cost['y_var']] = y_var

        print(f"Created {len(self.x_vars)} continuous variables and {len(self.y_vars)} binary variables")

        # Set objective: minimize fixed costs (y variables)
        print("Setting objective...")
        objective = gp.LinExpr()
        for cost in self.costs:
            fixed_cost = float(cost['fixed_cost'])
            objective += fixed_cost * self.y_vars[cost['y_var']]

        self.model.setObjective(objective, GRB.MINIMIZE)

        # Add capacity constraints: x_i <= capacity * y_i (FINAL CORRECTION)
        print("Adding capacity constraints...")
        for cost in self.costs:
            x_var = self.x_vars[cost['x_var']]  # continuous
            y_var = self.y_vars[cost['y_var']]  # binary
            self.model.addConstr(
                x_var <= self.params['capacity_per_arc'] * y_var,
                name=f"capacity_{cost['arc_id']}"
            )

        # Build node-arc incidence matrix for flow balance constraints
        print("Adding flow balance constraints...")
        node_balance = {}

        # Initialize node balance expressions
        for fb in self.flow_balance:
            node_balance[fb['node_id']] = gp.LinExpr()

        # Add flow contributions to node balances using x variables (continuous flow)
        for i, arc in enumerate(self.arcs):
            if i < len(self.costs):
                x_var = self.x_vars[self.costs[i]['x_var']]  # continuous flow variable
                start_node = arc['start_node']
                end_node = arc['end_node']

                # Flow contribution to node balance (based on original CNS pattern)
                if start_node in node_balance:
                    node_balance[start_node] -= x_var  # flow out (negative coefficient)

                if end_node in node_balance:
                    node_balance[end_node] += x_var   # flow in (positive coefficient)

        # Add flow balance constraints
        for fb in self.flow_balance:
            node_id = fb['node_id']
            required_balance = float(fb['flow_balance'])
            if node_id in node_balance:
                self.model.addConstr(
                    node_balance[node_id] == required_balance,
                    name=f"balance_{node_id}"
                )

        print(f"Added {len(node_balance)} flow balance constraints")

        # Configure solver
        self.model.Params.OutputFlag = 1
        self.model.Params.TimeLimit = 300  # 5 minutes time limit

        # Set up logging
        os.makedirs('logs', exist_ok=True)
        self.model.Params.LogFile = 'logs/solver.log'

    def solve(self):
        """Solve the optimization problem"""
        if self.model is None:
            self.build_model()

        print("\\nStarting optimization...")
        self.model.optimize()

        return self.model.Status

    def print_solution(self):
        """Print the solution"""
        if self.model.Status == GRB.OPTIMAL:
            print(f"\\nOptimal solution found!")
            print(f"Optimal objective value: {self.model.ObjVal}")

            # Count active arcs and total flow
            active_arcs = 0
            total_flow = 0
            for cost in self.costs:
                x_var = self.x_vars[cost['x_var']]  # continuous flow
                y_var = self.y_vars[cost['y_var']]  # binary
                if y_var.X > 0.5:  # Binary variable y is 1 (arc is active)
                    active_arcs += 1
                    total_flow += x_var.X

            print(f"Number of active arcs: {active_arcs}")
            print(f"Total flow: {total_flow:.2f}")

            # Standard output format
            print(f"optimal_value = {self.model.ObjVal}")
            print(f"objective = {self.model.ObjVal}")
            print(f"result = {self.model.ObjVal}")

            return self.model.ObjVal
        else:
            print(f"Optimization ended with status: {self.model.Status}")
            return None

    def save_solution(self, filename: str = 'solution.csv'):
        """Save solution to CSV file"""
        if self.model.Status != GRB.OPTIMAL:
            print("No optimal solution to save")
            return

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['arc_id', 'x_var', 'y_var', 'flow', 'is_active', 'fixed_cost'])

            for cost in self.costs:
                arc_id = cost['arc_id']
                x_var_name = cost['x_var']
                y_var_name = cost['y_var']
                flow = self.x_vars[x_var_name].X
                is_active = self.y_vars[y_var_name].X > 0.5
                fixed_cost = float(cost['fixed_cost'])

                writer.writerow([arc_id, x_var_name, y_var_name, flow, is_active, fixed_cost])

        print(f"Solution saved to {filename}")

def main():
    """Main function to solve the problem"""
    try:
        # Create solver instance
        solver = FixedChargeNetworkSolver()

        # Build and solve the model
        solver.build_model()
        status = solver.solve()

        # Print and save results
        if status == GRB.OPTIMAL:
            optimal_value = solver.print_solution()
            solver.save_solution("logs/solution.csv")
            return optimal_value
        else:
            print(f"Failed to find optimal solution. Status: {status}")
            return None

    except Exception as e:
        print(f"Error during solving: {e}")
        return None

if __name__ == "__main__":
    main()