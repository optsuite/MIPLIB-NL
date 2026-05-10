
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import sys


def load_data():
    """Load data from CSV files"""
    try:
        # Read period data
        df_periods = pd.read_csv('data/periods.csv')
        
        # Read parameter data
        df_parameters = pd.read_csv('data/parameters.csv')
        
        return df_periods, df_parameters
    
    except FileNotFoundError as e:
        print(f"❌ Error: Data file not found - {e}")
        print("Please ensure data/periods.csv and data/parameters.csv exist.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        sys.exit(1)


def build_model(df_periods, df_parameters):
    """Build the optimization model"""
    
    # Extract parameters
    params = df_parameters.iloc[0].to_dict()
    num_periods = len(df_periods)
    
    print("hhhhh",params['aircraft_retention_rate'])
    
    # Create model
    model = gp.Model("airline_fleet_planning")
    model.setParam('OutputFlag', 1)
    model.setParam('LogFile', 'logs/solver.log')
    
    # ============== Decision Variables ==============
    print("\nCreating decision variables...")
    
    # Standard aircraft count (STM: Standard Aircraft)
    standard_aircraft = {}
    for period in range(1, num_periods + 1):
        if period == 1:
            # Period 1: continuous variable, no lower bound
            standard_aircraft[period] = model.addVar(
                lb=0, 
                vtype=GRB.CONTINUOUS,
                name=f"STM{period}"
            )
        else:
            # Periods 2-6: integer variable with bounds
            standard_aircraft[period] = model.addVar(
                lb=params['min_standard_aircraft_period_2_6'],
                ub=params['max_standard_aircraft_period_2_6'],
                vtype=GRB.INTEGER,
                name=f"STM{period}"
            )
    
    # New aircraft purchases (ANM: New Aircraft)
    rental_aircraft = {}
    for period in range(1, num_periods + 1):
        rental_aircraft[period] = model.addVar(
            lb=0,
            ub=params['max_rental_aircraft'],
            vtype=GRB.INTEGER,
            name=f"ANM{period}"
        )
    
    # Overtime hours (UE: Overtime Hours)
    overtime_hours = {}
    for period in range(1, num_periods + 1):
        overtime_hours[period] = model.addVar(
            lb=0,
            vtype=GRB.CONTINUOUS,
            name=f"UE{period}"
        )
    
    print(f"  Created {num_periods * 3} decision variables")
    
    # ============== Objective Function ==============
    obj_expr = gp.quicksum(
        params['standard_aircraft_cost'] * standard_aircraft[p] +
        params['rental_aircraft_cost'] * rental_aircraft[p] +
        params['overtime_cost'] * overtime_hours[p]
        for p in range(1, num_periods + 1)
    )
    model.setObjective(obj_expr, GRB.MINIMIZE)
    
    # ============== Constraints ==============
    print("\nAdding constraints...")
    
    # Add 3 constraints for each period
    for period in range(1, num_periods + 1):
        period_data = df_periods[df_periods['period'] == period].iloc[0]
        
        # 1. Fleet balance constraint (ANZ)
        if period == 1:
            # Period 1: initial fleet size
            model.addConstr(
                standard_aircraft[period] == period_data['aircraft_balance'],
                name=f"ANZ{period}"
            )
        else:
            # Periods 2-6: STM[t] = params['aircraft_retention_rate']*STM[t-1] + ANM[t-1]
            # New standard fleet = 90% of previous period + previous purchases
            model.addConstr(
                params['aircraft_retention_rate'] * standard_aircraft[period-1] + rental_aircraft[period-1] - standard_aircraft[period] == 0,
                name=f"ANZ{period}"
            )
        
        # 2. Minimum flight hour requirement (STD)
        # 150*STM - 100*ANM + UE >= requirement
        # Note: ANM has negative coefficient (new aircraft consume resources for training)
        model.addConstr(
            params['standard_aircraft_hours'] * standard_aircraft[period] -
            params['rental_aircraft_hours'] * rental_aircraft[period] +
            overtime_hours[period] >= period_data['min_flight_hours'],
            name=f"STD{period}"
        )
        
        # 3. Maximum overtime limit (UEB)
        # -20*STM + UE <= 0, i.e., UE <= 20*STM
        model.addConstr(
            overtime_hours[period] <= 20 * standard_aircraft[period],
            name=f"UEB{period}"
        )
    
    print(f"  Added {num_periods * 3} constraints")
    
    return model, standard_aircraft, rental_aircraft, overtime_hours, params, num_periods


def print_results(model, standard_aircraft, rental_aircraft, overtime_hours, params, num_periods, df_periods):
    """Print detailed solution results"""
    
    if model.Status == GRB.OPTIMAL:
        print(f"\n{'='*80}")
        print(f"optimal_value = {model.ObjVal:.6f}")
        print(f"objective = {model.ObjVal:.6f}")
        print(f"result = {model.ObjVal:.6f}")
        print(f"{'='*80}")
        
        print("\n" + "=" * 80)
        print("Detailed Solution Results")
        print("=" * 80)
        
        # Display results by period
        print(f"\n{'Period':<8} {'Standard':<12} {'New':<12} {'Overtime':<12} {'Period Cost':<15}")
        print(f"{'':8} {'Aircraft':<12} {'Aircraft':<12} {'Hours':<12} {'':15}")
        print("-" * 65)
        
        total_cost = 0
        solution_data = []
        
        for period in range(1, num_periods + 1):
            std = standard_aircraft[period].X
            rental = rental_aircraft[period].X
            overtime = overtime_hours[period].X
            
            period_cost = (params['standard_aircraft_cost'] * std +
                          params['rental_aircraft_cost'] * rental +
                          params['overtime_cost'] * overtime)
            
            total_cost += period_cost
            
            print(f"{period:<8} {std:<12.2f} {rental:<12.0f} {overtime:<12.2f} {period_cost:<15,.2f}")
            
            solution_data.append({
                'period': period,
                'standard_aircraft': std,
                'new_aircraft': rental,
                'overtime_hours': overtime,
                'period_cost': period_cost
            })
        
        print("-" * 65)
        print(f"{'Total':<8} {'':<12} {'':<12} {'':<12} {total_cost:<15,.2f}")
        
        # Cost breakdown
        print(f"\n" + "=" * 80)
        print("Cost Breakdown")
        print("=" * 80)
        
        std_cost = sum(params['standard_aircraft_cost'] * standard_aircraft[p].X 
                       for p in range(1, num_periods + 1))
        rental_cost = sum(params['rental_aircraft_cost'] * rental_aircraft[p].X 
                          for p in range(1, num_periods + 1))
        overtime_cost_total = sum(params['overtime_cost'] * overtime_hours[p].X 
                                  for p in range(1, num_periods + 1))
        
        print(f"Standard aircraft cost: {std_cost:>15,.2f} ({std_cost/model.ObjVal*100:>5.1f}%)")
        print(f"New aircraft cost:      {rental_cost:>15,.2f} ({rental_cost/model.ObjVal*100:>5.1f}%)")
        print(f"Overtime cost:          {overtime_cost_total:>15,.2f} ({overtime_cost_total/model.ObjVal*100:>5.1f}%)")
        print(f"{'-'*45}")
        print(f"Total cost:             {model.ObjVal:>15,.2f}")
        
        # Constraint satisfaction
        print(f"\n" + "=" * 80)
        print("Constraint Satisfaction")
        print("=" * 80)
        
        print(f"\n{'Period':<8} {'Fleet':<12} {'Flight Hours':<25} {'Overtime':<15}")
        print(f"{'':8} {'Balance':<12} {'Requirement':<25} {'Limit':<15}")
        print("-" * 70)
        
        all_satisfied = True
        for period in range(1, num_periods + 1):
            period_data = df_periods[df_periods['period'] == period].iloc[0]
            
            # Check fleet balance
            if period == 1:
                balance_status = "✓" if abs(standard_aircraft[period].X - period_data['aircraft_balance']) < 0.01 else "✗"
                if balance_status == "✗":
                    all_satisfied = False
            else:
                expected = params['aircraft_retention_rate'] * standard_aircraft[period-1].X + rental_aircraft[period-1].X
                balance_status = "✓" if abs(standard_aircraft[period].X - expected) < 0.01 else "✗"
                if balance_status == "✗":
                    all_satisfied = False
            
            # Check flight hours
            actual_hours = (params['standard_aircraft_hours'] * standard_aircraft[period].X -
                           params['rental_aircraft_hours'] * rental_aircraft[period].X +
                           overtime_hours[period].X)
            hours_status = "✓" if actual_hours >= period_data['min_flight_hours'] - 0.01 else "✗"
            hours_info = f"{actual_hours:.0f} ≥ {period_data['min_flight_hours']:.0f}"
            if hours_status == "✗":
                all_satisfied = False
            
            # Check overtime limit
            max_overtime = 20 * standard_aircraft[period].X
            overtime_status = "✓" if overtime_hours[period].X <= max_overtime + 0.01 else "✗"
            overtime_info = f"{overtime_hours[period].X:.0f} ≤ {max_overtime:.0f}"
            if overtime_status == "✗":
                all_satisfied = False
            
            print(f"{period:<8} {balance_status:<12} {hours_status} {hours_info:<24} {overtime_status} {overtime_info:<14}")
        
        if all_satisfied:
            print("\n✅ All constraints satisfied")
        else:
            print("\n⚠️ Some constraints not satisfied (check above)")
        
        # Solution statistics
        print(f"\n" + "=" * 80)
        print("Solution Statistics")
        print("=" * 80)
        print(f"Model name: {model.ModelName}")
        print(f"Variables: {model.NumVars}")
        print(f"  Continuous: 7 (STM₁ + UE₁₋₆)")
        print(f"  Integer: 11 (STM₂₋₆ + ANM₁₋₆)")
        print(f"Constraints: {model.NumConstrs}")
        print(f"  Equality (=): 6 (fleet balance)")
        print(f"  Inequality (≥): 6 (flight hours)")
        print(f"  Inequality (≤): 6 (overtime limits)")
        print(f"Optimal value: {model.ObjVal:,.2f}")
        
        # Write solution to file
        df_solution = pd.DataFrame(solution_data)
        df_solution.to_csv('logs/solution_summary.csv', index=False)
        
        with open('logs/solution_summary.txt', 'w') as f:
            f.write(f"Optimal Value: {model.ObjVal:.2f}\n")
            f.write(f"Number of Periods: {num_periods}\n")
            f.write(f"Standard Aircraft Cost: {std_cost:.2f}\n")
            f.write(f"New Aircraft Cost: {rental_cost:.2f}\n")
            f.write(f"Overtime Cost: {overtime_cost_total:.2f}\n")
        
        print(f"\n✓ Solution written to logs/solution_summary.csv and logs/solution_summary.txt")
        
        return model.ObjVal
    
    elif model.Status == GRB.INFEASIBLE:
        print(f"\n{'='*80}")
        print(f"optimal_value = INFEASIBLE")
        print("❌ Problem is infeasible")
        print(f"{'='*80}")
        
        print("\nComputing IIS...")
        model.computeIIS()
        print("Infeasible constraints:")
        for c in model.getConstrs():
            if c.IISConstr:
                print(f"  {c.ConstrName}")
        return None
    
    elif model.Status == GRB.UNBOUNDED:
        print(f"\n{'='*80}")
        print(f"optimal_value = UNBOUNDED")
        print("❌ Problem is unbounded")
        print(f"{'='*80}")
        return None
    
    else:
        print(f"\n{'='*80}")
        print(f"optimal_value = ERROR")
        print(f"❌ Solver error, status code: {model.Status}")
        print(f"{'='*80}")
        return None


def main():
    """Main function"""
    print("=" * 80)
    print("Airline Fleet Planning Problem Solver")
    print("=" * 80)
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Load data
    print("\n[1] Loading data from CSV files...")
    df_periods, df_parameters = load_data()
    print(f"    ✓ Loaded {len(df_periods)} periods")
    print(f"    ✓ Loaded {len(df_parameters.columns)} parameters")
    
    # Build model
    print("\n[2] Building optimization model...")
    model, standard_aircraft, rental_aircraft, overtime_hours, params, num_periods = build_model(df_periods, df_parameters)
    print(f"    ✓ Model built with {model.NumVars} variables and {model.NumConstrs} constraints")
    
    # Solve
    print("\n[3] Solving...")
    model.optimize()
    
    # Print results
    print("\n[4] Results:")
    optimal_value = print_results(model, standard_aircraft, rental_aircraft, overtime_hours, params, num_periods, df_periods)
    
    print("\n" + "=" * 80)
    print("Solver completed")
    print("=" * 80)


if __name__ == "__main__":
    main()

