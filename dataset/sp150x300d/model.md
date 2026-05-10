# Minimum Edge Network Flow Model

## Problem Description
The problem asks to find the minimum number of transport routes (edges) required to satisfy the supply and demand constraints of a network. We have a set of locations (nodes) with specific net demands (positive for demand, negative for supply) and a set of potential routes (directed edges). Activating a route incurs a fixed cost (which we can consider as 1 per route to minimize the count), and an activated route can carry any amount of flow.

## Mathematical Model

### Sets and Indices
- $V$: Set of locations (nodes), indexed by $i$.
- $E$: Set of potential transport routes (directed edges), indexed by $(i, j)$.

### Parameters
- $d_i$: Net demand of location $i \in V$.
  - $d_i > 0$: Location $i$ is a demand point requiring $d_i$ units.
  - $d_i < 0$: Location $i$ is a supply point providing $|d_i|$ units.
  - $d_i = 0$: Location $i$ is a transshipment point.
- $M$: A sufficiently large constant, representing the capacity of an edge. It can be set to the sum of all positive demands (total demand).

### Decision Variables
- $x_{ij} \ge 0$: Continuous variable representing the amount of supplies transported on route $(i, j)$.
- $y_{ij} \in \{0, 1\}$: Binary variable indicating whether route $(i, j)$ is activated ($1$) or not ($0$).

### Objective Function
Minimize the total number of activated routes:
$$ \text{Minimize } Z = \sum_{(i,j) \in E} y_{ij} $$

### Constraints

1.  **Flow Conservation Constraints**:
    For each node $i \in V$, the total inflow minus the total outflow must equal the net demand.
    $$ \sum_{j: (j,i) \in E} x_{ji} - \sum_{j: (i,j) \in E} x_{ij} = d_i, \quad \forall i \in V $$

2.  **Linking Constraints (Big-M Constraints)**:
    Flow on an edge is only allowed if the edge is activated.
    $$ x_{ij} \le M \cdot y_{ij}, \quad \forall (i,j) \in E $$

3.  **Variable Domains**:
    $$ x_{ij} \ge 0, \quad \forall (i,j) \in E $$
    $$ y_{ij} \in \{0, 1\}, \quad \forall (i,j) \in E $$
