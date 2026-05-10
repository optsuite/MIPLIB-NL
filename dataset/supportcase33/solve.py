import gurobipy as gp
from gurobipy import GRB
import json
import csv
import sys
import os
import math

class Logger(object):
    def __init__(self, filename='logs/log.txt'):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def load_data(problem_path):
    with open(problem_path, 'r', encoding='utf-8') as f:
        problem = json.load(f)
    
    base_dir = os.path.dirname(problem_path)
    
    parts = []
    parts_path = os.path.join(base_dir, problem['files']['parts']['path'])
    with open(parts_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            parts.append({
                'id': int(row['id']),
                'demand': float(row['demand']),
                'recovery_time': float(row['recovery_time']),
                'start_time': float(row['start_time']),
                'end_time': float(row['end_time'])
            })
            
    transitions = {}
    trans_path = os.path.join(base_dir, problem['files']['transitions']['path'])
    with open(trans_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            transitions[(int(row['id1']), int(row['id2']))] = float(row['setup_time'])
            
    mutex = []
    mutex_path = os.path.join(base_dir, problem['files']['mutex']['path'])
    with open(mutex_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mutex.append((int(row['id1']), int(row['id2'])))
            
    return problem, parts, transitions, mutex

def solve():
    # Redirect output
    sys.stdout = Logger()
    
    problem_path = "./problem.json"
    if not os.path.exists(problem_path):
        print(f"Error: {problem_path} not found.")
        return

    problem_data, parts, transitions, mutex = load_data(problem_path)
    
    params = problem_data['parameters']
    arms_time = params['arms_time'] # [15, 20]
    max_gap = params['max_gap']
    start_time = params['start_time']
    end_time = params['end_time']
    
    # Create nodes
    # Node structure: (part_id, k)
    nodes = []
    part_nodes = {} # part_id -> list of node indices
    
    for p in parts:
        # Calculate max passes needed. Min arm time is 15.
        # If demand is 10, 1 pass. 20, 2 passes (15+15 > 20).
        # Actually, if demand is 20, arm 1 (20) can do it in 1 pass.
        # But we need to allow flexibility.
        # Hint suggests: 0-8 (1 pass), 9-26 (2 passes), 27-44 (3 passes)
        # Let's check demand to be safe, or just follow the hint logic if it aligns with demand/15.
        # Let's use ceil(demand / 15) as a safe upper bound for passes.
        num_passes = math.ceil(p['demand'] / 15.0)
        # Ensure at least 1 pass if demand > 0
        if num_passes == 0 and p['demand'] > 0:
            num_passes = 1
            
        p_nodes = []
        for k in range(num_passes):
            node_idx = len(nodes)
            nodes.append({'type': 'part', 'part_id': p['id'], 'k': k, 'part_data': p})
            p_nodes.append(node_idx)
        part_nodes[p['id']] = p_nodes

    source_idx = len(nodes)
    sink_idx = source_idx + 1
    nodes.append({'type': 'source'})
    nodes.append({'type': 'sink'})
    
    num_nodes = len(nodes)
    num_parts = len(parts)
    
    # Create Model
    m = gp.Model("RoboticArms")
    
    # Variables
    # x[u, v, i]: Arm i moves from u to v
    x = {}
    # c[u]: Completion time of node u
    c = {}
    # y[p]: Part p is valid
    y = {}
    
    for p in parts:
        y[p['id']] = m.addVar(vtype=GRB.BINARY, name=f"y_{p['id']}")
        
    for u in range(num_nodes):
        if nodes[u]['type'] == 'part':
            c[u] = m.addVar(lb=0, ub=end_time, vtype=GRB.CONTINUOUS, name=f"c_{nodes[u]['part_id']}_{nodes[u]['k']}")
    
    # Arcs
    # Source -> Parts
    # Parts -> Parts
    # Parts -> Sink
    # Source -> Sink (if no parts processed? allowed?)
    
    # Precompute valid arcs to save memory/time
    arcs = []
    for i in range(2): # 2 arms
        # Source -> Part
        for u in range(source_idx): # all part nodes
            x[source_idx, u, i] = m.addVar(vtype=GRB.BINARY, name=f"x_src_{u}_{i}")
            
        # Part -> Sink
        for u in range(source_idx):
            x[u, sink_idx, i] = m.addVar(vtype=GRB.BINARY, name=f"x_{u}_sink_{i}")
            
        # Part -> Part
        for u in range(source_idx):
            for v in range(source_idx):
                if u == v: continue
                # Check if transition exists (u.part -> v.part)
                p_u = nodes[u]['part_id']
                p_v = nodes[v]['part_id']
                
                # If same part, allow any future pass (k_v > k_u)
                # The arm can skip passes (e.g. do pass 0, then pass 2, while another arm does pass 1)
                if p_u == p_v:
                    if nodes[v]['k'] > nodes[u]['k']:
                        x[u, v, i] = m.addVar(vtype=GRB.BINARY, name=f"x_{u}_{v}_{i}")
                else:
                    # Different parts, check transition
                    if (p_u, p_v) in transitions:
                        x[u, v, i] = m.addVar(vtype=GRB.BINARY, name=f"x_{u}_{v}_{i}")

        # Source -> Sink (Empty schedule)
        x[source_idx, sink_idx, i] = m.addVar(vtype=GRB.BINARY, name=f"x_src_sink_{i}")

    m.update()
    
    # Constraints
    
    # 1. Flow Conservation
    for i in range(2):
        # Out of Source
        m.addConstr(gp.quicksum(x[source_idx, v, i] for v in range(num_nodes) if (source_idx, v, i) in x) == 1, name=f"flow_out_src_{i}")
        # Into Sink
        m.addConstr(gp.quicksum(x[u, sink_idx, i] for u in range(num_nodes) if (u, sink_idx, i) in x) == 1, name=f"flow_in_sink_{i}")
        
        # Flow balance at parts
        for u in range(source_idx):
            flow_in = gp.quicksum(x[v, u, i] for v in range(num_nodes) if (v, u, i) in x)
            flow_out = gp.quicksum(x[u, v, i] for v in range(num_nodes) if (u, v, i) in x)
            m.addConstr(flow_in == flow_out, name=f"flow_bal_{u}_{i}")

    # 2. Node Capacity (At most one arm visits a node)
    for u in range(source_idx):
        m.addConstr(gp.quicksum(x[v, u, i] for i in range(2) for v in range(num_nodes) if (v, u, i) in x) <= 1, name=f"cap_{u}")

    # 3. Time Windows & 4. Sequence Timing
    M = end_time + 1000
    
    for u in range(source_idx):
        p_data = nodes[u]['part_data']
        # Window constraints
        # Start time >= p_start
        # c[u] - proc_time >= p_start  => c[u] >= p_start + proc_time
        # But proc_time depends on arm.
        # We need to know which arm visited u.
        
        visited_by_0 = gp.quicksum(x[v, u, 0] for v in range(num_nodes) if (v, u, 0) in x)
        visited_by_1 = gp.quicksum(x[v, u, 1] for v in range(num_nodes) if (v, u, 1) in x)
        
        # If not visited, c[u] is free? No, let's constrain it only if visited.
        # Actually, if not visited, we can force c[u] = 0 or let it be anything.
        # Better: c[u] >= (Start + Proc) * visited
        
        # Start time constraint
        # c[u] >= p_start + 15*vis0 + 20*vis1
        m.addConstr(c[u] >= p_data['start_time'] + arms_time[0]*visited_by_0 + arms_time[1]*visited_by_1, name=f"tw_start_{u}")
        
        # End time constraint
        # c[u] <= p_end
        # Only if visited? If not visited, c[u] doesn't matter.
        # But to keep it clean, we can enforce it always, as c[u] is just a variable.
        m.addConstr(c[u] <= p_data['end_time'], name=f"tw_end_{u}")
        
        # Sequence constraints
        # If x[v, u, i] = 1: c[v] + setup + proc_i <= c[u]
        # v can be Source or Part
        
        # From Source
        for i in range(2):
            if (source_idx, u, i) in x:
                # c[u] >= start_time + setup(src, u)? No setup from source defined?
                # Assume setup from source is 0 or handled differently?
                # Problem says "Two robotic arms can start processing parts at time {start_time}".
                # Usually no setup for first part? Or maybe from "factory state"?
                # "restore to factory state" is at end.
                # "setup time before starting the next part".
                # Assume 0 setup for first part.
                m.addConstr(c[u] >= start_time + arms_time[i] - M*(1 - x[source_idx, u, i]), name=f"seq_src_{u}_{i}")
                
        # From other parts
        for v in range(source_idx):
            for i in range(2):
                if (v, u, i) in x:
                    # Setup v -> u
                    p_v = nodes[v]['part_id']
                    p_u = nodes[u]['part_id']
                    # Always check transitions, even for same part (p_v == p_u)
                    setup = transitions.get((p_v, p_u), 0)
                    
                    m.addConstr(c[u] >= c[v] + setup + arms_time[i] - M*(1 - x[v, u, i]), name=f"seq_{v}_{u}_{i}")

    # 5. Gap Constraint (Same part, k -> k+1)
    for p_id, node_indices in part_nodes.items():
        for k in range(len(node_indices) - 1):
            u = node_indices[k]
            v = node_indices[k+1]
            
            # If both u and v are visited
            # Start_v <= End_u + max_gap
            # c[v] - proc_time_v <= c[u] + max_gap
            
            # We need proc_time_v.
            vis_v_0 = gp.quicksum(x[w, v, 0] for w in range(num_nodes) if (w, v, 0) in x)
            vis_v_1 = gp.quicksum(x[w, v, 1] for w in range(num_nodes) if (w, v, 1) in x)
            
            # Also need to ensure v is processed AFTER u.
            # c[v] >= c[u] + setup(0) + proc_v? No setup for same part?
            # "Same part ... next processing must start within max_gap ... after previous processing ends"
            # Implies sequence.
            # If same arm does u->v, sequence constraint handles c[v] >= c[u] + proc_v.
            # If different arms, we still need c[v] >= c[u] + proc_v?
            # Yes, "next processing".
            
            # Enforce order: c[v] - proc_v >= c[u]
            # c[v] >= c[u] + 15*vis0 + 20*vis1
            # Only if both visited?
            # If v is visited, u MUST be visited? Not necessarily, but logical for "k-th pass".
            # Let's enforce: if v is visited, u must be visited.
            vis_u = gp.quicksum(x[w, u, i] for i in range(2) for w in range(num_nodes) if (w, u, i) in x)
            vis_v = vis_v_0 + vis_v_1
            m.addConstr(vis_v <= vis_u, name=f"order_vis_{u}_{v}")
            
            # Time order
            m.addConstr(c[v] >= c[u] + arms_time[0]*vis_v_0 + arms_time[1]*vis_v_1 - M*(1 - vis_v), name=f"time_order_{u}_{v}")
            
            # Gap constraint
            # c[v] - (15*vis0 + 20*vis1) <= c[u] + max_gap
            # Only if v is visited.
            m.addConstr(c[v] - (arms_time[0]*vis_v_0 + arms_time[1]*vis_v_1) <= c[u] + max_gap + M*(1 - vis_v), name=f"gap_{u}_{v}")

    # 6. Demand Satisfaction
    for p in parts:
        p_id = p['id']
        indices = part_nodes[p_id]
        total_proc = 0
        for u in indices:
            vis_0 = gp.quicksum(x[w, u, 0] for w in range(num_nodes) if (w, u, 0) in x)
            vis_1 = gp.quicksum(x[w, u, 1] for w in range(num_nodes) if (w, u, 1) in x)
            total_proc += arms_time[0]*vis_0 + arms_time[1]*vis_1
            
        m.addConstr(total_proc >= p['demand'] * y[p_id], name=f"demand_{p_id}")

    # 7. Mutex
    for p1, p2 in mutex:
        if p1 in y and p2 in y:
            m.addConstr(y[p1] + y[p2] <= 1, name=f"mutex_{p1}_{p2}")

    # 8. Recovery Time
    for i in range(2):
        for u in range(source_idx):
            if (u, sink_idx, i) in x:
                p_data = nodes[u]['part_data']
                # c[u] + recovery <= end_time
                m.addConstr(c[u] + p_data['recovery_time'] - M*(1 - x[u, sink_idx, i]) <= end_time, name=f"rec_{u}_{i}")

    # Objective
    m.setObjective(gp.quicksum(p['demand'] * y[p['id']] for p in parts), GRB.MAXIMIZE)
    
    # Solve
    m.optimize()
    
    # Output
    if m.status == GRB.OPTIMAL:
        print(f"Optimal Objective: {m.objVal}")
        
        # Reconstruct paths
        for i in range(2):
            print(f"\nArm {i} Path:")
            curr = source_idx
            while True:
                # Find next node
                next_node = None
                for v in range(num_nodes + 1): # +1 for sink
                    if (curr, v, i) in x and x[curr, v, i].X > 0.5:
                        next_node = v
                        break
                
                if next_node is None:
                    break
                    
                if next_node == sink_idx:
                    print(" -> Sink")
                    break
                
                # Print node info
                u = next_node
                p_id = nodes[u]['part_id']
                k = nodes[u]['k']
                time = c[u].X
                print(f" -> Part {p_id} (pass {k}), Finish Time: {time:.2f}")
                
                curr = next_node
    else:
        print("No optimal solution found.")

if __name__ == "__main__":
    solve()
