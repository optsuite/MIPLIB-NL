# Space Station Resource Scheduling Model

## Problem Description
This is a resource scheduling problem for space stations. We need to make decisions on activating research labs, producing products, investing in global support systems, and leasing emergency generators to maximize total profit while satisfying capacity constraints on each station.

## Sets and Indices
- $I = \{1, \dots, n\}$: Set of space stations, indexed by $i$.
- $J = \{1, \dots, m\}$: Set of products, indexed by $j$.
- $K = \{1, \dots, k\}$: Set of global support systems, indexed by $l$.

## Parameters
- $n$: Number of space stations.
- $m$: Number of products.
- $k$: Number of global support systems.
- $Cap^{gen}$: Capacity provided by one emergency generator (`generator_capacity`).
- $Cost^{gen}$: Cost of leasing one emergency generator (`generator_cost`).
- $Max^{gen}$: Maximum number of generators per station (`max_generators`).

### From Data Files
- $V^{lab}_i$: Profit from activating the research lab on station $i$ (`lab_value`).
- $L^{lab}_i$: Capacity load consumed by the lab on station $i$ (`lab_load`).
- $C_i$: Base energy capacity of station $i$ (`base_capacity`).
- $V^{prod}_j$: Profit per batch of product $j$ (`unit_value`).
- $M_j$: Maximum global production batches for product $j$ (`max_batches`).
- $L^{prod}_{ij}$: Capacity load on station $i$ for producing one batch of product $j$ (`load`).
- $C^{sys}_l$: Cost per unit level of global support system $l$ (`cost`).
- $U_l$: Maximum level for global support system $l$ (`max_level`).

## Decision Variables
- $x_i \in \{0, 1\}$: Binary variable, equal to 1 if the lab on station $i$ is activated, 0 otherwise.
- $y_j \in \mathbb{Z}_{\ge 0}$: Integer variable, number of batches produced for product $j$.
- $z_l \in \mathbb{R}_{\ge 0}$: Continuous variable, investment level in global support system $l$.
- $g_i \in \mathbb{Z}_{\ge 0}$: Integer variable, number of emergency generators leased for station $i$.

## Objective Function
Maximize the total profit, which is the sum of profits from activated labs and produced products, minus the costs of global support systems and leased generators.

$$
\text{Maximize } Z = \sum_{i \in I} V^{lab}_i x_i + \sum_{j \in J} V^{prod}_j y_j - \sum_{l \in K} C^{sys}_l z_l - \sum_{i \in I} Cost^{gen} g_i
$$

## Constraints

1.  **Station Capacity Constraints**:
    For each station $i \in I$, the total load from the activated lab and product production must not exceed the total available capacity (base capacity + global system capacity + generator capacity). Note that each unit of global system investment increases capacity by 1 for *all* stations.

    $$
    L^{lab}_i x_i + \sum_{j \in J} L^{prod}_{ij} y_j \le C_i + \sum_{l \in K} 1 \cdot z_l + Cap^{gen} g_i, \quad \forall i \in I
    $$

2.  **Product Production Limits**:
    The production of each product $j$ cannot exceed its global maximum limit.

    $$
    0 \le y_j \le M_j, \quad \forall j \in J
    $$

3.  **Global System Investment Limits**:
    The investment level for each global system $l$ cannot exceed its maximum level.

    $$
    0 \le z_l \le U_l, \quad \forall l \in K
    $$

4.  **Generator Limits**:
    The number of generators leased for each station $i$ cannot exceed the maximum limit.

    $$
    0 \le g_i \le Max^{gen}, \quad \forall i \in I
    $$

5.  **Variable Domains**:
    $$
    x_i \in \{0, 1\}, \quad \forall i \in I
    $$
    $$
    y_j \in \mathbb{Z}_{\ge 0}, \quad \forall j \in J
    $$
    $$
    z_l \in \mathbb{R}_{\ge 0}, \quad \forall l \in K
    $$
    $$
    g_i \in \mathbb{Z}_{\ge 0}, \quad \forall i \in I
    $$
