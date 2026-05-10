import json
import pandas as pd
from gurobipy import Model, GRB, quicksum
import os


def solve_bin_packing(json_config_path, stop_threshold=None):
    """
    Solve bin packing problem: Minimize standard weight h
    Stop early when a solution with objective value <= stop_threshold is found
    """
    # 1. Read JSON configuration and parse parameters
    if not os.path.exists(json_config_path):
        print(f"Error: JSON config file {json_config_path} does not exist")
        return

    with open(json_config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Get parameters
    M = config.get("parameters", {}).get("M")
    I = config.get("parameters", {}).get("I")
    N = config.get("parameters", {}).get("N")

    # Get file paths
    b1_file_path = config.get("files", {}).get("files_1", {}).get("path")
    b2_file_path = config.get("files", {}).get("files_2", {}).get("path")
    weight_file_path = config.get("files", {}).get("files_3", {}).get("path")

    # Check if files exist
    for file_path in [b1_file_path, b2_file_path, weight_file_path]:
        if not os.path.exists(file_path):
            print(f"Error: File {file_path} does not exist")
            return

    # 2. Read data files
    # Read B1.csv - Item and bin compatibility
    b1_df = pd.read_csv(b1_file_path, index_col=0)

    # Read B2.csv - Requirements
    b2_df = pd.read_csv(b2_file_path)

    # Read weight.csv - Item weights
    weight_df = pd.read_csv(weight_file_path, index_col=0)
    weights = weight_df.iloc[:, 0].to_dict()  # First column is weight

    # 3. Build Gurobi model
    model = Model("Bin_Packing_Problem")
    model.Params.LogToConsole = 1
    model.Params.TimeLimit = 3600
    print(b1_df.iloc[3, 4])
    # Define variables
    # x[i,j] = 1 if item i is put into bin j
    x = {}
    for i in range(I):
        for j in range(N):  # Bin numbering from 0 to N
            # Create variable only if marked as 1 in B1.csv
            if b1_df.iloc[i, j] == 1:
                x[i, j] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    # h: Standard weight (objective function)
    h = model.addVar(vtype=GRB.CONTINUOUS, name="h")

    # 4. Add constraints
    # Each item must be placed in exactly one bin
    for i in range(I):
        model.addConstr(
            quicksum(x.get((i, j), 0) for j in range(N + 1)) == 1,
            name=f"Item_{i}_Assignment"
        )

    # Process M requirements
    for k in range(M):
        # Get all (item, bin) combinations for requirement k
        row = b2_df.iloc[k]
        # [Modification 1] Use .iloc[0] to get the first column
        requirement_id = row.iloc[0]

        # Collect all combinations in this requirement
        combinations = []
        for col_idx in range(1, len(row)):
            # [Modification 2] Use .iloc[col_idx] to get column value
            if pd.notna(row.iloc[col_idx]):

                # [Modification 3] Use .iloc[col_idx] as well
                combo_str = str(row.iloc[col_idx]).strip()
                # Parse combination string, assuming format "(Item Bin)"
                if combo_str.startswith('(') and combo_str.endswith(')'):
                    try:
                        # Remove parentheses and split by space (combined with previous modification)
                        combo_content = combo_str[1:-1].split()
                        if len(combo_content) == 2:
                            i_val = int(combo_content[0])
                            j_val = int(combo_content[1])
                            combinations.append((i_val, j_val))
                        else:
                            print(f"Warning: Incorrect combination format: {combo_str}")
                    except ValueError as e:
                        print(f"Warning: Cannot parse combination {combo_str}: {e}")
            # ... Subsequent code remains unchanged
            # Add constraint: Sum of weights of selected items in these combinations must not exceed h
            if combinations:
                # Ensure all combinations are valid
                valid_combinations = []
                for i_val, j_val in combinations:
                    # Check if item index is valid
                    if i_val < 0 or i_val >= I:
                        print(f"Warning: Item index {i_val} out of range [0, {I - 1}], skipping")
                        continue

                    # Check if bin index is valid
                    if j_val < 0 or j_val > N:
                        print(f"Warning: Bin index {j_val} out of range [0, {N}], skipping")
                        continue

                    

                    valid_combinations.append((i_val, j_val))

                if valid_combinations:
                    model.addConstr(
                        quicksum(weights[i] * x[i, j] for i, j in valid_combinations) <= h,
                        name=f"Requirement_{k}"
                    )
                else:
                    print(f"Warning: Requirement {k} has no valid combinations, skipping")
    # 5. Set objective: Minimize h
    model.setObjective(h, GRB.MINIMIZE)

    # 6. Define callback: Stop once a solution with objective <= stop_threshold is found
    early_stop_flag = [False]
    early_stop_objval = [None]

    if stop_threshold is not None:
        def mycallback(model, where):
            if where == GRB.Callback.MIPSOL:
                # Get objective value of current solution
                objval = model.cbGet(GRB.Callback.MIPSOL_OBJ)
                if objval <= stop_threshold:
                    print(f"\n🎯 Found solution with objective <= {stop_threshold}: {objval}, stopping")
                    early_stop_flag[0] = True
                    early_stop_objval[0] = objval
                    model.terminate()

    # 7. Solve model
    print("\nStarting solve...")
    if stop_threshold is not None:
        model.optimize(mycallback)
    else:
        model.optimize()

    # 8. Output assignment result table
    def output_assignment_results():
        """Output table of item assignments"""
        # Create result DataFrame
        result_data = []
        for i in range(I):
            assigned_box = None
            for j in range(N + 1):
                if (i, j) in x and x[i, j].x > 0.5:
                    assigned_box = j
                    break

            result_data.append({
                'Item ID': i,
                'Assigned Bin': assigned_box,
                'Item Weight': weights[i]
            })

        # Create DataFrame
        result_df = pd.DataFrame(result_data)

        # Output table info
        print(f"\n📊 Item assignment table (total {len(result_df)} items):")
        print(result_df)

        # Save to CSV file
        output_csv_path = os.path.join(os.path.dirname(json_config_path), "bppc4-08_assignment.csv")
        result_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 Assignment results saved to: {output_csv_path}")

        return result_df

    # 9. Output solve results
    if model.status == GRB.OPTIMAL:
        obj_val = model.objVal
        print(f"\n✅ Solve complete: Found global optimal solution")
        print(f"📊 Minimum standard weight h = {obj_val}")
        output_assignment_results()

        # Verify requirement satisfaction
        print(f"\n🔍 Requirement verification:")
        for k in range(M):
            row = b2_df.iloc[k]
            combinations = []
            for col_idx in range(1, len(row)):
                if pd.notna(row[col_idx]):
                    combo_str = str(row[col_idx])
                    if combo_str.startswith('(') and combo_str.endswith(')'):
                        try:
                            i_val, j_val = map(int, combo_str[1:-1].split(','))
                            combinations.append((i_val, j_val))
                        except ValueError:
                            pass

            if combinations:
                total_weight = 0
                for i, j in combinations:
                    if (i, j) in x and x[i, j].x > 0.5:
                        total_weight += weights[i]

                print(f"  Requirement {k}: Total Weight = {total_weight}, h = {obj_val}, Satisfied: {total_weight <= obj_val}")

    elif model.status == GRB.INTERRUPTED and early_stop_flag[0]:
        obj_val = early_stop_objval[0]
        print(f"\n✅ Solve interrupted: Found solution with objective <= {stop_threshold}")
        print(f"📊 Current standard weight h = {obj_val}")
        output_assignment_results()

    elif model.status == GRB.TIME_LIMIT:
        print(f"\n⏱️  Solve timed out (Time limit: {model.Params.TimeLimit}s)")
        if model.solCount > 0:
            print(f"Current best solution: h = {model.objVal}")
            output_assignment_results()
        else:
            print("No feasible solution found")

    else:
        print(f"\n❌ Solve failed, model status: {model.status}")

    model.dispose()


if __name__ == "__main__":
    JSON_CONFIG_PATH = "path_to_your_file/bppc6-02/bppc6-02.json"
    # Set stop threshold, stop when a solution with h <= is found
    solve_bin_packing(JSON_CONFIG_PATH, stop_threshold=116)