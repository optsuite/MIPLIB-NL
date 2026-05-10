import json
import pandas as pd
from gurobipy import Model, GRB
import os
from collections import defaultdict


def solve_set_cover(json_config_path):
    """
    Solve the Set Cover problem (stop immediately once a solution with objective value <= 41 is found)
    """
    # --------------------------
    # 1. Read JSON configuration and parse parameters
    # --------------------------
    if not os.path.exists(json_config_path):
        print(f"Error: JSON configuration file {json_config_path} does not exist")
        return

    with open(json_config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    I = config.get("parameters", {}).get("I")
    s1_file_path = config.get("files", {}).get("files 1", {}).get("path")

    if I is None or s1_file_path is None:
        print("Error: JSON configuration file missing 'parameters.I' or 'files.files 1.path' fields")
        return
    if not os.path.exists(s1_file_path):
        print(f"Error: Set data file {s1_file_path} does not exist")
        return

    # --------------------------
    # 2. Read S1.csv data and preprocess
    # --------------------------
    s1_df = pd.read_csv(s1_file_path, index_col=0)
    integer_columns = [str(col) for col in s1_df.columns]
    required_integers = [str(i) for i in range(1, I + 1)]
    missing_integers = set(required_integers) - set(integer_columns)
    if missing_integers:
        print(f"Warning: S1.csv is missing some integer columns. Missing integers: {sorted(missing_integers)}")
        return

    # Organize set data (use set to store covered integers)
    set_coverage = {}
    for set_name in s1_df.index:
        covered = {int(col) for col in s1_df.columns if s1_df.loc[set_name, col] == 1}
        set_coverage[set_name] = covered

    # Preprocessing: Remove redundant sets
    set_names = list(set_coverage.keys())
    redundant_sets = set()
    for i in range(len(set_names)):
        if set_names[i] in redundant_sets:
            continue
        a_cover = set_coverage[set_names[i]]
        for j in range(len(set_names)):
            if i == j or set_names[j] in redundant_sets:
                continue
            b_cover = set_coverage[set_names[j]]
            if a_cover.issubset(b_cover):
                redundant_sets.add(set_names[i])
                break

    # Remove redundant sets
    for s in redundant_sets:
        del set_coverage[s]
    set_names = list(set_coverage.keys())  # Update set_names after removing redundant sets
    num_sets = len(set_coverage)
    print(
        f"Data preprocessing completed: Original sets {len(set_names) + len(redundant_sets)}, redundant sets removed {len(redundant_sets)}, remaining sets {num_sets}")
    if num_sets == 0:
        print("Error: All sets are redundant, cannot cover target integers")
        return

    # --------------------------

    # --------------------------
    # 4. Build Gurobi model
    # --------------------------
    model = Model("Set_Cover_Problem")
    model.Params.LogToConsole = 1
    model.Params.TimeLimit = 3600
    model.Params.Threads = 8
    model.Params.MIPFocus = 1  # Focus more on finding feasible solutions
    model.Params.Heuristics = 0.8
    model.Params.MIPGap = 0.001
    model.Params.BranchDir = 1

    # Define variables
    x = model.addVars(
        num_sets,
        vtype=GRB.BINARY,
        name=[f"Select_{set_name}" for set_name in set_names]
    )


    # Objective function
    model.setObjective(x.sum(), GRB.MINIMIZE)

    # Add constraints
    integer_to_sets = defaultdict(list)
    for idx, name in enumerate(set_names):
        for integer in set_coverage[name]:
            integer_to_sets[integer].append(idx)

    for integer in range(1, I + 1):
        if integer not in integer_to_sets:
            print(f"Error: Integer {integer} is not covered by any set, problem unsolvable")
            model.dispose()
            return
        model.addConstr(
            x.sum(integer_to_sets[integer]) >= 1,
            name=f"Cover_Integer_{integer}"
        )

    # --------------------------
    # 5. Define callback function: stop once a solution with objective value <= 23 is found
    # --------------------------
    early_stop_flag = [False]  # Use a list to allow modification inside callback
    early_stop_objval = [None]  # Save the objective value when stopping early

    def mycallback(model, where):
        if where == GRB.Callback.MIPSOL:
            # Get the objective value of the current solution
            objval = model.cbGet(GRB.Callback.MIPSOL_OBJ)
            if objval <= 23:
                print(f"\n🎯 Found solution with objective value <= 23: {objval}, stopping solving")
                early_stop_flag[0] = True
                early_stop_objval[0] = objval
                model.terminate()

    # --------------------------
    # 6. Solve model (using callback function)
    # --------------------------
    print("\nStarting to solve... (stop immediately once a solution with objective value <= 23 is found)")
    model.optimize(mycallback)

    # --------------------------
    # 7. Result processing and output table
    # --------------------------
    def output_selection_results():
        """Output the table of set selection results"""
        # Create result DataFrame
        result_data = []
        for idx, set_name in enumerate(set_names):
            is_selected = 1 if x[idx].x > 0.5 else 0
            result_data.append({
                'Set Name': set_name,
                'Selected': is_selected,
                'Covered Integer Count': len(set_coverage[set_name]),
                'Covered Integer List': sorted(list(set_coverage[set_name]))
            })

        # Create DataFrame
        result_df = pd.DataFrame(result_data)

        # Sort by whether selected, selected ones first
        result_df = result_df.sort_values(['Selected', 'Set Name'], ascending=[False, True])

        # Output table information
        selected_count = result_df['Selected'].sum()
        print(f"\n📊 Set selection status table (Total {len(result_df)} sets, {selected_count} selected):")
        print(result_df[['Set Name', 'Selected', 'Covered Integer Count']].head(20))

        # Save to CSV file
        output_csv_path = json_config_path.replace('.json', '_selection_results.csv')
        result_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        print(f"\n💾 Detailed results saved to: {output_csv_path}")

        # Verify coverage
        covered_check = set()
        selected_sets = [set_names[idx] for idx in range(num_sets) if x[idx].x > 0.5]
        for set_name in selected_sets:
            covered_check.update(set_coverage[set_name])

        if covered_check == set(range(1, I + 1)):
            print("\n✅ Coverage verification: All integers have been covered")
        else:
            missing = sorted(set(range(1, I + 1)) - covered_check)
            print(f"\n⚠️  Coverage warning: Some integers not covered, missing: {missing}")

        return result_df

    # Output results based on solution status
    if model.status == GRB.OPTIMAL:
        obj_val = model.objVal
        print(f"\n✅ Solving completed: Found global optimal solution, objective value = {obj_val}")
        output_selection_results()

    elif model.status == GRB.INTERRUPTED and early_stop_flag[0]:
        obj_val = early_stop_objval[0]
        print(f"\n✅ Solving interrupted: Found solution with objective value <= 41, objective value = {obj_val}")
        output_selection_results()

    elif model.status == GRB.TIME_LIMIT:
        print(f"\n⏱️  Solving timeout (time limit: {model.Params.TimeLimit} seconds)")
        if model.solCount > 0:
            print(f"Current best solution: Number of selected sets = {int(model.objVal)}")
            output_selection_results()
        else:
            print("No feasible solution found")

    else:
        print(f"\n❌ Solving failed, model status: {model.status} ({GRB.statusName[model.status]})")

    model.dispose()


if __name__ == "__main__":
    JSON_CONFIG_PATH = "path_to_your_file/glass-sc/glass-sc.json"
    solve_set_cover(JSON_CONFIG_PATH)