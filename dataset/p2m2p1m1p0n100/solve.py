import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os


def solve_knapsack(json_file_path, csv_file_path, output_dir):
    """
    Solve the 0-1 knapsack problem based on JSON configuration and CSV weight files
    Requirement: Total weight >= W, and minimize total weight

    Parameters:
    json_file_path: Path to the JSON configuration file
    csv_file_path: Path to the CSV weight file
    output_dir: Path to the output directory
    """

    # 1. Read JSON configuration file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Extract parameters
    I = config["parameters"]["I"]  # Number of items
    W = config["parameters"]["W"]  # Knapsack capacity lower bound

    print(f"Problem type: {config['problem_type']}")
    print(f"Number of items: {I}")
    print(f"Weight lower bound: {W}")
    print(f"Optimization goal: Minimize total weight (Total weight >= {W})")

    # 2. Read CSV weight file
    weights_df = pd.read_csv(csv_file_path)

    # Ensure data column names are correct
    if len(weights_df.columns) >= 2:
        # Assume first column is item ID, second is weight
        weights_df.columns = ['item_id', 'weight']

    print(f"Read weight data for {len(weights_df)} items")

    # Extract weight data
    weights = weights_df['weight'].values
    item_ids = weights_df['item_id'].values

    # 3. Create Gurobi model
    model = gp.Model("01_Knapsack_Minimize")

    # 4. Create decision variables - 0-1 variables indicating whether each item is selected
    x = model.addVars(I, vtype=GRB.BINARY, name="x")

    # 5. Set objective function - minimize total weight
    model.setObjective(gp.quicksum(weights[i] * x[i] for i in range(I)), GRB.MINIMIZE)

    # 6. Add constraints - total weight not less than W
    model.addConstr(gp.quicksum(weights[i] * x[i] for i in range(I)) >= W, "weight_lower_bound")

    # 7. Solve model
    model.optimize()

    # 8. Output results
    if model.status == GRB.OPTIMAL:
        print("\n=== Solution Results ===")
        print(f"Optimal objective value: {model.objVal}")
        print(f"Weight lower bound: {W}")

        # Get selected item indices
        selected_indices = [i for i in range(I) if x[i].X > 0.5]
        print(f"Number of selected items: {len(selected_indices)}")

        # Get selected item IDs
        selected_item_ids = [item_ids[i] for i in selected_indices]

        # Output selected item information (first 10)
        print("\nSelected items (first 10):")
        for i in selected_indices[:10]:
            print(f"  Item {item_ids[i]}: Weight = {weights[i]}")

        if len(selected_indices) > 10:
            print(f"  ... and {len(selected_indices) - 10} other items")

        # 9. Save results to CSV file
        output_file = os.path.join(output_dir, "p2m2p1m1p0n100_solve.csv")
        result_df = pd.DataFrame(selected_item_ids, columns=["item_id"])
        result_df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")

    elif model.status == GRB.INFEASIBLE:
        print("Problem has no feasible solution!")
        print("Possible reason: Total weight of all items is less than the required lower bound W")

    else:
        print(f"Solving failed, status code: {model.status}")



if __name__ == "__main__":
    json_file = "path_to_your_file/p2m2p1m1p0n100/instance.json"  # Replace with your JSON file path
    csv_file = "path_to_your_file/p2m2p1m1p0n100/data/weight.csv"  # Replace with your CSV file path
    output_directory = "path_to_your_file/p2m2p1m1p0n100"
    os.makedirs(output_directory, exist_ok=True)
    solve_knapsack(json_file, csv_file, output_directory)