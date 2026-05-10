import gurobipy as gp
from gurobipy import GRB


def solve_basketball_schedule():
    # Parameter configuration
    N1 = 11  # Number of players
    N2 = 4  # Number of quarters
    P = 5  # Number of players on court at the same time

    # Key logic: Substitution occurs every half-quarter, so the number of time slots is twice the number of quarters
    num_slots = N2 * 2

    print(f"Configuration: {N1} players, {N2} quarters ({num_slots} half-quarters), {P} players on court")

    try:
        # 1. Create model
        m = gp.Model("basketball_staffing")

        # Suppress excessive log output (optional)
        m.setParam('OutputFlag', 1)

        # 2. Define variables
        # x[i, t] = 1 indicates player i is on the court at time slot t
        x = m.addVars(N1, num_slots, vtype=GRB.BINARY, name="x")

        # z: Minimum playing time among all players (unit: half-quarter)
        # Since time slots are discrete, playing times must be integers
        z = m.addVar(vtype=GRB.INTEGER, name="min_playing_slots")

        # 3. Add constraints

        # Constraint (1): Exactly P players must be on court in each time slot
        m.addConstrs((x.sum('*', t) == P for t in range(num_slots)), name="capacity_per_slot")

        # Constraint (2): Define z as the minimum playing time
        # For each player i, their total playing time must be >= z
        for i in range(N1):
            m.addConstr(gp.quicksum(x[i, t] for t in range(num_slots)) >= z, name=f"min_play_constraint_{i}")

        # 4. Set objective function
        # Our goal is to maximize this minimum value z
        m.setObjective(z, GRB.MAXIMIZE)

        # 5. Solve
        m.optimize()

        # 6. Output results
        if m.status == GRB.OPTIMAL:
            min_slots = z.x
            min_quarters = min_slots * 0.5
            print("\n" + "=" * 30)
            print(f"[Optimal Solution Found]")
            print(f"Maximized minimum playing time (z): {min_slots:.0f} half-quarters")
            print(f"Converted to quarters: {min_quarters} quarters")
            print("=" * 30)

            print("\nDetailed schedule:")
            for i in range(N1):
                slots_played = sum(x[i, t].x for t in range(num_slots))
                quarters_played = slots_played * 0.5
                schedule_str = "".join(['1' if x[i, t].x > 0.5 else '0' for t in range(num_slots)])
                print(f"Player {i + 1:02d}: {quarters_played:.1f} quarters (sequence: {schedule_str})")

            # Verify total slots
            total_slots = sum(x[i, t].x for i in range(N1) for t in range(num_slots))
            print(f"\nCheck: Total slots should be {num_slots}*{P}={num_slots * P}, actual is {total_slots:.0f}")

        else:
            print("No optimal solution found")

    except gp.GurobiError as e:
        print(f"Gurobi Error Code {e.errno}: {e}")
    except AttributeError:
        print("AttributeError encountered, please check if Gurobi License is correctly installed and activated")


if __name__ == "__main__":
    solve_basketball_schedule()