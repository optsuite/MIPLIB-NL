# Power Transmission Network Design Model

## Problem Description
The problem asks us to design a power transmission network connecting $n$ cities. Each city has a net power generation (positive for surplus, negative for demand), and the sum of net generation across all cities is zero. We need to determine the number and type of power lines to install between specified pairs of cities to satisfy the power flow requirements while minimizing the total cost.

There are $k$ types of physical lines available, each with a specific capacity and cost per unit length. For the first $k-1$ types (smaller capacities), at most one line can be installed per edge. For the largest capacity type, up to $l$ lines can be installed.

## Sets and Indices
*   $V = \{1, \dots, n\}$: Set of cities.
*   $E$: Set of allowed connections (edges) between cities. Each edge is an unordered pair $\{i, j\}$.
*   $T = \{1, \dots, k\}$: Set of line types, ordered by capacity.

## Parameters
*   $G_i$: Net power generation of city $i \in V$.
*   $D_{ij}$: Distance between city $i$ and city $j$ for $\{i, j\} \in E$.
*   $Cap_t$: Rated capacity of line type $t \in T$.
*   $Cost_t$: Cost per unit length of line type $t \in T$.
*   $L$: Maximum number of lines allowed for the largest line type ($t=k$).

## Variables
*   $f_{ij}$: Net power flow from city $i$ to city $j$ for $\{i, j\} \in E$. We define this for ordered pairs $(i, j)$ where $i < j$. A positive value indicates flow from $i$ to $j$, and negative indicates flow from $j$ to $i$. Alternatively, we can use directed variables $x_{ij} \ge 0$ for flow on arc $(i, j)$. Let's use continuous variables $f_{ij}$ (unrestricted in sign) representing flow from $i$ to $j$ for each edge $\{i, j\} \in E$ with $i < j$.
*   $y_{ijt}$: Number of lines of type $t$ installed on edge $\{i, j\} \in E$.
    *   For $t \in \{1, \dots, k-1\}$, $y_{ijt} \in \{0, 1\}$.
    *   For $t = k$, $y_{ijk} \in \{0, \dots, L\}$.

## Objective Function
Minimize the total cost of the installed physical lines:
$$
\text{Minimize} \quad \sum_{\{i, j\} \in E} D_{ij} \sum_{t=1}^k Cost_t \cdot y_{ijt}
$$

## Constraints

1.  **Flow Conservation**:
    For each city $i \in V$, the net flow out of the city must equal its net generation.
    $$
    \sum_{j: \{i, j\} \in E, i < j} f_{ij} - \sum_{j: \{i, j\} \in E, j < i} f_{ji} = G_i \quad \forall i \in V
    $$
    (Note: Here $f_{ji}$ refers to the variable for edge $\{j, i\}$ where $j < i$. If we strictly use $f_{uv}$ with $u < v$, then for neighbors $j$ of $i$: if $i < j$, term is $+f_{ij}$; if $j < i$, term is $-f_{ji}$.)

2.  **Capacity Constraints**:
    The absolute power flow on any edge must not exceed the total installed capacity.
    $$
    |f_{ij}| \le \sum_{t=1}^k Cap_t \cdot y_{ijt} \quad \forall \{i, j\} \in E, i < j
    $$
    This can be linearized as two constraints:
    $$
    f_{ij} \le \sum_{t=1}^k Cap_t \cdot y_{ijt}
    $$
    $$
    -f_{ij} \le \sum_{t=1}^k Cap_t \cdot y_{ijt}
    $$

3.  **Variable Bounds and Integrality**:
    *   $y_{ijt} \in \{0, 1\}$ for $t \in \{1, \dots, k-1\}$, $\forall \{i, j\} \in E$.
    *   $y_{ijk} \in \{0, \dots, L\}$ (integer), $\forall \{i, j\} \in E$.
    *   $f_{ij}$ is free (unrestricted sign), or bounded by max possible flow if needed for numerical stability.

## Solution Approach
We will model this problem as a Mixed-Integer Linear Programming (MILP) problem.
1.  Define the graph nodes and edges based on the input data.
2.  Create continuous flow variables and integer line count variables.
3.  Add flow conservation constraints for each node.
4.  Add capacity constraints linking flow and line variables.
5.  Set the objective to minimize total line cost.
6.  Use the Gurobi Optimizer to solve the MILP.
