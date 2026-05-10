import json
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    # Path to the problem file
    problem_path = "./problem.json"
    
    # Read problem parameters
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    # Extract parameters
    # The problem asks for the maximum size of a codeword set with length n_bits
    if 'parameters' not in problem_data or 'n_bits' not in problem_data['parameters']:
        print("Error: 'n_bits' parameter not found in problem.json")
        return

    n_bits = problem_data['parameters']['n_bits']
    print(f"Solving for n_bits = {n_bits}")

    # Initialize Gurobi Model
    m = gp.Model("ErrorCorrectingCode")
    
    # Set log file
    log_file = "./logs/log.txt"
    # Ensure spec directory exists (it should, since this script is in logs/)
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    m.setParam("LogFile", log_file)
    
    # Generate all possible binary sequences of length n_bits
    num_sequences = 1 << n_bits
    sequences = range(num_sequences)
    
    # Create binary variables for each sequence
    # x[i] = 1 if sequence i is selected, 0 otherwise
    x = m.addVars(sequences, vtype=GRB.BINARY, name="x")
    
    # Add constraints based on error detection rules
    # Rule 1: Bit Flip - Hamming distance 1
    # Rule 2: Bit Swap - Hamming distance 2 AND same weight
    
    print("Building constraints...")
    count_constraints = 0
    
    for i in sequences:
        # 1. Bit Flip Constraints
        # Flip each bit position to find neighbors
        for bit in range(n_bits):
            # XOR with 1 shifted by 'bit' positions flips that bit
            j = i ^ (1 << bit)
            
            # Add constraint only if i < j to avoid duplicates
            if i < j:
                m.addConstr(x[i] + x[j] <= 1, name=f"flip_{i}_{j}")
                count_constraints += 1
        
        # 2. Bit Swap Constraints
        # Swap any pair of bits at different positions
        for p1 in range(n_bits):
            for p2 in range(p1 + 1, n_bits):
                # Get bits at positions p1 and p2
                bit1 = (i >> p1) & 1
                bit2 = (i >> p2) & 1
                
                # If bits are different, swapping them creates a new sequence
                if bit1 != bit2:
                    # Create mask to flip both bits
                    mask = (1 << p1) | (1 << p2)
                    j = i ^ mask
                    
                    # Add constraint only if i < j
                    if i < j:
                        m.addConstr(x[i] + x[j] <= 1, name=f"swap_{i}_{j}")
                        count_constraints += 1

    print(f"Added {count_constraints} constraints.")

    # Set Objective: Maximize the number of selected codewords
    m.setObjective(x.sum(), GRB.MAXIMIZE)
    
    # Optimize
    m.optimize()
    
    # Append results to the log file
    with open(log_file, 'a') as f:
        f.write("\n" + "="*50 + "\n")
        f.write("Optimization Results\n")
        f.write("="*50 + "\n")
        
        if m.Status == GRB.OPTIMAL:
            f.write(f"Optimal Objective Value: {m.ObjVal}\n")
            f.write("Selected Codewords:\n")
            
            count = 0
            for i in sequences:
                if x[i].X > 0.5:
                    # Convert integer to binary string
                    binary_str = format(i, f'0{n_bits}b')
                    f.write(f"Index {i}: {binary_str}\n")
                    count += 1
            
            f.write(f"Total Selected: {count}\n")
        else:
            f.write(f"Optimization ended with status: {m.Status}\n")

if __name__ == "__main__":
    solve()
