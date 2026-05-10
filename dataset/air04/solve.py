import json
import pandas as pd
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Load problem configuration
    problem_path = "./problem.json"
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    # Parse data file paths
    pairing_costs_path = problem_data['files']['pairing_costs']['path']
    pairing_flights_path = problem_data['files']['pairing_flights']['path']

    # Read data
    # Assuming paths in problem.json are relative to the problem directory
    # Since we run from the problem directory, these paths should be valid directly
    df_costs = pd.read_csv(pairing_costs_path)
    df_flights = pd.read_csv(pairing_flights_path)

    # Data processing
    # Create a dictionary for costs: pairing_id -> cost
    costs = dict(zip(df_costs['pairing_id'], df_costs['cost']))
    
    # Create a mapping from flight to pairings: flight_id -> list of pairing_ids
    # This helps in building constraints efficiently
    flight_to_pairings = {}
    
    # Get all unique flights and pairings
    all_flights = set(df_flights['flight_id'].unique())
    all_pairings = set(df_costs['pairing_id'].unique())

    # Group by flight_id to get list of pairings for each flight
    grouped = df_flights.groupby('flight_id')['pairing_id'].apply(list)
    flight_to_pairings = grouped.to_dict()

    # Initialize Gurobi Model
    model = gp.Model("CrewScheduling")
    
    # Set log file
    log_file = "./logs/log.txt"
    model.setParam('LogFile', log_file)

    # Create variables
    # x[j] = 1 if pairing j is selected
    x = model.addVars(all_pairings, vtype=GRB.BINARY, name="x")

    # Set Objective
    model.setObjective(gp.quicksum(costs[j] * x[j] for j in all_pairings), GRB.MINIMIZE)

    # Add Constraints
    # Each flight must be covered exactly once
    for flight_id in all_flights:
        if flight_id in flight_to_pairings:
            pairings_covering_flight = flight_to_pairings[flight_id]
            model.addConstr(gp.quicksum(x[j] for j in pairings_covering_flight) == 1, name=f"cover_flight_{flight_id}")
        else:
            # This case should ideally not happen if data is consistent, 
            # but if a flight is not covered by any pairing, the problem is infeasible.
            print(f"Warning: Flight {flight_id} is not covered by any pairing.")
            # We can either raise an error or add an infeasible constraint
            # model.addConstr(0 == 1, name=f"infeasible_flight_{flight_id}")

    # Optimize
    model.optimize()

    # Output result summary (optional, but good for debugging)
    if model.status == GRB.OPTIMAL:
        print(f"Optimal Objective Value: {model.objVal}")
        # You might want to save the solution to a file if needed
    else:
        print("Optimization was not successful.")

if __name__ == "__main__":
    solve()
