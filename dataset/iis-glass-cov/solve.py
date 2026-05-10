import json
import pandas as pd
from gurobipy import Model, GRB
import os
from collections import defaultdict


def solve_set_cover(json_config_path):
    """
    Solve Set Cover problem (stop immediately once a solution with objective <= 41 is found)
    """
    # --------------------------
    # 1. Read JSON configuration and parse parameters
    # --------------------------
    if not os.path.exists(json_config_path):
        print(f"Error: JSON config file {json_config_path} does not exist")
        return

    with open(json_config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    I = config.get("parameters", {}).get("I")
    s1_file_path = config.get("files", {}).get("files 1", {}).get("path")

    if I is None or s1_file_path is None:
        print("Error: JSON config file missing 'parameters.I' or 'files.files 1.path' fields")
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
        print(f"Warning: S1.csv missing some integer columns, missing integers: {sorted(missing_integers)}")
        return

    # Organize set data (store covered integers using set)
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
    set_names = list(set_coverage.keys())  # Update set_names to set names after removing redundancies
    num_sets = len(set_coverage)
    print(
        f"Data preprocessing complete: original sets {len(set_names) + len(redundant_sets)}, redundant sets removed {len(redundant_sets)}, remaining {num_sets} sets")
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
            print(f"Error: Integer {integer} is not covered by any set, problem infeasible")
            model.dispose()
            return
        model.addConstr(
            x.sum(integer_to_sets[integer]) >= 1,
            name=f"Cover_Integer_{integer}"
        )

    # --------------------------
    # 5. Define callback function: stop once a solution with objective <= 21 is found
    # --------------------------
    early_stop_flag = [False]  # Use list to modify inside callback
    early_stop_objval = [None]  # Save objective value when stopping early

    def mycallback(model, where):
        if where == GRB.Callback.MIPSOL:
            # Get current solution objective value
            objval = model.cbGet(GRB.Callback.MIPSOL_OBJ)
            if objval <= 21:
                print(f"\n🎯 Found solution with objective <= 21: {objval}, stopping")
                early_stop_flag[0] = True
                early_stop_objval[0] = objval
                model.terminate()

    # --------------------------
    # 6. Solve model (using callback)
    # --------------------------
    print("\nStarting solve... (stop immediately once a solution with objective <= 21 is found)")
    model.optimize(mycallback)

    # --------------------------
    # 7. Result processing and output table
    # --------------------------
    def output_selection_results():
        """Output table of set selection results"""
        # Create result DataFrame
        result_data = []
        for idx, set_name in enumerate(set_names):
            is_selected = 1 if x[idx].x > 0.5 else 0
            result_data.append({
                'Set Name': set_name,
                'Is Selected': is_selected,
                'Covered Integer Count': len(set_coverage[set_name]),
                'Covered Integer List': sorted(list(set_coverage[set_name]))
            })

        # Create DataFrame
        result_df = pd.DataFrame(result_data)

        # Sort by selection status, selected ones first
        result_df = result_df.sort_values(['Is Selected', 'Set Name'], ascending=[False, True])

        # Output table information
        selected_count = result_df['Is Selected'].sum()
        print(f"\n📊 Set selection table (Total {len(result_df)} sets, selected {selected_count}):")
        print(result_df[['Set Name', 'Is Selected', 'Covered Integer Count']].head(20))

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
            print("\n✅ Coverage verification: All integers are covered")
        else:
            missing = sorted(set(range(1, I + 1)) - covered_check)
            print(f"\n⚠️  Coverage warning: Some integers not covered, missing: {missing}")

        return result_df

    # Output results based on solve status
    if model.status == GRB.OPTIMAL:
        obj_val = model.objVal
        print(f"\n✅ Solve complete: Global optimal solution found, objective = {obj_val}")
        output_selection_results()

    elif model.status == GRB.INTERRUPTED and early_stop_flag[0]:
        obj_val = early_stop_objval[0]
        print(f"\n✅ Solve interrupted: Found solution with objective <= 41, objective = {obj_val}")
        output_selection_results()

    elif model.status == GRB.TIME_LIMIT:
        print(f"\n⏱️  Solve time limit exceeded (Time limit: {model.Params.TimeLimit}s)")
        if model.solCount > 0:
            print(f"Current best solution: Selected sets count = {int(model.objVal)}")
            output_selection_results()
        else:
            print("No feasible solution found")

    else:
        print(f"\n❌ Solve failed, model status: {model.status} ({GRB.statusName[model.status]})")

    model.dispose()


if __name__ == "__main__":
    JSON_CONFIG_PATH = "path_to_your_file/iis-glass-cov/iis-glass-cov.json"
    solve_set_cover(JSON_CONFIG_PATH)