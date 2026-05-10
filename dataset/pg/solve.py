import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def read_data(data_dir: str = 'data/'):
    """
    Read problem data from CSV files.
    
    Args:
        data_dir: Directory containing CSV files
        
    Returns:
        Dictionary containing all problem data
    """
    print(f"Reading data from {data_dir}...")
    
    # Read project data
    project_df = pd.read_csv(f"{data_dir}project.csv")
    print(f"  ✓ Loaded {len(project_df)} projects")
    
    # Read facility data
    facility_df = pd.read_csv(f"{data_dir}facility.csv")
    print(f"  ✓ Loaded {len(facility_df)} facilities")
    
    # Read assignment profits
    profit_df = pd.read_csv(f"{data_dir}assignment_profit.csv")
    print(f"  ✓ Loaded {len(profit_df)} assignment profit entries")
    
    # Read facility demands
    demand_df = pd.read_csv(f"{data_dir}facility_demand.csv")
    print(f"  ✓ Loaded {len(demand_df)} facility demand entries")
    
    # Convert to dictionaries for easy lookup
    data = {
        'project_df': project_df,
        'facility_df': facility_df,
        'profit_df': profit_df,
        'demand_df': demand_df,
        'num_projects': len(project_df),
        'num_facilities': len(facility_df)
    }
    
    # Create lookup dictionaries
    data['fixed_cost'] = dict(zip(project_df['project_id'], project_df['fixed_cost']))
    data['project_demand'] = dict(zip(project_df['project_id'], project_df['demand']))
    data['f_upper_bound'] = dict(zip(project_df['project_id'], project_df['f_upper_bound']))
    data['facility_capacity'] = dict(zip(facility_df['facility_id'], facility_df['capacity']))
    
    # Create assignment profit dictionary {(project_id, facility_id): profit}
    data['assignment_profit'] = {}
    for _, row in profit_df.iterrows():
        data['assignment_profit'][(int(row['project_id']), int(row['facility_id']))] = row['profit']
    
    # Create demand coefficient dictionary {(project_id, facility_id): coefficient}
    data['demand_coefficient'] = {}
    for _, row in demand_df.iterrows():
        data['demand_coefficient'][(int(row['project_id']), int(row['facility_id']))] = row['demand_coefficient']
    
    print(f"\n✅ Data loaded successfully")
    return data


def build_and_solve_model(data: dict):
    """
    Build and solve the optimization model.
    
    Args:
        data: Dictionary containing problem data
        
    Returns:
        Gurobi model object
    """
    print("\n" + "="*70)
    print("Building optimization model...")
    print("="*70)
    
    # Create model
    model = gp.Model("project_facility_assignment")
    
    # Configure Gurobi logging
    os.makedirs('logs', exist_ok=True)
    model.setParam('LogFile', 'logs/solver.log')
    model.setParam('OutputFlag', 1)
    
    num_projects = data['num_projects']
    num_facilities = data['num_facilities']
    
    print(f"\nProblem Size:")
    print(f"- Projects: {num_projects}")
    print(f"- Facilities: {num_facilities}")
    print(f"- Total assignment variables: {num_projects * num_facilities}")
    
    # Decision Variables
    print("\nCreating decision variables...")
    
    # z[i]: Binary variable for project selection
    z = model.addVars(num_projects, vtype=GRB.INTEGER, lb=0, ub=1, name="z")
    
    # l[i,j]: Continuous variable for assignment (0 <= l[i,j] <= 1)
    l = model.addVars(num_projects, num_facilities, vtype=GRB.CONTINUOUS, 
                      lb=0, ub=1, name="l")
    
    # f[i]: Continuous auxiliary variable with upper bound
    f = {}
    for i in range(num_projects):
        f[i] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, 
                           ub=data['f_upper_bound'][i], name=f"f{i}")
    
    print(f"  ✓ Created {len(z)} binary variables (z)")
    print(f"  ✓ Created {len(l)} continuous variables (l)")
    print(f"  ✓ Created {len(f)} auxiliary variables (f)")
    
    # Objective Function
    print("\nSetting objective function...")
    obj_expr = gp.LinExpr()
    
    # Project fixed costs: sum(fixed_cost[i] * z[i])
    for i in range(num_projects):
        obj_expr -= data['fixed_cost'][i] * z[i]
    
    # Assignment profits: -sum(assignment_profit[i,j] * l[i,j])
    for i in range(num_projects):
        for j in range(num_facilities):
            profit = data['assignment_profit'].get((i, j), 0)
            obj_expr += profit * l[i, j]
    
    model.setObjective(obj_expr, GRB.MAXIMIZE)
    print(f"  ✓ Objective set: Minimize (fixed costs - assignment profits)")
    
    # Constraints
    print("\nAdding constraints...")
    
    # 1. Facility Capacity Constraints
    print("  Adding facility capacity constraints...")
    for j in range(num_facilities):
        constr_expr = gp.LinExpr()
        for i in range(num_projects):
            coeff = data['demand_coefficient'].get((i, j), 0)
            constr_expr += coeff * l[i, j]
        
        model.addConstr(constr_expr <= data['facility_capacity'][j],
                       name=f"capacity_facility_{j}")
    print(f"    ✓ Added {num_facilities} facility capacity constraints")
    
    # 2. Project Demand Constraints
    # Constraint: project_demand[i] * z[i] + sum_j(demand_coefficient[i,j] * l[i,j]) + f[i] = project_demand[i]
    print("  Adding project demand constraints...")
    for i in range(num_projects):
        constr_expr = gp.LinExpr()
        # Add project_demand[i] * z[i] term
        constr_expr += data['project_demand'][i] * z[i]
        # Add demand_coefficient terms  
        for j in range(num_facilities):
            coeff = data['demand_coefficient'].get((i, j), 0)
            constr_expr += coeff * l[i, j]
        # Add f[i] term
        constr_expr += f[i]
        
        model.addConstr(constr_expr == data['project_demand'][i],
                       name=f"demand_project_{i}")
    print(f"    ✓ Added {num_projects} project demand constraints")
    
    print(f"\n✅ Model built successfully")
    print(f"   Total constraints: {model.NumConstrs}")
    print(f"   Total variables: {model.NumVars}")
    
    # Solve the model
    print("\n" + "="*70)
    print("Solving the model...")
    print("="*70 + "\n")
    
    model.optimize()
    
    return model


