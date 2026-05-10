# Fixed Charge Network Flow Model

## Problem Understanding

The problem asks for an optimal transportation network configuration and flow allocation in a retail supply chain. We have a set of Regional Distribution Centers (RDCs), some acting as supply points and some as demand points. The trunk lines connecting them have both a variable transportation cost (per unit of flow) and a fixed maintenance cost (setup cost) if the line is used. Each line direction has a capacity limit.

This is a classic **Fixed Charge Network Design Problem** (or Fixed Charge Minimum Cost Flow Problem).

## Mathematical Formulation

### Sets and Parameters

*   $V$: Set of nodes (RDCs).
*   $A$: Set of directed arcs. Since connections are bidirectional, each undirected edge $\{i, j\}$ in the input corresponds to two directed arcs $(i, j)$ and $(j, i)$.
*   $D_i$: Net demand of node $i \in V$.
    *   If $D_i > 0$, node $i$ is a demand point.
    *   If $D_i < 0$, node $i$ is a supply point (net supply $-D_i$).
    *   $\sum_{i \in V} D_i = 0$ (Balanced system).
*   $c_{ij}$: Variable cost per unit of flow on arc $(i, j)$.
*   $f_{ij}$: Fixed cost for opening/using arc $(i, j)$.
*   $U$: Capacity of arc $(i, j)$ (same for all arcs in this problem instance, $U=100$).

### Decision Variables

*   $x_{ij} \ge 0$: Continuous variable representing the amount of flow on arc $(i, j)$.
*   $y_{ij} \in \{0, 1\}$: Binary variable indicating if arc $(i, j)$ is open (1) or closed (0).

### Objective Function

Minimize the total cost, which is the sum of variable transportation costs and fixed setup costs:

$$
\min \sum_{(i,j) \in A} (c_{ij} x_{ij} + f_{ij} y_{ij})
$$

### Constraints

1.  **Flow Conservation Constraints**:
    For each node $i \in V$, the total inflow minus the total outflow must equal the net demand at that node.

    $$
    \sum_{j : (j,i) \in A} x_{ji} - \sum_{j : (i,j) \in A} x_{ij} = D_i, \quad \forall i \in V
    $$

2.  **Capacity and Linking Constraints**:
    Flow on an arc cannot exceed the capacity, and flow is only allowed if the arc is open ($y_{ij}=1$). This is effectively a "Big-M" constraint where $M$ is the capacity $U$.

    $$
    x_{ij} \le U \cdot y_{ij}, \quad \forall (i,j) \in A
    $$

3.  **Variable Domains**:
    $$
    x_{ij} \ge 0, \quad y_{ij} \in \{0, 1\}, \quad \forall (i,j) \in A
    $$

## Solving Approach

We will model this problem using Mixed-Integer Linear Programming (MILP) and solve it using the Gurobi Optimizer.

1.  **Data Parsing**: Read nodes and edges from the provided CSV files. Treat each edge in the CSV as two directed ares.
2.  **Model Building**:
    *   Create variables $x_{ij}$ and $y_{ij}$.
    *   Add flow conservation constraints for each node.
    *   Add capacity constraints linking $x$ and $y$.
    *   Set the minimization objective.
3.  **Optimization**: Solve the MILP model.
4.  **Result Extraction**: Identify the arcs with $y_{ij} > 0.5$ (or $x_{ij} > 0$) as the selected edges for the network.
