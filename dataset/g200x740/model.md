# Supply Chain Network Design Problem

## Problem Description
The goal of this problem is to design a supply chain network that minimizes the total cost, which includes fixed costs for activating transportation links and variable costs for the actual volume of goods transported. The network consists of nodes (warehouses or customers) with specific demands or supplies, and potential links between them. Each link has a maximum capacity.

## Mathematical Model

### Sets and Indices
- $N$: Set of nodes, indexed by $i$.
- $E$: Set of potential transportation links (edges), indexed by $e = (i, j)$, where $i$ is the source node and $j$ is the target node.

### Parameters
- $d_i$: Net demand of node $i$. $d_i > 0$ indicates a demand node, $d_i < 0$ indicates a supply node, and $d_i = 0$ indicates a transshipment point.
- $f_e$: Fixed cost to activate link $e \in E$.
- $c_e$: Variable cost per unit of flow on link $e \in E$.
- $u_e$: Maximum capacity of link $e \in E$.

### Decision Variables
- $x_e$: Continuous variable representing the volume of goods transported on link $e \in E$ ($x_e \ge 0$).
- $y_e$: Binary variable indicating whether link $e \in E$ is activated ($y_e = 1$) or not ($y_e = 0$).

### Objective Function
Minimize the total cost, which is the sum of fixed activation costs and variable transportation costs:
$$\min Z = \sum_{e \in E} (f_e y_e + c_e x_e)$$

### Constraints
1. **Flow Balance**: For each node $i \in N$, the net flow (outflow minus inflow) must equal the net supply (which is the negative of net demand):
   $$\sum_{j: (i, j) \in E} x_{ij} - \sum_{j: (j, i) \in E} x_{ji} = -d_i, \quad \forall i \in N$$

2. **Capacity and Activation**: The flow on each link $e$ cannot exceed its capacity, and flow is only possible if the link is activated:
   $$x_e \le u_e y_e, \quad \forall e \in E$$

3. **Variable Domains**:
   $$x_e \ge 0, \quad \forall e \in E$$
   $$y_e \in \{0, 1\}, \quad \forall e \in E$$

## Solution Approach
The problem is formulated as a Mixed-Integer Linear Programming (MILP) model. The binary variables $y_e$ handle the fixed-charge aspect, while the continuous variables $x_e$ handle the flow. The model can be solved using commercial solvers like Gurobi.
