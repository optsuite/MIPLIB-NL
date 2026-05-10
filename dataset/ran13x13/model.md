# Fixed-Charge Transportation Problem Model

## Problem Description
A logistics company manages a set of warehouses and retail stores. Each warehouse has a limited supply of goods, and each retail store has a specific demand. Goods can be transported from warehouses to stores via shipping lanes. Each lane has a capacity limit, a variable transportation cost per unit, and a fixed setup cost that is incurred only if the lane is used. The objective is to minimize the total cost (sum of fixed and variable costs) while satisfying all store demands and respecting warehouse supplies and lane capacities.

## Mathematical Model

### Sets
*   $I$: Set of warehouses.
*   $J$: Set of retail stores.

### Parameters
*   $S_i$: Supply capacity of warehouse $i \in I$.
*   $D_j$: Demand of retail store $j \in J$.
*   $c_{ij}$: Variable transportation cost per unit from warehouse $i$ to store $j$.
*   $f_{ij}$: Fixed setup cost for activating the route from warehouse $i$ to store $j$.
*   $K_{ij}$: Maximum capacity of the route from warehouse $i$ to store $j$.

### Decision Variables
*   $x_{ij} \ge 0$: Quantity of goods transported from warehouse $i$ to store $j$.
*   $y_{ij} \in \{0, 1\}$: Binary variable equal to 1 if the route from warehouse $i$ to store $j$ is activated (used), and 0 otherwise.

### Objective Function
Minimize the total cost, which consists of variable transportation costs and fixed setup costs:
$$ \min Z = \sum_{i \in I} \sum_{j \in J} (c_{ij} x_{ij} + f_{ij} y_{ij}) $$

### Constraints

1.  **Warehouse Supply Constraints**: The total amount of goods shipped from each warehouse $i$ must not exceed its supply.
    $$ \sum_{j \in J} x_{ij} \le S_i, \quad \forall i \in I $$

2.  **Store Demand Constraints**: The total amount of goods received by each store $j$ must equal its demand.
    $$ \sum_{i \in I} x_{ij} = D_j, \quad \forall j \in J $$

3.  **Route Capacity and Linking Constraints**: The amount shipped on any route $(i, j)$ cannot exceed its capacity. Furthermore, goods can only be shipped if the route is activated ($y_{ij} = 1$).
    $$ x_{ij} \le K_{ij} y_{ij}, \quad \forall i \in I, j \in J $$

4.  **Variable Domains**:
    $$ x_{ij} \ge 0, \quad \forall i \in I, j \in J $$
    $$ y_{ij} \in \{0, 1\}, \quad \forall i \in I, j \in J $$
