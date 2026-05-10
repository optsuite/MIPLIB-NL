# Two-Echelon Supply Chain Network Design Problem

## Problem Description

We consider a two-echelon supply chain network design problem (also known as the Capacitated Facility Location Problem with flow conservation). The network consists of three layers of nodes:
1.  **Upstream Manufacturing Plants (Sources)**: Produce goods with limited capacity.
2.  **Potential Distribution Centers (Candidate Hubs)**: Receive goods from plants and distribute them to customers. We must select a specific number of hubs to open from the candidate set.
3.  **Downstream Demand Regions (Customers)**: Have specific demand requirements that must be met.

The objective is to minimize the total cost, which comprises the fixed setup costs for opening distribution centers and the variable transportation costs across the network (Plant $\to$ DC and DC $\to$ Customer).

The decision involves determining:
1.  Which candidate distribution centers to open.
2.  The quantity of goods shipped from each plant to each opened distribution center.
3.  The quantity of goods shipped from each opened distribution center to each customer.

## Sets and Indices

* $I$: Set of upstream manufacturing plants (Sources), indexed by $i$.
* $J$: Set of potential distribution centers (Candidate Hubs), indexed by $j$.
* $K$: Set of downstream demand regions (Customers), indexed by $k$.

## Parameters

* $F_j$: Fixed setup cost for opening distribution center $j$.
* $C1_{ij}$: Unit transportation cost from plant $i$ to distribution center $j$.
* $C2_{jk}$: Unit transportation cost from distribution center $j$ to customer $k$.
* $Cap_i$: Maximum production capacity of plant $i$.
* $Dem_k$: Demand requirement of customer $k$.
* $N_{select}$: The exact number of distribution centers that must be opened (in this instance, $N_{select}=4$).
* $M$: A sufficiently large number (Big-M) used for linking constraints.

## Decision Variables

* $y_j \in \{0, 1\}$: Binary variable. Equal to 1 if distribution center $j$ is opened; 0 otherwise.
* $x_{ij} \ge 0$: Continuous (or Integer) variable representing the flow quantity from plant $i$ to distribution center $j$.
* $z_{jk} \ge 0$: Continuous (or Integer) variable representing the flow quantity from distribution center $j$ to customer $k$.

## Mathematical Formulation

### Objective Function

Minimize the total cost, consisting of fixed facility costs and variable transportation costs:

$$
\min Z = \sum_{j \in J} F_j y_j + \sum_{i \in I} \sum_{j \in J} C1_{ij} x_{ij} + \sum_{j \in J} \sum_{k \in K} C2_{jk} z_{jk}
$$

### Constraints

**1. Plant Production Capacity**
The total flow leaving each plant cannot exceed its production capacity:

$$
\sum_{j \in J} x_{ij} \le Cap_i, \quad \forall i \in I
$$

**2. Customer Demand Satisfaction**
The total flow received by each customer must meet or exceed their demand:

$$
\sum_{j \in J} z_{jk} \ge Dem_k, \quad \forall k \in K
$$

**3. Flow Conservation at Distribution Centers**
For any distribution center, the total inflow from plants must equal the total outflow to customers (no storage allowed):

$$
\sum_{i \in I} x_{ij} = \sum_{k \in K} z_{jk}, \quad \forall j \in J
$$

**4. Linking Constraints (Big-M)**
Flow is only allowed through a distribution center if it is opened ($y_j = 1$). If $y_j = 0$, the inflow must be 0:

$$
\sum_{i \in I} x_{ij} \le M \cdot y_j, \quad \forall j \in J
$$

**5. Cardinality Constraint**
Exactly $N_{select}$ distribution centers must be opened:

$$
\sum_{j \in J} y_j = N_{select}
$$

**6. Variable Domains**

$$
y_j \in \{0, 1\}, \quad \forall j \in J
$$
$$
x_{ij} \ge 0, \quad \forall i \in I, j \in J
$$
$$
z_{jk} \ge 0, \quad \forall j \in J, k \in K
$$