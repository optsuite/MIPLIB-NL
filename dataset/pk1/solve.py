import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import sys


def load_data():
    """Load data from CSV files"""
    try:
        # Read CSV files
        df_items = pd.read_csv('data/items.csv')
        df_dimensions = pd.read_csv('data/dimensions.csv')
        df_contributions = pd.read_csv('data/contributions.csv')
        
        return df_items, df_dimensions, df_contributions
    
    except FileNotFoundError as e:
        print(f"Error: Data file not found - {e}")
        print("Please ensure data/items.csv, data/dimensions.csv, and data/contributions.csv exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)


def build_model(df_items, df_dimensions, df_contributions):
    """Build the optimization model"""
    
    # Create model
    model = gp.Model("multi_dimensional_project_selection")
    model.setParam('OutputFlag', 1)
    model.setParam('LogFile', 'logs/solver.log')
    
    # ============== Decision Variables ==============
    print("\nCreating decision variables...")
    
    # Main variable: maximum deviation across all dimensions
    max_deviation = model.addVar(lb=0, obj=1.0, vtype=GRB.CONTINUOUS, name='max_deviation')
    
    # Selection variables: binary decision for each project
    selection = {}
    for _, row in df_items.iterrows():
        item_id = row['item_id']
        selection[item_id] = model.addVar(vtype=GRB.BINARY, name=f'select_item_{item_id}')
    
    # Auxiliary variables for absolute value modeling
    positive_deviation = {}
    negative_deviation = {}
    for _, row in df_dimensions.iterrows():
        dim_id = row['dimension_id']
        positive_deviation[dim_id] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f'pos_dev_{dim_id}')
        negative_deviation[dim_id] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f'neg_dev_{dim_id}')
    
    print(f"  Created {1 + len(selection) + len(positive_deviation) + len(negative_deviation)} decision variables")
    
    # ============== Objective Function ==============
    # Minimize the maximum deviation across all dimensions
    model.setObjective(max_deviation, GRB.MINIMIZE)
    
    # ============== Constraints ==============
    print("\nAdding constraints...")
    
    balance_constrs = 0
    max_dev_constrs = 0
    
    for _, dim_row in df_dimensions.iterrows():
        dim_id = dim_row['dimension_id']
        target = dim_row['target_value']
        
        # Get contributions for this dimension
        dim_contrib = df_contributions[df_contributions['dimension_id'] == dim_id]
        
        # Balance constraint: sum of contributions + pos_dev - neg_dev = target
        model.addConstr(
            gp.quicksum(row['contribution'] * selection[row['item_id']] 
                       for _, row in dim_contrib.iterrows()) + 
            positive_deviation[dim_id] - negative_deviation[dim_id] == target,
            name=f'balance_dim_{dim_id}'
        )
        balance_constrs += 1
        
        # Max deviation constraint: max_deviation >= pos_dev
        model.addConstr(
            max_deviation >= positive_deviation[dim_id],
            name=f'max_dev_pos_{dim_id}'
        )
        max_dev_constrs += 1
        
        # Max deviation constraint: max_deviation >= neg_dev
        model.addConstr(
            max_deviation >= negative_deviation[dim_id],
            name=f'max_dev_neg_{dim_id}'
        )
        max_dev_constrs += 1
    
    print(f"  Added {balance_constrs + max_dev_constrs} constraints")
    print(f"    - Balance constraints: {balance_constrs}")
    print(f"    - Max deviation constraints: {max_dev_constrs}")
    
    return model, max_deviation, selection, positive_deviation, negative_deviation


