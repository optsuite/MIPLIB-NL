import gurobipy as gp
from gurobipy import GRB
import json
import os

def solve():
    problem_path = "./problem.json"
    
    # Read problem parameters
    with open(problem_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    params = data['parameters']
    val_a = params['val_a']
    val_b = params['val_b']
    val_c = params['val_c']
    
    # Define log file path
    log_file = "./logs/log.txt"
    
    # Create Gurobi model
    model = gp.Model("CurrencyExchange")
    
    # Set log file
    model.setParam("LogFile", log_file)
    model.setParam("LogToConsole", 1)
    
    # Create variables
    x = model.addVar(vtype=GRB.INTEGER, lb=1, name="GoldCoins")
    y = model.addVar(vtype=GRB.INTEGER, lb=0, name="PlatinumCoins")
    z = model.addVar(vtype=GRB.INTEGER, lb=0, name="ObsidianCoins")
    
    # Set objective: minimize Gold Coins
    model.setObjective(x, GRB.MINIMIZE)
    
    # Add constraint: Value conservation
    # val_a * x = val_b * y + val_c * z
    model.addConstr(val_a * x == val_b * y + val_c * z, "ValueEq")
    
    # Optimize
    model.optimize()
    
    # Append solution to log file
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n--- Solution Info ---\n")
        if model.status == GRB.OPTIMAL:
            f.write(f"Objective Value (Min Gold Coins): {model.objVal}\n")
            f.write(f"Gold Coins (x): {x.X}\n")
            f.write(f"Platinum Coins (y): {y.X}\n")
            f.write(f"Obsidian Coins (z): {z.X}\n")
        else:
            f.write("No optimal solution found.\n")

if __name__ == "__main__":
    solve()
