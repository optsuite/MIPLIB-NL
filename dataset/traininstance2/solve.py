import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import os

def solve_instance(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
    # --- Read Data ---
    try:
        params_df = pd.read_csv(os.path.join(data_dir, "parameters.csv"))
        params = dict(zip(params_df["parameter"], params_df["value"]))
        
        distances_df = pd.read_csv(os.path.join(data_dir, "distances.csv"))
        timetable_df = pd.read_csv(os.path.join(data_dir, "scheduled_timetable.csv"))
        # demand_df = pd.read_csv(os.path.join(data_dir, "passenger_demand.csv")) # Removed as not used in this formulation
    except FileNotFoundError as e:
        print(f"Error reading data: {e}")
        return

    # Extract parameters
    num_trains = int(params["num_trains"])
    num_stations = int(params["num_stations"])
    max_time_horizon = int(params["max_time_horizon"])
    delay_time_step = int(params["delay_time_step"])
    max_delayed_trains = int(params["max_delayed_trains"])
    max_delay_steps_per_train = int(params["max_delay_steps_per_train"])
    train_capacity = int(params["train_capacity"])
    
    # Sets
    trains = sorted(timetable_df["train_id"].unique())
    stations = sorted(timetable_df["station_id"].unique())
    
    # Mappings
    # Distances: (from, to) -> distance (time)
    dist_map = {}
    for _, row in distances_df.iterrows():
        dist_map[(int(row["from_station"]), int(row["to_station"]))] = row["distance"]
        
    # Timetable: (train, station) -> (arr, dep)
    schedule = {}
    for _, row in timetable_df.iterrows():
        schedule[(int(row["train_id"]), int(row["station_id"]))] = (row["scheduled_arrival_time"], row["scheduled_departure_time"])
        
    # Demand: station -> (initial, additional)
    # demand_map = {}
    # for _, row in demand_df.iterrows():
    #     demand_map[int(row["station_id"])] = (row["initial_passengers"], row["additional_passengers_per_train"])

    # --- Model ---
    m = gp.Model("TrainRescheduling")
    
    # Variables
    # d[t]: delay steps for train t
    d = m.addVars(trains, vtype=GRB.INTEGER, lb=0, ub=max_delay_steps_per_train, name="d")
    
    # z[t]: binary, 1 if train t is delayed
    z = m.addVars(trains, vtype=GRB.BINARY, name="z")
    
    # A[t, s], D[t, s]: actual arrival/departure times
    A = m.addVars(trains, stations, vtype=GRB.CONTINUOUS, lb=0, ub=max_time_horizon, name="A")
    D = m.addVars(trains, stations, vtype=GRB.CONTINUOUS, lb=0, ub=max_time_horizon, name="D")
    
    # Unused variables B, U, L removed

    # --- Constraints ---
    
    # 5.1 Timetable Consistency
    for t in trains:
        for s in stations:
            if (t, s) in schedule:
                sched_arr, sched_dep = schedule[(t, s)]
                m.addConstr(A[t, s] >= sched_arr + delay_time_step * d[t], name=f"Arr_Delay_{t}_{s}")
                m.addConstr(D[t, s] >= sched_dep + delay_time_step * d[t], name=f"Dep_Delay_{t}_{s}")
                m.addConstr(A[t, s] <= D[t, s], name=f"Dwell_{t}_{s}")

    # Propagation
    for t in trains:
        for s in stations:
            if s < num_stations:
                if (s, s+1) in dist_map:
                    travel_time = dist_map[(s, s+1)]
                    m.addConstr(A[t, s+1] >= D[t, s] + travel_time, name=f"Prop_{t}_{s}")

    # 5.2 Delay Bounds
    m.addConstr(gp.quicksum(z[t] for t in trains) <= max_delayed_trains, name="MaxDelayedTrains")
    for t in trains:
        m.addConstr(d[t] <= max_delay_steps_per_train * z[t], name=f"Link_d_z_{t}")

    # 5.3 Passenger Balance - Removed as not applicable to Weighted Completion Time formulation
    # (Original constraints relied on passenger flow which is not tracked in this version)

    # 5.4 Capacity and Load - Removed as not applicable
    # (Original constraints relied on passenger load L[t,s])

    # --- Deadlines ---
    try:
        deadlines_df = pd.read_csv(os.path.join(data_dir, "deadlines.csv"))
        for _, row in deadlines_df.iterrows():
            t = int(row["train_id"])
            s = int(row["station_id"])
            deadline = float(row["deadline"])
            if row["type"] == "departure":
                m.addConstr(D[t, s] <= deadline, name=f"Deadline_Dep_{t}_{s}")
            else:
                m.addConstr(A[t, s] <= deadline, name=f"Deadline_Arr_{t}_{s}")
    except FileNotFoundError:
        pass

    # --- Headway Constraints ---
    # Enforce minimum separation between consecutive trains at the same station
    # We apply this to Departure times (and potentially Arrival, but Dep is critical for single track segments)
    
    headway = float(params.get("headway_minutes", 2.0))
    
    # Sort trains by ID (assuming ID order = schedule order)
    sorted_trains = sorted(trains)
    
    for i in range(len(sorted_trains) - 1):
        t_curr = sorted_trains[i]
        t_next = sorted_trains[i+1]
        for s in stations:
            # Departure Headway
            # D[t_next, s] >= D[t_curr, s] + headway
            m.addConstr(D[t_next, s] >= D[t_curr, s] + headway, name=f"Headway_Dep_{t_curr}_{t_next}_{s}")
            
            # Arrival Headway (often required too)
            # A[t_next, s] >= A[t_curr, s] + headway
            m.addConstr(A[t_next, s] >= A[t_curr, s] + headway, name=f"Headway_Arr_{t_curr}_{t_next}_{s}")

    # --- Objective ---
    # Minimize Sum(Weight * Arrival_Time) for specific passenger groups
    
    obj_terms = []
    
    # Re-reading weights as (train, station) -> weight
    try:
        obj_weights_df = pd.read_csv(os.path.join(data_dir, "objective_weights.csv"))
        for _, row in obj_weights_df.iterrows():
            t = int(row["train_id"])
            s = int(row["station_id"])
            w = float(row["weight"])
            if t in trains and s in stations:
                obj_terms.append(w * A[t, s])
    except FileNotFoundError:
         print("Error: objective_weights.csv not found.")
         return
        
    m.setObjective(gp.quicksum(obj_terms), GRB.MINIMIZE)
    
    m.optimize()
    
    if m.status == GRB.OPTIMAL:
        print(f"Optimal Value: {m.objVal}")
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    solve_instance()