def print_results(model: gp.Model, data: dict):
    """
    Print optimization results.
    
    Args:
        model: Solved Gurobi model
        data: Problem data dictionary
    """
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS")
    print("="*70)
    
    if model.Status == GRB.OPTIMAL:
        print(f"\n✅ Optimal solution found!")
        print(f"\nOptimal Value: {model.ObjVal:.6f}")
        
        # Standard output format for automatic verification
        print(f"\noptimal_value = {model.ObjVal}")
        print(f"objective = {model.ObjVal}")
        print(f"result = {model.ObjVal}")
        
        # Extract solution
        z_vars = [v for v in model.getVars() if v.VarName.startswith('z[')]
        l_vars = [v for v in model.getVars() if v.VarName.startswith('l[')]
        f_vars = [v for v in model.getVars() if v.VarName.startswith('f')]
        
        # Count selected projects
        selected_projects = sum(1 for v in z_vars if v.X > 0.5)
        print(f"\nSolution Summary:")
        print(f"- Selected projects: {selected_projects} / {data['num_projects']}")
        print(f"- Active assignments (l > 0.01): {sum(1 for v in l_vars if v.X > 0.01)}")
        print(f"- Non-zero f variables: {sum(1 for v in f_vars if v.X > 0.01)}")
        
        # Calculate objective components
        fixed_cost_total = sum(data['fixed_cost'][i] * z_vars[i].X 
                              for i in range(data['num_projects']))
        
        profit_total = 0
        for i in range(data['num_projects']):
            for j in range(data['num_facilities']):
                idx = i * data['num_facilities'] + j
                if idx < len(l_vars):
                    profit = data['assignment_profit'].get((i, j), 0)
                    profit_total += profit * l_vars[idx].X
        
        print(f"\nObjective Breakdown:")
        print(f"- Total fixed costs: {fixed_cost_total:.2f}")
        print(f"- Total assignment profits: {profit_total:.2f}")
        print(f"- Net objective (cost - profit): {fixed_cost_total - profit_total:.6f}")
        
    elif model.Status == GRB.INFEASIBLE:
        print("\n❌ Problem is INFEASIBLE")
        print("optimal_value = INFEASIBLE")
        model.computeIIS()
        model.write("logs/infeasible.ilp")
        print("IIS written to logs/infeasible.ilp")
        
    elif model.Status == GRB.UNBOUNDED:
        print("\n❌ Problem is UNBOUNDED")
        print("optimal_value = UNBOUNDED")
        
    else:
        print(f"\n❌ Optimization ended with status {model.Status}")
        print(f"optimal_value = ERROR_{model.Status}")
    
    print("\n" + "="*70)
    print(f"Solver log saved to: logs/solver.log")
    print("="*70)


def main():
    """Main function to run the solver"""
    print("\n" + "="*70)
    print("PROJECT-FACILITY ASSIGNMENT PROBLEM SOLVER")
    print("="*70 + "\n")
    
    # Read data
    data = read_data('data/')
    
    # Build and solve model
    model = build_and_solve_model(data)
    
    # Print results
    print_results(model, data)


if __name__ == "__main__":
    main()

