# Mathematical Model

## Problem Description
The problem asks to select a set of directed pipeline routes to construct and determine the oil flow on them to transport oil from sources (oil fields) to sinks (refineries) via potential transshipment points. The goal is to minimize the total cost, which includes the fixed construction cost of the pipelines and the variable flow cost proportional to the amount of oil transported.

## Sets and Indices
- $V$: Set of nodes (locations).
- $E$: Set of potential directed edges (pipelines).
- $i, j \in V$: Indices for nodes.
- $(i, j) \in E$: Index for a directed edge from node $i$ to node $j$.

## Parameters
- $b_i$: Net supply of node $i$.
  - If $b_i > 0$, node $i$ is a source (supply).
  - If $b_i < 0$, node $i$ is a sink (demand).
  - If $b_i = 0$, node $i$ is a transshipment node.
- $c_{ij}$: Flow cost per unit of oil on edge $(i, j)$.
- $f_{ij}$: Fixed construction cost for edge $(i, j)$.
- $M$: A sufficiently large constant, representing the capacity of a constructed pipeline. Since the problem states capacity is infinite, $M$ can be set to the total supply of all source nodes ($\sum_{i \in V, b_i > 0} b_i$).

## Decision Variables
- $x_{ij} \ge 0$: Continuous variable representing the amount of oil flow on edge $(i, j)$.
- $y_{ij} \in \{0, 1\}$: Binary variable. $y_{ij} = 1$ if edge $(i, j)$ is constructed (selected), and $0$ otherwise.

## Objective Function
Minimize the total cost, consisting of flow costs and fixed construction costs:
$$
\text{Minimize } Z = \sum_{(i, j) \in E} c_{ij} x_{ij} + \sum_{(i, j) \in E} f_{ij} y_{ij}
$$

## Constraints

1.  **Flow Conservation Constraints**:
    For each node $i \in V$, the total outflow minus the total inflow must equal the net supply $b_i$.
    $$
    \sum_{j: (i, j) \in E} x_{ij} - \sum_{j: (j, i) \in E} x_{ji} = b_i, \quad \forall i \in V
    $$

2.  **Linking Constraints (Big-M Constraints)**:
    Flow is only allowed on an edge if it is constructed. If constructed ($y_{ij}=1$), the flow is bounded by $M$. If not constructed ($y_{ij}=0$), the flow must be 0.
    $$
    x_{ij} \le M \cdot y_{ij}, \quad \forall (i, j) \in E
    $$

3.  **Variable Domains**:
    $$
    x_{ij} \ge 0, \quad \forall (i, j) \in E
    $$
    $$
    y_{ij} \in \{0, 1\}, \quad \forall (i, j) \in E
    $$
