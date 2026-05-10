import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os
import sys


def load_data():
    """Load data from CSV files"""
    try:
        # Read product data
        df_product = pd.read_csv('data/product.csv')
        products = df_product['productID'].tolist()
        
        # Get market columns (all columns except 'productID')
        market_columns = [col for col in df_product.columns if col != 'productID']
        markets = market_columns
        
        # Build contribution matrix: {(product, market): contribution_value}
        contribution = {}
        for _, row in df_product.iterrows():
            product_id = row['productID']
            for market in markets:
                contribution[(product_id, market)] = row[market]
        
        # Read target data
        df_target = pd.read_csv('data/target.csv')
        target_values = df_target.set_index('market')['target'].to_dict()
        
        return products, markets, contribution, target_values
    
    except FileNotFoundError as e:
        print(f"Error: Data file not found - {e}")
        print("Please ensure data/product.csv and data/target.csv exist.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)


def build_model(products, markets, contribution, target_values):
    """Build the optimization model"""
    # Create model
    model = gp.Model("market_share_optimization")
    
    # Suppress Gurobi output for cleaner run (set to 1 to see solver output)
    model.setParam('OutputFlag', 1)
    model.setParam('LogFile', 'logs/solver.log')
    
    # ============== Decision Variables ==============
    # x[j]: Binary variable, 1 if product j is selected, 0 otherwise
    x = model.addVars(products, vtype=GRB.BINARY, name="x")
    
    # s[i]: Slack variable for market i (gap from target)
    s = model.addVars(markets, vtype=GRB.CONTINUOUS, lb=0, name="s")
    
    # ============== Objective Function ==============
    # Minimize total slack across all markets
    obj_expr = gp.quicksum(s[i] for i in markets)
    model.setObjective(obj_expr, GRB.MINIMIZE)
    
    # ============== Constraints ==============
    # For each market: s[i] + sum of contributions from selected products = target[i]
    for market in markets:
        constr_expr = s[market] + gp.quicksum(
            contribution[(product, market)] * x[product] 
            for product in products
        )
        model.addConstr(
            constr_expr == target_values[market],
            name=f"Market_{market}"
        )
    
    return model, x, s


def print_results(model, x, s, products, markets, contribution, target_values):
    """Print detailed solution results"""
    if model.Status == GRB.OPTIMAL:
        print(f"\n{'='*80}")
        print(f"optimal_value = {model.ObjVal:.6f}")
        print(f"objective = {model.ObjVal:.6f}")
        print(f"result = {model.ObjVal:.6f}")
        print(f"{'='*80}")
        
        print("\n" + "=" * 80)
        print("Detailed Solution")
        print("=" * 80)
        
        # Output slack variables
        print("\n[Market Gaps]")
        print(f"{'Market':<10} {'Target':<12} {'Achieved':<12} {'Gap':<12}")
        print("-" * 50)
        
        total_gap = 0
        for market in markets:
            target = target_values[market]
            gap = s[market].X
            actual = target - gap
            total_gap += gap
            print(f"{market:<10} {target:<12.2f} {actual:<12.2f} {gap:<12.2f}")
        
        print("-" * 50)
        print(f"{'Total':<10} {sum(target_values.values()):<12.2f} "
              f"{sum(target_values.values()) - total_gap:<12.2f} {total_gap:<12.2f}")
        
        # Output selected products
        selected_products = [p for p in products if x[p].X > 0.5]
        print(f"\n[Selected Products]")
        print(f"Count: {len(selected_products)}/{len(products)}")
        print(f"Product List: {selected_products}")
        
        # Detailed contribution table
        print(f"\n[Contribution Details]")
        if selected_products:
            contribution_table = []
            for product in selected_products:
                row = {'Product': product}
                for market in markets:
                    row[market] = contribution[(product, market)]
                contribution_table.append(row)
            
            df_contribution = pd.DataFrame(contribution_table)
            print(df_contribution.to_string(index=False))
            
            # Market totals
            print("\nTotal Contribution by Market:")
            for market in markets:
                total_contrib = sum(contribution[(p, market)] for p in selected_products)
                print(f"  {market}: {total_contrib}")
        
        # Output all decision variables (optional)
        print("\n" + "=" * 80)
        print("All Product Selection Status :")
        print("=" * 80)
        for product in products:
            status = "✓ Selected" if x[product].X > 0.5 else "  Not Selected"
            print(f"{product:<6} {status}")
        
        return model.ObjVal
    
    elif model.Status == GRB.INFEASIBLE:
        print("\n" + "=" * 80)
        print("optimal_value = INFEASIBLE")
        print("Problem is infeasible")
        print("=" * 80)
        print("\nTip: Targets may be too high, please check data.")
        
        # Compute IIS
        print("\nComputing Irreducible Inconsistent Subsystem (IIS)...")
        model.computeIIS()
        print("Infeasible constraints:")
        for c in model.getConstrs():
            if c.IISConstr:
                print(f"  {c.ConstrName}")
        return None
                
    elif model.Status == GRB.UNBOUNDED:
        print("\n" + "=" * 80)
        print("optimal_value = UNBOUNDED")
        print("Problem is unbounded")
        print("=" * 80)
        return None
    
    else:
        print("\n" + "=" * 80)
        print(f"optimal_value = ERROR")
        print(f"Solver error, status code: {model.Status}")
        print("=" * 80)
        return None


def main():
    """Main function"""
    print("=" * 80)
    print("Market Share Optimization Problem Solver")
    print("=" * 80)
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Load data
    print("\n[1] Loading data from CSV files...")
    products, markets, contribution, target_values = load_data()
    print(f"    ✓ Loaded {len(products)} products and {len(markets)} markets")
    
    # Build model
    print("\n[2] Building optimization model...")
    model, x, s = build_model(products, markets, contribution, target_values)
    print(f"    Model built with {model.NumVars} variables and {model.NumConstrs} constraints")
    
    # Solve
    print("\n[3] Solving...")
    model.optimize()
    
    # Print results
    print("\n[4] Results:")
    optimal_value = print_results(model, x, s, products, markets, contribution, target_values)
    
    # Write summary to file
    if optimal_value is not None:
        with open('logs/solution_summary.txt', 'w') as f:
            f.write(f"Optimal Value: {optimal_value:.6f}\n")
            f.write(f"Number of Products: {len(products)}\n")
            f.write(f"Number of Markets: {len(markets)}\n")
            selected_products = [p for p in products if x[p].X > 0.5]
            f.write(f"Selected Products: {len(selected_products)}\n")
            f.write(f"Product List: {', '.join(selected_products)}\n")
        print(f"\nSolution summary written to logs/solution_summary.txt")
    
    print("\n" + "=" * 80)
    print("Solver completed")
    print("=" * 80)


if __name__ == "__main__":
    main()

