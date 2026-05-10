import json
import csv
import re
from gurobipy import Model, GRB, quicksum

print("=" * 80)
print("Forest Harvest Planning Optimization Problem Solver")
print("=" * 80)

# ========== 1. Read parameters and data ==========
print("\n[Step 1] Reading parameter and data files...")

# Read instance.json to get parameters
with open('instance.json', 'r', encoding='utf-8') as f:
    instance = json.load(f)

M = instance['parameters']['M']  # Number of harvest units
T = instance['parameters']['T']  # Number of batches
N1 = instance['parameters']['N1']  # Harvest volume smoothing parameter (lower limit multiplier)
N2 = instance['parameters']['N2']  # Harvest volume smoothing parameter (upper limit multiplier)

print(f"  Parameters: M={M} (harvest units), T={T} (batches), N1={N1}, N2={N2}")

# Read R.csv (Revenue data)
revenue = {}  # {(unit, batch): revenue_value}
with open('data/R.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        unit = int(row['unit'])
        for batch in range(T):
            batch_key = f'batch_{batch}'
            revenue[(unit, batch)] = float(row[batch_key])

print(f"  Read R.csv: {len(revenue)} revenue data points")

# Read C1.csv (Mutually exclusive activity list)
mutually_exclusive_groups = []
with open('data/C1.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        activities = []
        for item in row:
            # Parse (i,j) format
            match = re.match(r'\((\d+),(\d+)\)', item.strip('"'))
            if match:
                unit = int(match.group(1))
                batch = int(match.group(2))
                activities.append((unit, batch))
        if activities:
            mutually_exclusive_groups.append(activities)

print(f"  Read C1.csv: {len(mutually_exclusive_groups)} groups of mutually exclusive activities")

# Read C2.csv (Harvest volume data)
harvest_volume = {}  # {(unit, batch): volume}
with open('data/C2.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        unit = int(row['unit'])
        for batch in range(T):
            batch_key = f'batch_{batch}'
            harvest_volume[(unit, batch)] = float(row[batch_key])

print(f"  Read C2.csv: {len(harvest_volume)} harvest volume data points")

# Read C3.csv (Ecological constraints)
ecological_constraints = []
with open('data/C3.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    for row in reader:
        triples = []
        for item in row:
            # Parse (y,i,j) format
            match = re.match(r'\(([+-]?\d+\.?\d*),(\d+),(\d+)\)', item.strip('"'))
            if match:
                y = float(match.group(1))
                unit = int(match.group(2))
                batch = int(match.group(3))
                triples.append((y, unit, batch))
        if triples:
            ecological_constraints.append(triples)

print(f"  Read C3.csv: {len(ecological_constraints)} ecological constraints")

# ========== 2. Build optimization model ==========
print("\n[Step 2] Building Gurobi optimization model...")

model = Model("ForestHarvestPlanning")
model.setParam('OutputFlag', 1)  # Show solution process
model.setParam('LogToConsole', 1)

# Decision variables: x[i][j] = 1 means harvest unit i in batch j, otherwise 0
x = {}
for i in range(M):
    for j in range(T):
        x[i, j] = model.addVar(vtype=GRB.BINARY, name=f'x_{i}_{j}')

print(f"  Created {M * T} binary decision variables")

# Objective function: Maximize total revenue
obj = quicksum(revenue.get((i, j), 0.0) * x[i, j] 
               for i in range(M) for j in range(T))
model.setObjective(obj, GRB.MAXIMIZE)
print("  Set objective function: Maximize total revenue")

# ========== 3. Add constraints ==========
print("\n[Step 3] Adding constraints...")

# Constraint 1: Mutually exclusive activity constraints (C1.csv)
# For each group of mutually exclusive activities, select at most one
constraint_count = 0
for group_idx, group in enumerate(mutually_exclusive_groups):
    model.addConstr(
        quicksum(x[unit, batch] for (unit, batch) in group 
                 if (unit, batch) in x)
        <= 1,
        name=f'MutualExclusive_{group_idx}'
    )
    constraint_count += 1

print(f"  Added {constraint_count} mutually exclusive activity constraints")

# Constraint 2: Harvest volume smoothing constraints
# For batches, total harvest volume must be >= N1 * previous batch and <= N2 * previous batch
# Define auxiliary variable H[j] for total harvest volume of batch j
H = {}
for j in range(T):
    H[j] = quicksum(harvest_volume.get((i, j), 0.0) * x[i, j] 
                    for i in range(M))

# Add smoothing constraints
smoothing_count = 0
for j in range(2, T ):  # Batches 2 to T-1
    # H[j] >= N1 * H[j-1]
    model.addConstr(H[j] >= N1 * H[j - 1], 
                    name=f'Smoothing_Lower_{j}')
    # H[j] <= N2 * H[j-1]
    model.addConstr(H[j] <= N2 * H[j - 1],
                    name=f'Smoothing_Upper_{j}')
    smoothing_count += 2

print(f"  Added {smoothing_count} harvest volume smoothing constraints")

# Constraint 3: Ecological balance constraints (C3.csv)
# For each ecological indicator, net impact must be non-negative
eco_count = 0
for eco_idx, triples in enumerate(ecological_constraints):
    # Calculate net impact: sum(y * x[i][j])
    net_impact = quicksum(y * x[unit, batch] 
                          for y, unit, batch in triples 
                          if (unit, batch) in x)
    model.addConstr(net_impact >= 0, 
                    name=f'Ecological_{eco_idx}')
    eco_count += 1

print(f"  Added {eco_count} ecological balance constraints")

total_constraints = constraint_count + smoothing_count + eco_count
print(f"\n  Total: {total_constraints} constraints")

# ========== 4. Solve model ==========
print("\n[Step 4] Starting solution...")
print("-" * 80)

model.optimize()

# ========== 5. Show results ==========
print("\n" + "=" * 80)
print("Solution Results")
print("=" * 80)

if model.status == GRB.OPTIMAL:
    print(f"\n✓ Optimal solution found!")
    print(f"  Optimal Objective (Total Revenue): {model.ObjVal:,.2f}")
    
    # Statistics of harvest decisions
    harvest_decisions = []
    total_harvest_volume_by_batch = [0.0] * T
    
    for i in range(M):
        for j in range(T):
            if x[i, j].x > 0.5:  # Binary variable, >0.5 considered as 1
                harvest_decisions.append((i, j))
                vol = harvest_volume.get((i, j), 0.0)
                total_harvest_volume_by_batch[j] += vol
    
    print(f"\n  Number of harvest decisions: {len(harvest_decisions)}")
    print(f"\n  Total harvest volume by batch:")
    for j in range(T):
        print(f"    Batch {j}: {total_harvest_volume_by_batch[j]:,.2f}")
    
    # Show top 20 harvest decisions
    print(f"\n  Top 20 harvest decisions (Unit, Batch):")
    for idx, (unit, batch) in enumerate(harvest_decisions[:20]):
        rev = revenue.get((unit, batch), 0.0)
        vol = harvest_volume.get((unit, batch), 0.0)
        print(f"    ({unit:3d}, {batch}): Revenue={rev:10.2f}, Volume={vol:8.2f}")
    
    if len(harvest_decisions) > 20:
        print(f"    ... and {len(harvest_decisions) - 20} more decisions")
    
    # Validation of constraints
    print(f"\n  Constraint Validation:")
    print(f"    - Mutually exclusive constraints: {constraint_count}")
    print(f"    - Smoothing constraints: {smoothing_count}")
    print(f"    - Ecological constraints: {eco_count}")
    
    # Calculate revenue by batch
    revenue_by_batch = [0.0] * T
    for i, j in harvest_decisions:
        revenue_by_batch[j] += revenue.get((i, j), 0.0)
    
    print(f"\n  Revenue by batch:")
    for j in range(T):
        print(f"    Batch {j}: {revenue_by_batch[j]:,.2f}")
    
elif model.status == GRB.INFEASIBLE:
    print("\n✗ Problem is infeasible!")
    print("  Attempting to compute IIS...")
    model.computeIIS()
    print("  Infeasible constraints:")
    for constr in model.getConstrs():
        if constr.IISConstr:
            print(f"    {constr.ConstrName}")
    
elif model.status == GRB.UNBOUNDED:
    print("\n✗ Problem is unbounded!")
    
else:
    print(f"\n? Solution status: {model.status}")
    print(f"  Status code check: {model.status == GRB.OPTIMAL}")

print("\n" + "=" * 80)
print("Solving completed!")
print("=" * 80)