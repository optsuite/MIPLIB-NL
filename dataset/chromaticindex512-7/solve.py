import json
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    n = data['parameters']['n']
    
    # Build Graph
    edges = []
    
    for k in range(n):
        base = 12 * k
        
        # Cycle 7: 0-1-2-3-4-5-6-0
        c7_nodes = [0, 1, 2, 3, 4, 5, 6]
        for i in range(len(c7_nodes)):
            u = base + c7_nodes[i]
            v = base + c7_nodes[(i + 1) % len(c7_nodes)]
            if u < v: edges.append((u, v))
            else: edges.append((v, u))
            
        # Cycle 5: 7-9-11-8-10-7
        c5_nodes = [7, 9, 11, 8, 10]
        for i in range(len(c5_nodes)):
            u = base + c5_nodes[i]
            v = base + c5_nodes[(i + 1) % len(c5_nodes)]
            if u < v: edges.append((u, v))
            else: edges.append((v, u))
            
        # Internal connections
        # Common: 0-7, 2-8, 5-10, 6-11
        pairs = [(0, 7), (2, 8), (5, 10), (6, 11)]
        for u_local, v_local in pairs:
            u = base + u_local
            v = base + v_local
            if u < v: edges.append((u, v))
            else: edges.append((v, u))
            
        # Specific connections
        if k == 0:
            # Exception: 4-9
            u, v = base + 4, base + 9
            if u < v: edges.append((u, v))
            else: edges.append((v, u))
        else:
            # Normal: 3-9
            u, v = base + 3, base + 9
            if u < v: edges.append((u, v))
            else: edges.append((v, u))
            
        # Inter-group connections
        # Connect node 4 of group k to node 1 of group k-1 (starting from second group, k=1..n-1)
        if k > 0:
            u = base + 4 # Node 4 of current group
            v = (12 * (k - 1)) + 1 # Node 1 of previous group
            if u < v: edges.append((u, v))
            else: edges.append((v, u))

    # Remove duplicates if any
    edges = list(set(edges))
    # Ensure deterministic ordering: sort by smaller vertex then larger vertex
    edges = [tuple(e) for e in edges]
    edges.sort(key=lambda e: (e[0], e[1]))
    
    # Adjacency list for constraints
    adj = {}
    for u, v in edges:
        if u not in adj: adj[u] = []
        if v not in adj: adj[v] = []
        adj[u].append((u, v))
        adj[v].append((u, v))

    # Gurobi Model
    model = gp.Model("ChromaticIndex")
    model.setParam('LogFile', 'logs/log.txt')
    
    colors = range(4) # 0, 1, 2, 3
    
    # Variables
    # x[e, c] = 1 if edge e uses color c
    x = {}
    for e in edges:
        for c in colors:
            x[e, c] = model.addVar(vtype=GRB.BINARY, name=f"x_{e}_{c}")
            
    # u[c] = 1 if color c is used
    u = {}
    for c in colors:
        u[c] = model.addVar(vtype=GRB.BINARY, name=f"u_{c}")
        
    model.update()
    
    # Objective: Minimize used colors
    model.setObjective(gp.quicksum(u[c] for c in colors), GRB.MINIMIZE)
    
    # Constraints
    
    # 1. Each edge must have exactly one color
    for e in edges:
        model.addConstr(gp.quicksum(x[e, c] for c in colors) == 1, name=f"edge_color_{e}")
        
    # 2. Vertex constraints: Edges incident to v must have distinct colors AND respect u[c]
    # sum(x[e, c] for e in delta(v)) <= u[c]
    for v in adj:
        for c in colors:
            model.addConstr(gp.quicksum(x[e, c] for e in adj[v]) <= u[c], name=f"vertex_{v}_color_{c}")
            
    # Optimize
    model.optimize()
    
    # Output results
    with open('logs/log.txt', 'a', encoding='utf-8') as f:
        f.write("\n\nSolution Analysis\n")
        f.write("=================\n")
        if model.Status == GRB.OPTIMAL:
            obj_val = model.ObjVal
            f.write(f"Optimal Objective Value (Min Colors): {obj_val}\n")
            f.write(f"Colors Used: {sum(u[c].X > 0.5 for c in colors)}\n\n")
            
            f.write("Edge Coloring (First 200 edges):\n")
            for i, e in enumerate(edges):
                if i >= 200:
                    break
                assigned_color = -1
                for c in colors:
                    if x[e, c].X > 0.5:
                        assigned_color = c
                        break
                f.write(f"Edge {e}: Color {assigned_color}\n")
        else:
            f.write("No optimal solution found.\n")
            
if __name__ == "__main__":
    solve()
