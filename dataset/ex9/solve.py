import sys
import json
import os
import csv
import gurobipy as gp
from gurobipy import GRB

def solve():
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)

    n = problem_data['parameters']['n']
    # Handle data path. problem.json says "./data/numbers.csv"
    data_path = problem_data['files']['numbers']['path']
    
    pieces = []
    with open(data_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pieces.append({
                'id': int(row['piece_id']),
                'top': int(row['top_edge']),
                'right': int(row['right_edge']),
                'bottom': int(row['bottom_edge']),
                'left': int(row['left_edge'])
            })
            
    pieces_dict = {p['id']: p for p in pieces}

    # Helper to get edges after rotation
    # r=0: T, R, B, L
    # r=1: R, B, L, T (90 CCW)
    # r=2: B, L, T, R
    # r=3: L, T, R, B
    def get_edges(piece, r):
        edges = [piece['top'], piece['right'], piece['bottom'], piece['left']]
        return edges[r:] + edges[:r]

    # Valid tuples (p_id, i, j, r)
    valid_vars = []
    
    # Pre-calculate valid positions for each piece
    for p in pieces:
        pid = p['id']
        zeros = [p['top'], p['right'], p['bottom'], p['left']].count(0)
        
        possible_pos = []
        if zeros == 2: # Corner
            possible_pos = [(0,0), (0,n-1), (n-1,0), (n-1,n-1)]
        elif zeros == 1: # Edge
            # Top row (excl corners)
            possible_pos.extend([(0, j) for j in range(1, n-1)])
            # Bottom row
            possible_pos.extend([(n-1, j) for j in range(1, n-1)])
            # Left col
            possible_pos.extend([(i, 0) for i in range(1, n-1)])
            # Right col
            possible_pos.extend([(i, n-1) for i in range(1, n-1)])
        else: # Internal
            possible_pos = [(i, j) for i in range(1, n-1) for j in range(1, n-1)]
            
        for i, j in possible_pos:
            for r in range(4):
                edges = get_edges(p, r)
                # Check boundary constraints
                valid = True
                if i == 0 and edges[0] != 0: valid = False
                if i == n-1 and edges[2] != 0: valid = False
                if j == 0 and edges[3] != 0: valid = False
                if j == n-1 and edges[1] != 0: valid = False
                
                # Check internal constraints (cannot have 0 on internal edges)
                if i > 0 and edges[0] == 0: valid = False
                if i < n-1 and edges[2] == 0: valid = False
                if j > 0 and edges[3] == 0: valid = False
                if j < n-1 and edges[1] == 0: valid = False
                
                if valid:
                    valid_vars.append((pid, i, j, r))

    # Group vars by position for easier constraint creation
    vars_by_pos = {}
    for v in valid_vars:
        pid, i, j, r = v
        if (i,j) not in vars_by_pos:
            vars_by_pos[(i,j)] = []
        vars_by_pos[(i,j)].append(v)

    # Group vars by piece
    vars_by_piece = {}
    for v in valid_vars:
        pid, i, j, r = v
        if pid not in vars_by_piece:
            vars_by_piece[pid] = []
        vars_by_piece[pid].append(v)

    # Model
    m = gp.Model("puzzle")
    m.setParam('LogFile', './logs/log.txt')
    
    # Variables
    b = m.addVars(valid_vars, vtype=GRB.BINARY, name="b")
    
    # Constraints
    # 1. Each cell has exactly one piece
    for i in range(n):
        for j in range(n):
            if (i,j) in vars_by_pos:
                m.addConstr(gp.quicksum(b[v] for v in vars_by_pos[(i,j)]) == 1, name=f"cell_{i}_{j}")
            else:
                print(f"Warning: No valid pieces for cell ({i},{j})")
                # This would imply infeasibility if we enforce == 1
                
    # 2. Each piece is used exactly once
    for p in pieces:
        pid = p['id']
        if pid in vars_by_piece:
            m.addConstr(gp.quicksum(b[v] for v in vars_by_piece[pid]) == 1, name=f"piece_{pid}")
        else:
            print(f"Warning: Piece {pid} has no valid positions")

    # 3. Adjacency
    # Horizontal
    for i in range(n):
        for j in range(n-1):
            # Right of (i,j) == Left of (i,j+1)
            left_terms = []
            if (i,j) in vars_by_pos:
                for (pid, _i, _j, r) in vars_by_pos[(i,j)]:
                    e = get_edges(pieces_dict[pid], r)[1] # Right
                    left_terms.append(b[(pid, i, j, r)] * e)
            
            right_terms = []
            if (i,j+1) in vars_by_pos:
                for (pid, _i, _j, r) in vars_by_pos[(i,j+1)]:
                    e = get_edges(pieces_dict[pid], r)[3] # Left
                    right_terms.append(b[(pid, i, j+1, r)] * e)
                    
            m.addConstr(gp.quicksum(left_terms) == gp.quicksum(right_terms), name=f"h_adj_{i}_{j}")

    # Vertical
    for i in range(n-1):
        for j in range(n):
            # Bottom of (i,j) == Top of (i+1,j)
            top_terms = []
            if (i,j) in vars_by_pos:
                for (pid, _i, _j, r) in vars_by_pos[(i,j)]:
                    e = get_edges(pieces_dict[pid], r)[2] # Bottom
                    top_terms.append(b[(pid, i, j, r)] * e)
                    
            bottom_terms = []
            if (i+1,j) in vars_by_pos:
                for (pid, _i, _j, r) in vars_by_pos[(i+1,j)]:
                    e = get_edges(pieces_dict[pid], r)[0] # Top
                    bottom_terms.append(b[(pid, i+1, j, r)] * e)
                    
            m.addConstr(gp.quicksum(top_terms) == gp.quicksum(bottom_terms), name=f"v_adj_{i}_{j}")

    # Objective
    m.setObjective(gp.quicksum(b), GRB.MAXIMIZE)
    
    m.optimize()
    
    # Output
    with open('./logs/log.txt', 'a') as log:
        if m.status == GRB.OPTIMAL:
            log.write("\nSolution found!\n")
            print("Solution found!")
            
            solution = {}
            for (pid, i, j, r) in valid_vars:
                if b[(pid, i, j, r)].X > 0.5:
                    solution[(i,j)] = (pid, r)
            
            # Print grid
            print("\nFinal Layout (PieceID_Rotation):")
            log.write("\nFinal Layout (PieceID_Rotation):\n")
            for i in range(n):
                row_str = []
                for j in range(n):
                    if (i,j) in solution:
                        pid, r = solution[(i,j)]
                        row_str.append(f"{pid}_{r}")
                    else:
                        row_str.append("Empty")
                print("\t".join(row_str))
                log.write("\t".join(row_str) + "\n")
        else:
            log.write(f"\nNo optimal solution found. Status: {m.status}\n")
            print(f"No optimal solution found. Status: {m.status}")

if __name__ == "__main__":
    solve()
