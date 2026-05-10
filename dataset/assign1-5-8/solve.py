import csv
import os
import sys
import gurobipy as gp
from gurobipy import GRB
import numpy as np
from typing import Dict, List, Tuple


class GAPSolver:
    """
    Solver for the Generalized Assignment Problem.

    The GAP involves assigning tasks to agents with capacity constraints
    to minimize total assignment costs.
    """

    def __init__(self, data_dir: str = 'data/'):
        """
        Initialize the GAP solver.

        Args:
            data_dir: Directory containing CSV data files
        """
        self.data_dir = data_dir
        self.tasks = []
        self.agents = []
        self.cost_matrix = None
        self.resource_matrix = None
        self.parameters = {}
        self.model = None
        self.assignment_vars = {}

    def load_data(self) -> bool:
        """
        Load data from CSV files.

        Returns:
            True if data loaded successfully, False otherwise
        """
        try:
            # Load parameters
            parameter_file = os.path.join(self.data_dir, 'parameter.csv')
            self.parameters = {}
            with open(parameter_file, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        self.parameters[row[0]] = int(row[1]) if row[1].isdigit() else float(row[1])

            # Load tasks
            task_file = os.path.join(self.data_dir, 'tasks.csv')
            with open(task_file, 'r') as f:
                reader = csv.DictReader(f)
                self.tasks = list(reader)

            # Load agents
            agent_file = os.path.join(self.data_dir, 'agents.csv')
            with open(agent_file, 'r') as f:
                reader = csv.DictReader(f)
                self.agents = list(reader)

            # Load cost matrix
            cost_file = os.path.join(self.data_dir, 'cost.csv')
            with open(cost_file, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)[1:]  # Skip task_id column
                cost_data = []
                for row in reader:
                    cost_data.append([int(x) for x in row[1:]])
                self.cost_matrix = np.array(cost_data)

            # Load resource requirements
            resource_file = os.path.join(self.data_dir, 'resource.csv')
            with open(resource_file, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)[1:]  # Skip task_id column
                resource_data = []
                for row in reader:
                    resource_data.append([int(x) for x in row[1:]])
                self.resource_matrix = np.array(resource_data)

            print(f"Loaded {len(self.tasks)} tasks and {len(self.agents)} agents")
            return True

        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    def build_model(self) -> bool:
        """
        Build the MILP model.

        Returns:
            True if model built successfully, False otherwise
        """
        try:
            self.model = gp.Model("Generalized_Assignment_Problem")
            self.model.setParam('OutputFlag', 1)

            # Create assignment variables x[i][j] = 1 if task i is assigned to agent j
            self.assignment_vars = {}
            for i, task in enumerate(self.tasks):
                self.assignment_vars[task['task_id']] = {}
                for j, agent in enumerate(self.agents):
                    var_name = f"x_{task['task_id']}_{agent['agent_id']}"
                    self.assignment_vars[task['task_id']][agent['agent_id']] = \
                        self.model.addVar(vtype=GRB.BINARY, name=var_name)

            # Add constraints
            # 1. Each task must be assigned to exactly one agent
            for i, task in enumerate(self.tasks):
                task_assignments = []
                for j, agent in enumerate(self.agents):
                    task_assignments.append(self.assignment_vars[task['task_id']][agent['agent_id']])
                self.model.addConstr(sum(task_assignments) == 1, name=f"assign_task_{task['task_id']}")

            # 2. Agent capacity constraints
            for j, agent in enumerate(self.agents):
                capacity_expr = []
                for i, task in enumerate(self.tasks):
                    var = self.assignment_vars[task['task_id']][agent['agent_id']]
                    resource_req = self.resource_matrix[i][j]
                    capacity_expr.append(resource_req * var)
                self.model.addConstr(
                    sum(capacity_expr) <= int(agent['capacity']),
                    name=f"capacity_{agent['agent_id']}"
                )

            # Set objective: minimize total assignment cost
            objective_expr = []
            for i, task in enumerate(self.tasks):
                for j, agent in enumerate(self.agents):
                    var = self.assignment_vars[task['task_id']][agent['agent_id']]
                    cost = self.cost_matrix[i][j]
                    objective_expr.append(cost * var)

            self.model.setObjective(sum(objective_expr), GRB.MINIMIZE)

            # Update model
            self.model.update()

            print(f"Model built successfully with {self.model.NumVars} variables and {self.model.NumConstrs} constraints")
            return True

        except Exception as e:
            print(f"Error building model: {e}")
            return False

    def solve(self, time_limit: int = 300) -> bool:
        """
        Solve the GAP model.

        Args:
            time_limit: Maximum solution time in seconds

        Returns:
            True if solved successfully, False otherwise
        """
        try:
            # Configure solver
            self.model.setParam('TimeLimit', time_limit)
            self.model.setParam('MIPGap', 0.01)  # 1% optimality gap

            # Solve the model
            print("Solving Generalized Assignment Problem...")
            self.model.optimize()

            return True

        except Exception as e:
            print(f"Error solving model: {e}")
            return False

    def print_solution(self):
        """Print the solution details."""
        if self.model.Status == GRB.OPTIMAL or self.model.Status == GRB.TIME_LIMIT:
            print(f"\n{'='*60}")
            print("SOLUTION SUMMARY")
            print(f"{'='*60}")
            print(f"Status: {self.model.Status}")
            print(f"Objective value: {self.model.ObjVal}")
            print(f"MIP gap: {self.model.MIPGap:.4%}")
            print(f"Solution time: {self.model.Runtime:.2f} seconds")

            # Print assignments
            print(f"\nASSIGNMENTS:")
            total_cost = 0
            agent_workload = {agent['agent_id']: 0 for agent in self.agents}

            for i, task in enumerate(self.tasks):
                for j, agent in enumerate(self.agents):
                    var = self.assignment_vars[task['task_id']][agent['agent_id']]
                    if var.X > 0.5:  # Variable is 1 (assigned)
                        cost = self.cost_matrix[i][j]
                        resource = self.resource_matrix[i][j]
                        total_cost += cost
                        agent_workload[agent['agent_id']] += resource
                        print(f"  {task['task_id']} -> {agent['agent_id']} "
                              f"(cost: {cost}, resource: {resource})")

            print(f"\nAGENT WORKLOAD:")
            for agent in self.agents:
                workload = agent_workload[agent['agent_id']]
                capacity = int(agent['capacity'])
                utilization = (workload / capacity) * 100 if capacity > 0 else 0
                print(f"  {agent['agent_id']}: {workload}/{capacity} ({utilization:.1f}%)")

            print(f"\nTotal cost: {total_cost}")
            print(f"{'='*60}")

            # Standard output format for validation
            print(f"optimal_value = {self.model.ObjVal}")
            print(f"objective = {self.model.ObjVal}")
            print(f"result = {self.model.ObjVal}")

        else:
            if self.model.Status == GRB.INFEASIBLE:
                print("Problem is infeasible!")
            elif self.model.Status == GRB.UNBOUNDED:
                print("Problem is unbounded!")
            else:
                print(f"Solution status: {self.model.Status}")

    def save_solution_to_csv(self, filename: str = 'solution.csv'):
        """Save solution to CSV file."""
        if self.model.Status not in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
            print("No feasible solution to save")
            return

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['task_id', 'agent_id', 'cost', 'resource_usage'])

            for i, task in enumerate(self.tasks):
                for j, agent in enumerate(self.agents):
                    var = self.assignment_vars[task['task_id']][agent['agent_id']]
                    if var.X > 0.5:
                        cost = self.cost_matrix[i][j]
                        resource = self.resource_matrix[i][j]
                        writer.writerow([task['task_id'], agent['agent_id'], cost, resource])

        print(f"Solution saved to {filename}")


def main():
    """Main function to solve the GAP instance."""
    # Setup logging
    os.makedirs('logs', exist_ok=True)

    # Create solver instance
    solver = GAPSolver()

    # Load data
    if not solver.load_data():
        print("Failed to load data")
        sys.exit(1)

    # Build model
    if not solver.build_model():
        print("Failed to build model")
        sys.exit(1)

    # Set up logging
    if solver.model:
        solver.model.setParam('LogFile', 'logs/solver.log')

    # Solve model
    if not solver.solve():
        print("Failed to solve model")
        sys.exit(1)

    # Print solution
    solver.print_solution()

    # Save solution
    solver.save_solution_to_csv()

    # Exit with success code only if we have a valid solution
    if solver.model.Status in [GRB.OPTIMAL, GRB.TIME_LIMIT]:
        sys.exit(0)
    else:
        print(f"No valid solution found. Status: {solver.model.Status}")
        sys.exit(1)


if __name__ == "__main__":
    main()