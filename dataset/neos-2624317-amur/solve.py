import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import os


def solve_production_planning():
    # -------------------------------------------------------------------------
    # 1. Configure paths and read data
    # -------------------------------------------------------------------------
    data_dir = 'data'

    try:
        df_vars = pd.read_csv(os.path.join(data_dir, 'variable_attributes.csv'))
        df_params = pd.read_csv(os.path.join(data_dir, 'period_parameters.csv'))
        df_periodic = pd.read_csv(os.path.join(data_dir, 'periodic_coefficient_matrix.csv'))
        df_struct = pd.read_csv(os.path.join(data_dir, 'structural_logic_matrix.csv'))
    except FileNotFoundError as e:
        print(f"Error: Cannot find data files. Please ensure CSV files are saved in the '{data_dir}' folder.\nDetails: {e}")
        return

    # Initialize Gurobi model
    model = gp.Model("MultiPeriod_Production_Smoothing")

    # -------------------------------------------------------------------------
    # 2. Define decision variables
    # -------------------------------------------------------------------------
    vars_dict = {}

    print("Creating decision variables...")
    for _, row in df_vars.iterrows():
        name = str(row['Variable_Name'])  # Force to string
        vtype_str = row['Variable_Type']
        lb = row['Lower_Bound']
        ub = row['Upper_Bound']
        obj = row['Objective_Coefficient']

        if vtype_str == 'Integer':
            vtype = GRB.INTEGER
        else:
            vtype = GRB.CONTINUOUS

        if pd.isna(lb): lb = 0.0
        if pd.isna(ub): ub = GRB.INFINITY

        vars_dict[name] = model.addVar(lb=lb, ub=ub, obj=obj, vtype=vtype, name=name)

    model.update()

    # -------------------------------------------------------------------------
    # 3. Add periodic constraints
    # -------------------------------------------------------------------------
    periodic_map = {
        'Resource': {'col': 'Resource_Limit_L_t', 'sense': GRB.LESS_EQUAL},
        'Demand': {'col': 'Cumulative_Demand_D_t', 'sense': GRB.GREATER_EQUAL},
        'MinProd': {'col': 'Min_Production_P_min_t', 'sense': GRB.GREATER_EQUAL},
        'MaxInv': {'col': 'Max_Inventory_I_max_t', 'sense': GRB.LESS_EQUAL}
    }

    print("Building periodic constraints...")
    grouped_coeffs = df_periodic.groupby(['Period_ID', 'Constraint_Group_Type'])

    for _, param_row in df_params.iterrows():
        period = param_row['Period_ID']

        for c_type, config in periodic_map.items():
            if (period, c_type) in grouped_coeffs.groups:
                coeffs = grouped_coeffs.get_group((period, c_type))

                lhs_expr = gp.LinExpr()
                for _, r in coeffs.iterrows():
                    vname = str(r['Variable_Name'])
                    if vname in vars_dict:
                        lhs_expr.add(vars_dict[vname], r['Coefficient'])

                rhs_val = param_row[config['col']]
                constr_name = f"{c_type}_Period_{period}"

                # Ensure name is a string
                model.addLConstr(lhs_expr, config['sense'], rhs_val, name=str(constr_name))

    # -------------------------------------------------------------------------
    # 4. Add structural logic constraints
    # -------------------------------------------------------------------------
    print("Building structural logic constraints...")
    struct_groups = df_struct.groupby('Logic_Constraint_ID')

    for cid, group in struct_groups:
        lhs_expr = gp.LinExpr()

        meta = group.iloc[0]
        rhs_val = meta['RHS_Value']
        sense_str = meta['Sense']

        if sense_str == '<=':
            sense = GRB.LESS_EQUAL
        elif sense_str == '>=':
            sense = GRB.GREATER_EQUAL
        elif sense_str == '=':
            sense = GRB.EQUAL
        else:
            print(f"Warning: Unknown symbol '{sense_str}' in constraint {cid}")
            continue

        for _, r in group.iterrows():
            vname = str(r['Variable_Name'])
            if vname in vars_dict:
                lhs_expr.add(vars_dict[vname], r['Coefficient'])

        # [Critical Fix] Force cast cid to string
        model.addLConstr(lhs_expr, sense, rhs_val, name=str(cid))

    # -------------------------------------------------------------------------
    # 5. Solve and output results
    # -------------------------------------------------------------------------
    print("Starting solution...")
    model.optimize()

    print("\n" + "=" * 50)
    if model.Status == GRB.OPTIMAL:
        print(f"Optimal solution found!")
        print(f"Total Cost Minimized (Objective Value): {model.ObjVal:.4f}")

        print("\nDecision variable selection (non-zero variables):")
        print("-" * 30)
        nonzero_count = 0
        for v in model.getVars():
            if abs(v.X) > 1e-6:
                print(f"{v.VarName}: {v.X}")
                nonzero_count += 1
        print("-" * 30)
        print(f"Total {nonzero_count} variables selected (value > 0).")

    elif model.Status == GRB.INFEASIBLE:
        print("Problem is Infeasible.")
        print("According to the description in instance.json, this is the expected result.")
        print("Computing IIS (Irreducible Inconsistent Subsystem) to analyze conflicts...")
        model.computeIIS()
        model.write("model_conflict.ilp")
        print("Conflict constraints written to 'model_conflict.ilp'.")

    else:
        print(f"Solving finished, status code: {model.Status}")
    print("=" * 50)


if __name__ == "__main__":
    solve_production_planning()