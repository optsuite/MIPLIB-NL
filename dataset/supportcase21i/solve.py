import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
from typing import Dict, List, Any, Optional

class TechnicalSupportCaseSolver:
    """
    Universal solver for Technical Support Case Selection Problem.
    Implements the mathematical model: minimize Σ(c_i * x_i) subject to Σ(a_ij * x_i) ≥ b_j
    """

    def __init__(self, data_dir: str = "data/", log_dir: str = "logs/"):
        self.data_dir = data_dir
        self.log_dir = log_dir
        self.model = None
        self.data = {}

    def load_data(self) -> Dict[str, Any]:
        """Load and process CSV data"""
        try:
            # Load cases
            df_cases = pd.read_csv(f"{self.data_dir}cases.csv")
            case_id_col = self._find_identifier_column(df_cases, ['case_id', 'id', 'identifier', 'name'])
            cost_col = self._find_column(df_cases, ['cost', 'deployment_cost', 'price', 'expense'])

            cases = df_cases[case_id_col].astype(str).tolist()
            costs = df_cases.set_index(case_id_col)[cost_col].astype(float).to_dict()

            # Load requirements
            df_requirements = pd.read_csv(f"{self.data_dir}requirements.csv")
            req_id_col = self._find_identifier_column(df_requirements, ['requirement_id', 'id', 'identifier', 'name'])
            threshold_col = self._find_column(df_requirements, ['threshold', 'coverage_threshold', 'requirement', 'demand'])

            requirements = df_requirements[req_id_col].astype(str).tolist()
            thresholds = df_requirements.set_index(req_id_col)[threshold_col].astype(float).to_dict()

            # Load coverage
            df_coverage = pd.read_csv(f"{self.data_dir}coverage.csv")
            if len(df_coverage.columns) >= 3:
                case_coverage_col = self._find_identifier_column(df_coverage, ['case_id', 'case', 'source'], case_id_col)
                req_coverage_col = self._find_identifier_column(df_coverage, ['requirement_id', 'requirement', 'target'], req_id_col)
                value_col = self._find_column(df_coverage, ['value', 'coverage', 'amount', 'coefficient'])

                coverage = {}
                for _, row in df_coverage.iterrows():
                    case_key = str(row[case_coverage_col])
                    req_key = str(row[req_coverage_col])
                    coverage[(case_key, req_key)] = float(row[value_col])
            else:
                coverage = {(case, req): 1 for case in cases for req in requirements}

            # Load parameters
            parameters = self._load_parameters()

            self.data = {
                'cases': cases,
                'costs': costs,
                'requirements': requirements,
                'thresholds': thresholds,
                'coverage': coverage,
                'parameters': parameters
            }

            return self.data

        except Exception as e:
            raise RuntimeError(f"Error loading data: {str(e)}")

    def _find_identifier_column(self, df: pd.DataFrame, preferred_names: List[str], fallback: Optional[str] = None) -> str:
        """Find the best identifier column"""
        for name in preferred_names:
            if name in df.columns:
                return name
        for col in df.columns:
            if df[col].dtype == 'object':
                return col
        return fallback if fallback else df.columns[0]

    def _find_column(self, df: pd.DataFrame, preferred_names: List[str]) -> str:
        """Find the best numeric column"""
        for name in preferred_names:
            if name in df.columns:
                return name
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                return col
        raise ValueError(f"Could not find suitable column among {preferred_names}")

    def _load_parameters(self) -> Dict[str, Any]:
        """Load parameters from CSV"""
        try:
            df_params = pd.read_csv(f"{self.data_dir}parameter.csv", header=None)
            if len(df_params.columns) == 2:
                return dict(zip(df_params.iloc[:, 0], df_params.iloc[:, 1]))
            elif len(df_params) == 2 and len(df_params.columns) == 1:
                return dict(zip(df_params.iloc[0], df_params.iloc[1]))
            else:
                return {}
        except FileNotFoundError:
            return {}

    def build_model(self) -> gp.Model:
        """Build the optimization model"""
        if not self.data:
            self.load_data()

        # Create model
        self.model = gp.Model("Technical_Support_Case_Selection")

        # Configure logging
        os.makedirs(self.log_dir, exist_ok=True)
        self.model.setParam('LogFile', f"{self.log_dir}solver.log")
        self.model.setParam('OutputFlag', 1)

        # Extract data
        cases = self.data['cases']
        costs = self.data['costs']
        requirements = self.data['requirements']
        thresholds = self.data['thresholds']
        coverage = self.data['coverage']

        # Decision variables
        x = self.model.addVars(cases, vtype=GRB.BINARY, name="x")

        # Objective: minimize total cost
        objective = gp.quicksum(costs[i] * x[i] for i in cases)
        self.model.setObjective(objective, GRB.MINIMIZE)

        # Constraints: coverage requirements
        for j in requirements:
            # Ensure both j and thresholds[j] are compatible types
            threshold_value = float(thresholds[j])
            coverage_expr = gp.quicksum(coverage.get((i, j), 0.0) * x[i] for i in cases)
            self.model.addConstr(coverage_expr >= threshold_value, name=f"Coverage_Req_{j[:8]}")

        return self.model

    def solve(self) -> Dict[str, Any]:
        """Solve the optimization problem"""
        try:
            if self.model is None:
                self.build_model()

            # Solve
            self.model.optimize()

            # Extract solution
            solution = self._extract_solution()
            self._solution = solution

            # Print standard output
            self._print_standard_output(solution)

            return solution

        except Exception as e:
            print(f"Error during solving: {str(e)}")
            raise e

    def _extract_solution(self) -> Dict[str, Any]:
        """Extract solution from model"""
        if self.model.Status != GRB.OPTIMAL:
            return {
                'status': 'No optimal solution found',
                'status_code': self.model.Status
            }

        # Extract selected cases
        x_vars = {var.VarName: var.X for var in self.model.getVars() if var.VarName.startswith('x[')}
        selected_cases = []

        for var_name, value in x_vars.items():
            if value > 0.5:  # Binary variable
                case_id = var_name[2:-1]  # Remove 'x[' and ']'
                selected_cases.append(case_id)

        # Calculate total cost
        total_cost = sum(self.data['costs'].get(case, 0.0) for case in selected_cases)

        return {
            'status': 'Optimal',
            'objective_value': self.model.ObjVal,
            'total_cost': total_cost,
            'selected_cases': selected_cases,
            'num_selected_cases': len(selected_cases),
            'solve_time': self.model.Runtime
        }

    def _print_standard_output(self, solution: Dict[str, Any]):
        """Print solution in standard format"""
        if solution['status'] == 'Optimal':
            print(f"optimal_value = {solution['objective_value']}")
            print(f"objective = {solution['objective_value']}")
            print(f"result = {solution['objective_value']}")
        else:
            print(f"optimal_value = ERROR")
            print(f"objective = ERROR")
            print(f"result = ERROR")

    def print_detailed_solution(self):
        """Print detailed solution analysis"""
        if not hasattr(self, '_solution'):
            print("No solution available. Run solve() first.")
            return

        solution = self._solution
        if solution['status'] != 'Optimal':
            print(f"Solution status: {solution['status']}")
            return

        print(f"\n{'='*60}")
        print("DETAILED SOLUTION ANALYSIS")
        print(f"{'='*60}")
        print(f"Total Cost: {solution['total_cost']}")
        print(f"Selected Cases: {solution['num_selected_cases']}/{len(self.data['cases'])}")
        print(f"Solve Time: {solution['solve_time']:.3f} seconds")

        # Cost breakdown
        cost_breakdown = {}
        for case in solution['selected_cases']:
            cost = self.data['costs'].get(case, 0)
            cost_breakdown[cost] = cost_breakdown.get(cost, 0) + 1

        print(f"\nCost Breakdown:")
        for cost, count in sorted(cost_breakdown.items()):
            print(f"  Cost {cost}: {count} case(s)")

        print(f"\nSelected Cases:")
        for case in sorted(solution['selected_cases']):
            cost = self.data['costs'].get(case, 0)
            print(f"  {case}: cost = {cost}")


def main():
    """Main function for command line execution"""
    try:
        solver = TechnicalSupportCaseSolver()
        solution = solver.solve()

        if solution['status'] == 'Optimal':
            solver.print_detailed_solution()

        return solution

    except Exception as e:
        print(f"Error: {str(e)}")
        return None


if __name__ == "__main__":
    main()