# Logistics Optimization Model for ran12x21

## Problem Description
A logistics company manages $m$ warehouses and $n$ retail stores. Each warehouse has a specific supply level, and each retail store has a specific demand. The total supply across all warehouses equals the total demand across all stores. To ship goods from a warehouse to a retail store, a shipping lane must be activated, incurring a one-time fixed setup cost. Once activated, there is a variable transportation cost per unit of goods shipped. Additionally, each lane has a maximum capacity limit. The goal is to determine which lanes to activate and the quantity to ship on each lane to satisfy all store demands without exceeding warehouse supplies, minimizing the total cost (fixed setup costs + variable transportation costs).

## Modeling Approach
The problem is modeled as a **Fixed-Charge Transportation Problem with Capacities**. We use binary variables to represent the activation of shipping lanes and continuous variables to represent the quantity of goods shipped.

## Decision Variables
- $x_{i,j}$: The quantity of goods shipped from warehouse $i$ to retail store $j$ (Continuous, $x_{i,j} \ge 0$).
- $y_{i,j}$: Binary variable indicating whether the shipping lane from warehouse $i$ to retail store $j$ is activated (Binary, $y_{i,j} \in \{0, 1\}$).

## Parameters
- $m$: Number of warehouses.
- $n$: Number of retail stores.
- $S_i$: Supply level of warehouse $i$.
- $D_j$: Demand of retail store $j$.
- $F_{i,j}$: Fixed setup cost to activate the lane from warehouse $i$ to store $j$.
- $V_{i,j}$: Variable transportation cost per unit shipped from warehouse $i$ to store $j$.
- $C_{i,j}$: Maximum capacity of the lane from warehouse $i$ to store $j$.

## Objective Function
Minimize the total cost, which includes the sum of fixed setup costs for activated lanes and variable transportation costs for the goods shipped:
$$\min \sum_{i=1}^{m} \sum_{j=1}^{n} (F_{i,j} \cdot y_{i,j} + V_{i,j} \cdot x_{i,j})$$

## Constraints
1. **Supply Constraints**: The total quantity shipped from each warehouse $i$ cannot exceed its supply $S_i$.
   $$\sum_{j=1}^{n} x_{i,j} \le S_i, \quad \forall i \in \{1, \dots, m\}$$

2. **Demand Constraints**: The total quantity shipped to each retail store $j$ must satisfy its demand $D_j$.
   $$\sum_{i=1}^{m} x_{i,j} = D_j, \quad \forall j \in \{1, \dots, n\}$$

3. **Capacity and Activation Constraints**: The quantity shipped on lane $(i, j)$ cannot exceed its capacity $C_{i,j}$, and can only be non-zero if the lane is activated ($y_{i,j} = 1$).
   $$x_{i,j} \le C_{i,j} \cdot y_{i,j}, \quad \forall i \in \{1, \dots, m\}, \forall j \in \{1, \dots, n\}$$

4. **Variable Domains**:
   - $x_{i,j} \ge 0, \quad \forall i, j$
   - $y_{i,j} \in \{0, 1\}, \quad \forall i, j$
