# Logistics Network Optimization Model

## Problem Description
A logistics company operates a network of distribution centers. Some centers have net supply (negative demand) while others have net demand (positive demand). The goal is to satisfy all demands by transporting goods between centers through potential links. Each link supports bidirectional flow, but establishing flow in a specific direction incurs a fixed setup cost and a variable transportation cost per unit. Each link has a maximum capacity.

## Mathematical Model

### Sets and Indices
- $N$: Set of distribution centers (nodes), indexed by $i, j$.
- $A$: Set of directed arcs $(i, j)$, where each potential link between $i$ and $j$ provides two arcs: $i \to j$ and $j \to i$.

### Parameters
- $d_i$: Net demand at node $i$. $d_i > 0$ indicates demand, $d_i < 0$ indicates supply.
- $v_{ij}$: Variable transportation cost per unit on arc $(i, j)$.
- $f_{ij}$: Fixed setup cost for arc $(i, j)$.
- $C$: Maximum capacity for any arc.

### Decision Variables
- $x_{ij} \ge 0$: Quantity of goods transported on arc $(i, j)$.
- $y_{ij} \in \{0, 1\}$: Binary variable, $y_{ij} = 1$ if arc $(i, j)$ is used, $0$ otherwise.

### Objective Function
Minimize the total cost, which is the sum of fixed setup costs and variable transportation costs:
$$\min Z = \sum_{(i,j) \in A} (f_{ij} y_{ij} + v_{ij} x_{ij})$$

### Constraints
1. **Flow Conservation**: For each node $i \in N$, the net flow out of the node must equal its net supply (or negative net demand):
   $$\sum_{j: (i,j) \in A} x_{ij} - \sum_{j: (j,i) \in A} x_{ji} = -d_i, \quad \forall i \in N$$

2. **Capacity and Linking Constraints**: The flow on each arc cannot exceed its capacity, and flow can only occur if the arc is set up:
   $$x_{ij} \le C \cdot y_{ij}, \quad \forall (i, j) \in A$$

3. **Variable Domains**:
   $$x_{ij} \ge 0, \quad y_{ij} \in \{0, 1\}, \quad \forall (i, j) \in A$$

## Solution Approach
The problem is formulated as a Mixed-Integer Linear Programming (MILP) problem, specifically a Fixed-Charge Network Flow Problem. We use the Gurobi optimizer to solve this model. The binary variables $y_{ij}$ handle the fixed costs and enforce the capacity constraints. The flow conservation constraints ensure that all supplies and demands are balanced across the network.
