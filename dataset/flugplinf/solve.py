import gurobipy as gp
from gurobipy import GRB
import pandas as pd


def solve_crew_planning():
    # 1. Load data
    # Read task demands (assume task.csv first column is month, second column is demand)
    try:
        df = pd.read_csv('data/task.csv', header=None)
        # Assume data starts from row 0 or 1, adjust based on file content, assume no header or standard format
        # Based on previous file inspection, the first line might be in format "month_1", 8000
        # We extract the last column as demand
        demands = df.iloc[:, -1].tolist()
        # Ensure demands are numeric
        demands = [int(d) for d in demands if str(d).isdigit()]
    except Exception as e:
        print(f"Failed to read CSV, using default data: {e}")
        demands = [8000, 9000, 8000, 10000, 9000, 12000]

    print(f"Monthly task demands: {demands}")

    months = len(demands)
    time_periods = range(months)  # 0 to 5, corresponding to month_1 to month_6

    # 2. Define parameters (parsed from instance.json)
    P_init = 60  # Initial pilots (STM1)
    Cap_reg = 150  # Regular working hours per pilot
    Cost_sal = 2700  # Pilot monthly salary
    Retention = 0.9  # Retention rate (1 - attrition rate 0.1)
    Load_trainee = 100  # Effective working hours reduced by training a new employee
    Cost_hire = 1500  # Hiring/training cost
    Max_hire = 18  # Max hiring per month
    Max_pilots = 75  # Max number of pilots
    Min_pilots = 57  # Min number of pilots
    Max_ot = 20  # Max overtime per person
    Cost_ot = 30  # Overtime rate

    # 3. Create model
    m = gp.Model("Airline_Crew_Planning")

    # 4. Define variables
    # STM: Number of skilled pilots (Integer)
    stm = m.addVars(time_periods, vtype=GRB.INTEGER, name="STM", lb=Min_pilots, ub=Max_pilots)

    # ANM: Number of newly hired pilots (Integer)
    anm = m.addVars(time_periods, vtype=GRB.INTEGER, name="ANM", lb=0, ub=Max_hire)

    # UE: Overtime hours (Continuous)
    ue = m.addVars(time_periods, vtype=GRB.CONTINUOUS, name="UE", lb=0)

    # 5. Set objective function: minimize total cost
    # Total cost = Salary(STM) + Hiring cost(ANM) + Overtime cost(UE)
    m.setObjective(
        gp.quicksum(Cost_sal * stm[t] + Cost_hire * anm[t] + Cost_ot * ue[t] for t in time_periods),
        GRB.MINIMIZE
    )

    # 6. Add constraints

    # Initial state constraint (1st month)
    # Note: According to problem definition, STM1 is currently existing, fixed at 60
    m.addConstr(stm[0] == P_init, name="Init_Pilots")

    for t in time_periods:
        # A. Demand and productivity constraints
        # Regular hours - Training loss + Overtime hours >= Demand
        m.addConstr(
            Cap_reg * stm[t] - Load_trainee * anm[t] + ue[t] >= demands[t],
            name=f"Demand_M{t + 1}"
        )

        # B. Overtime limit constraints
        # Total overtime hours <= 20 * Number of skilled pilots
        m.addConstr(ue[t] <= Max_ot * stm[t], name=f"Overtime_Limit_M{t + 1}")

        # C. Personnel flow constraints (linking t and t+1)
        if t < months - 1:
            # Next month count = 0.9 * This month count + This month hired
            m.addConstr(
                stm[t + 1] == Retention * stm[t] + anm[t],
                name=f"Flow_Balance_M{t + 1}"
            )

    # 7. Solve
    m.optimize()

    # 8. Output results
    if m.status == GRB.OPTIMAL:
        print(f"\nOptimal total cost: {m.objVal:,.2f}")
        print("\nDetailed schedule:")
        print(
            f"{'Month':<6} | {'Pilots (STM)':<12} | {'Hired (ANM)':<12} | {'Overtime (UE)':<14} | {'Demand':<8} | {'Capacity':<8}")
        print("-" * 75)
        for t in time_periods:
            s = stm[t].X
            a = anm[t].X
            u = ue[t].X
            cap = Cap_reg * s - Load_trainee * a + u
            print(f"{t + 1:<6} | {s:<12.0f} | {a:<12.0f} | {u:<14.1f} | {demands[t]:<8} | {cap:<8.1f}")
    else:
        print("Optimal solution not found")


if __name__ == "__main__":
    solve_crew_planning()