def print_results(model, max_deviation, selection, positive_deviation, negative_deviation,
                 df_items, df_dimensions, df_contributions):
    """Print detailed solution results"""
    
    if model.Status == GRB.OPTIMAL:
        max_dev_value = max_deviation.X
        
        print(f"\n{'='*80}")
        print(f"optimal_value = {max_dev_value:.6f}")
        print(f"objective = {max_dev_value:.6f}")
        print(f"result = {max_dev_value:.6f}")
        print(f"{'='*80}")
        
        # Get selected items
        selected_items = [item_id for item_id, var in selection.items() if var.X > 0.5]
        
        print("\n" + "=" * 80)
        print("Detailed Solution")
        print("=" * 80)
        
        print(f"\n[Selected Projects]")
        print(f"Total selected: {len(selected_items)}/{len(df_items)} ({len(selected_items)/len(df_items)*100:.1f}%)")
        print(f"Selected project IDs: {sorted(selected_items)}")
        
        # Show dimension balance
        print(f"\n[Dimension Balance]")
        print(f"{'Dimension':<15} {'Target':<10} {'Achieved':<12} {'Deviation':<12} {'Status':<8}")
        print("-" * 60)
        
        max_actual_dev = 0
        dimension_details = []
        
        for _, dim_row in df_dimensions.iterrows():
            dim_id = dim_row['dimension_id']
            dim_name = dim_row['dimension_name']
            target = dim_row['target_value']
            
            # Calculate achieved value
            dim_contrib = df_contributions[df_contributions['dimension_id'] == dim_id]
            achieved = sum(
                row['contribution'] * selection[row['item_id']].X
                for _, row in dim_contrib.iterrows()
            )
            
            deviation = abs(achieved - target)
            max_actual_dev = max(max_actual_dev, deviation)
            status = "Perfect" if deviation < 0.01 else ("Good" if deviation <= max_dev_value else "Check")
            
            print(f"{dim_name:<15} {target:<10.0f} {achieved:<12.2f} {deviation:<12.2f} {status:<8}")
            
            dimension_details.append({
                'dimension_id': dim_id,
                'dimension_name': dim_name,
                'target': target,
                'achieved': achieved,
                'deviation': deviation
            })
        
        print(f"\nActual maximum deviation: {max_actual_dev:.2f}")
        
        # Contribution statistics for selected projects
        print(f"\n[Selected Projects Contribution Statistics]")
        selected_contrib = df_contributions[df_contributions['item_id'].isin(selected_items)]
        
        print(f"Total contributions from selected projects: {len(selected_contrib)}")
        print(f"Contribution value range: [{selected_contrib['contribution'].min():.0f}, {selected_contrib['contribution'].max():.0f}]")
        print(f"Average contribution per dimension: {selected_contrib['contribution'].mean():.1f}")
        
        # Show some selected projects with their contributions
        print(f"\n[Sample Selected Projects]")
        for i, item_id in enumerate(sorted(selected_items)[:5], 1):
            item_row = df_items[df_items['item_id'] == item_id].iloc[0]
            item_contrib = df_contributions[df_contributions['item_id'] == item_id]
            contrib_str = ', '.join([f'D{int(row.dimension_id)}:{row.contribution:.0f}' 
                                    for _, row in item_contrib.head(15).iterrows()])
            print(f"\n  {item_row['item_name']} (ID: {item_id}):")
            print(f"    Contributions: {contrib_str}")
        
        if len(selected_items) > 5:
            print(f"\n  ... and {len(selected_items) - 5} more projects")
        
        # Problem statistics
        print(f"\n[Problem Statistics]")
        print(f"Problem size:")
        print(f"  Total projects (candidates): {len(df_items)}")
        print(f"  Resource dimensions: {len(df_dimensions)}")
        print(f"  Total decision variables: {model.NumVars}")
        print(f"    - Maximum deviation variable: 1")
        print(f"    - Project selection variables: {len(selection)}")
        print(f"    - Auxiliary deviation variables: {len(positive_deviation) + len(negative_deviation)}")
        print(f"  Total constraints: {model.NumConstrs}")
        
        print(f"\nSolution quality:")
        print(f"  Maximum deviation: {max_dev_value:.2f}")
        print(f"  Projects selected: {len(selected_items)}/{len(df_items)} ({len(selected_items)/len(df_items)*100:.1f}%)")
        print(f"  Average deviation per dimension: {sum([d['deviation'] for d in dimension_details])/len(dimension_details):.2f}")
        
        print(f"\nSolving statistics:")
        print(f"  Solution time: {model.Runtime:.2f} seconds")
        if hasattr(model, 'NodeCount'):
            print(f"  Branch-and-bound nodes: {model.NodeCount:.0f}")
        if hasattr(model, 'IterCount'):
            print(f"  Simplex iterations: {model.IterCount:.0f}")
        
        # Write solution to files
        df_selected = df_items[df_items['item_id'].isin(selected_items)][['item_id', 'item_name', 'description']]
        df_selected.to_csv('logs/selected_projects.csv', index=False)
        
        df_dim_details = pd.DataFrame(dimension_details)
        df_dim_details.to_csv('logs/dimension_balance.csv', index=False)
        
        with open('logs/solution_summary.txt', 'w') as f:
            f.write(f"Optimal Value (Max Deviation): {max_dev_value:.2f}\n")
            f.write(f"Projects Selected: {len(selected_items)}/{len(df_items)}\n")
            f.write(f"Selection Rate: {len(selected_items)/len(df_items)*100:.1f}%\n")
            f.write(f"Selected Project IDs: {sorted(selected_items)}\n")
        
        print(f"\nSolution written to logs/selected_projects.csv, logs/dimension_balance.csv, and logs/solution_summary.txt")
        
        return max_dev_value
    
    elif model.Status == GRB.INFEASIBLE:
        print(f"\n{'='*80}")
        print(f"optimal_value = INFEASIBLE")
        print("Problem is infeasible")
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
        print("Problem is unbounded")
        print(f"{'='*80}")
        return None
    
    else:
        print(f"\n{'='*80}")
        print(f"optimal_value = ERROR")
        print(f"Solve error, status code: {model.Status}")
        print(f"{'='*80}")
        return None


def main():
    """Main function"""
    print("=" * 80)
    print("Multi-Dimensional Project Selection Problem Solver (pk1)")
    print("=" * 80)
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Load data
    print("\n[1] Loading data from CSV files...")
    df_items, df_dimensions, df_contributions = load_data()
    print(f"    Loaded {len(df_items)} projects")
    print(f"    Loaded {len(df_dimensions)} dimensions")
    print(f"    Loaded {len(df_contributions)} contribution entries")
    
    # Build model
    print("\n[2] Building optimization model...")
    model, max_deviation, selection, positive_deviation, negative_deviation = build_model(
        df_items, df_dimensions, df_contributions
    )
    print(f"    Model built with {model.NumVars} variables and {model.NumConstrs} constraints")
    
    # Solve
    print("\n[3] Solving...")
    model.optimize()
    
    # Print results
    print("\n[4] Results:")
    optimal_value = print_results(
        model, max_deviation, selection, positive_deviation, negative_deviation,
        df_items, df_dimensions, df_contributions
    )
    
    print("\n" + "=" * 80)
    print("Solver completed")
    print("=" * 80)


if __name__ == "__main__":
    main()

