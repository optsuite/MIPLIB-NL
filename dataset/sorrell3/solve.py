import json
import gurobipy as gp
from gurobipy import GRB
import os

def solve():
    problem_path = "./problem.json"
    
    # Read problem parameters
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    with open(problem_path, 'r', encoding='utf-8') as f:
        problem_data = json.load(f)
    
    params = problem_data['parameters']
    n_bits = params['n_bits']
    lcs_threshold = params['lcs_threshold']
    
    # Generate all binary sequences of length n_bits
    # Represented as strings for easier LCS computation
    sequences = []
    for i in range(2**n_bits):
        # Format integer as binary string, padded with zeros
        seq = format(i, f'0{n_bits}b')
        sequences.append(seq)
        
    num_sequences = len(sequences)
    
    # Helper function to compute LCS length
    def compute_lcs_length(s1, s2):
        m = len(s1)
        n = len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]

    # Initialize Gurobi Model
    model = gp.Model("LCS_Code_Set")
    
    # Setup logging
    log_file = "./logs/log.txt"
    # Ensure spec directory exists
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    model.setParam('LogFile', log_file)
    
    # Create variables
    # x[i] = 1 if sequence i is selected
    x = model.addVars(num_sequences, vtype=GRB.BINARY, name="x")
    
    # Set Objective: Maximize number of selected sequences
    model.setObjective(x.sum(), GRB.MAXIMIZE)
    
    # Add Constraints
    # If LCS(s_i, s_j) >= lcs_threshold, then x_i + x_j <= 1
    # We only need to check pairs (i, j) with i < j
    print("Building constraints (calculating LCS for all pairs)...")
    constraint_count = 0
    for i in range(num_sequences):
        for j in range(i + 1, num_sequences):
            lcs_len = compute_lcs_length(sequences[i], sequences[j])
            if lcs_len >= lcs_threshold:
                model.addConstr(x[i] + x[j] <= 1, name=f"conflict_{i}_{j}")
                constraint_count += 1
                
    print(f"Added {constraint_count} conflict constraints.")
    
    # Optimize
    model.optimize()
    
    # Append results to log file
    with open(log_file, 'a') as f:
        f.write("\n--- Solution ---\n")
        if model.Status == GRB.OPTIMAL:
            f.write(f"Optimal Objective Value: {model.ObjVal}\n")
            f.write("Selected Sequences:\n")
            selected_indices = []
            for i in range(num_sequences):
                if x[i].X > 0.5:
                    selected_indices.append(i)
                    f.write(f"Sequence {i}: {sequences[i]}\n")
            
            # Double check verification (optional but good for log)
            f.write("\nVerification of selected set:\n")
            valid = True
            for i in range(len(selected_indices)):
                for j in range(i + 1, len(selected_indices)):
                    idx1 = selected_indices[i]
                    idx2 = selected_indices[j]
                    l = compute_lcs_length(sequences[idx1], sequences[idx2])
                    # f.write(f"LCS({sequences[idx1]}, {sequences[idx2]}) = {l}\n")
                    if l >= lcs_threshold:
                        valid = False
                        f.write(f"  VIOLATION! LCS({sequences[idx1]}, {sequences[idx2]}) = {l} >= {lcs_threshold}\n")
            if valid:
                f.write("All constraints satisfied.\n")
        else:
            f.write("No optimal solution found.\n")

if __name__ == "__main__":
    solve()
