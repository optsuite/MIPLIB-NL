# Mathematical Model

## Problem Description

We are given $n$ cities. We need to select $p$ cities to establish warehouse centers to minimize the total transportation cost.
For each city $i$, there is a specific "city chain" which lists potential service cities and their associated costs (orders).
If city $i$ is served by a city $j$ which appears at order $k$ in $i$'s chain, the cost is $k$.
The actual service cost for city $i$ is the order of the *first* selected city in its chain.

## Sets and Indices

*   $I = \{0, 1, \dots, n-1\}$: Set of cities (chain owners).
*   $J = \{0, 1, \dots, n-1\}$: Set of potential warehouse locations (service cities).
*   $C_i$: The set of cities in the chain of city $i$.
*   $O_{ij}$: The order (cost) of city $j$ in the chain of city $i$, for $j \in C_i$.

## Parameters

*   $n$: Total number of cities.
*   $p$: Number of warehouses to open.

## Decision Variables

*   $y_j \in \{0, 1\}$: Binary variable, equal to 1 if city $j$ is selected as a warehouse, 0 otherwise.
*   $x_{ij} \in \{0, 1\}$: Binary variable, equal to 1 if city $i$ is served by city $j$, 0 otherwise. This variable is defined only if $j \in C_i$.

## Objective Function

Minimize the total service cost:
$$
\text{Minimize} \quad \sum_{i \in I} \sum_{j \in C_i} O_{ij} \cdot x_{ij}
$$

## Constraints

1.  **Warehouse Selection Limit**: Exactly $p$ warehouses must be opened.
    $$
    \sum_{j \in J} y_j = p
    $$

2.  **Single Service Assignment**: Each city $i$ must be served by exactly one city from its chain.
    $$
    \sum_{j \in C_i} x_{ij} = 1, \quad \forall i \in I
    $$

3.  **Service Validity**: City $i$ can be served by city $j$ only if city $j$ is selected as a warehouse.
    $$
    x_{ij} \le y_j, \quad \forall i \in I, \forall j \in C_i
    $$

4.  **Binary Constraints**:
    $$
    x_{ij} \in \{0, 1\}, \quad y_j \in \{0, 1\}
    $$
