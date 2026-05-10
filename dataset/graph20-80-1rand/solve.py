import json
import csv
import os
import sys
import gurobipy as gp
from gurobipy import GRB

def solve():
    # Problem path is expected to be in the current directory
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    # Read problem.json
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    n = problem_data['parameters']['n']
    m = problem_data['parameters']['m']
    
    # Get topology file path
    topo_rel_path = problem_data['files']['network_topology']['path']
    
    edges = []
    if os.path.exists(topo_rel_path):
        with open(topo_rel_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                u = int(row['id1'])
                v = int(row['id2'])
                edges.append((u, v))
    else:
        print(f"Error: Topology file {topo_rel_path} not found.")
        return

    if len(edges) != m:
        print(f"Warning: Number of edges in file ({len(edges)}) does not match parameter m ({m}). Using file count.")
        m = len(edges)

    # Initialize Gurobi Model
    model = gp.Model("MaxIndependentDefenseLines")
    
    # Set log file to logs/log.txt
    log_file = os.path.join("logs", "log.txt")
    # Ensure spec directory exists (it should, as this script is in it, but we are running from parent)
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    model.setParam("LogFile", log_file)
    model.setParam("OutputFlag", 1)

    # Sets
    # We use m as the upper bound for the number of cuts
    K_range = range(m) 
    
    # Variables
    # z[k] = 1 if cut k is active
    z = model.addVars(K_range, vtype=GRB.BINARY, name="z")
    # x[v, k] = 1 if vertex v is in partition 1 of cut k (partition 0 contains node 0)
    x = model.addVars(n, K_range, vtype=GRB.BINARY, name="x")
    # y[e, k] = 1 if edge e is in cut k
    y = model.addVars(len(edges), K_range, vtype=GRB.BINARY, name="y")

    # Objective: Maximize number of active cuts
    model.setObjective(z.sum(), GRB.MAXIMIZE)

    # Constraints
    
    # 1. Edge Disjointness: Each edge belongs to at most one active cut
    for e_idx in range(len(edges)):
        model.addConstr(sum(y[e_idx, k] for k in K_range) <= 1, name=f"EdgeDisjoint_{e_idx}")

    # 2. Cut Definition: Edge is in cut if endpoints are in different partitions
    for k in K_range:
        for e_idx, (u, v) in enumerate(edges):
            # y >= x_u - x_v
            model.addConstr(y[e_idx, k] >= x[u, k] - x[v, k], name=f"CutDef1_{e_idx}_{k}")
            # y >= x_v - x_u
            model.addConstr(y[e_idx, k] >= x[v, k] - x[u, k], name=f"CutDef2_{e_idx}_{k}")

    # 3. Active Cut Validity & 4. Inactive Cut Handling
    for k in K_range:
        # Fix node 0 to partition 0 to break symmetry within the cut
        model.addConstr(x[0, k] == 0, name=f"FixNode0_{k}")
        
        # If z_k=0, then all x must be 0 (inactive cut uses no edges)
        # If z_k=1, x can be 0 or 1
        for v in range(n):
            model.addConstr(x[v, k] <= z[k], name=f"InactiveZero_{v}_{k}")
            
        # If z_k=1, at least one node must be in partition 1 (non-trivial partition)
        # Since node 0 is in partition 0, this ensures both partitions are non-empty
        model.addConstr(x.sum('*', k) >= z[k], name=f"NonTrivial_{k}")

    # 5. Symmetry Breaking: Fill cuts in order
    for k in range(m - 1):
        model.addConstr(z[k] >= z[k+1], name=f"Symmetry_{k}")

    # Optimize
    model.optimize()

    if model.status == GRB.OPTIMAL:
        print(f"Optimal solution found: {model.objVal}")
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    solve()
