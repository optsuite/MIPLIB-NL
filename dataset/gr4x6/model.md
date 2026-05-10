### Problem Description
- We need to determine the optimal transportation plan to deliver goods from $N_1$ factories to $N_2$ customers.
- The goal is to minimize the total cost, which comprises the fixed costs for opening transportation routes and the variable unit shipping costs for the transported goods.
- The schedule must satisfy several constraints: factory production limits (supply), customer demand requirements, and the logical condition that goods can only be transported along a route if the fixed opening cost for that route has been paid.

### Parameter Description
- $N_1$: Number of factories ($N1 = 4$).
- $N_2$: Number of customers ($N2 = 6$).
- $C1_{i,j}$: Fixed cost for opening the route from factory $i$ to customer $j$, defined in Table C1.
- $C2_{i,j}$: Unit shipping cost per unit of goods from factory $i$ to customer $j$, defined in Table C2.
- $C3_i$: Production volume (supply capacity) of factory $i$, defined in Table C3.
- $C4_j$: Demand volume of customer $j$, defined in Table C4.

### Decision Variables
- $X_{i,j}$: Continuous variable, quantity of goods shipped from factory $i$ to customer $j$.
- $Y_{i,j}$: Binary variable (Integer), equals 1 if the route from factory $i$ to customer $j$ is selected (opened), and 0 otherwise.

### Objective Function

$$
\text{Minimize} \quad \sum_{i=0}^{N_1-1} \sum_{j=0}^{N_2-1} (C2_{i,j} \cdot X_{i,j} + C1_{i,j} \cdot Y_{i,j})
$$

### Constraints

1.  **Supply Satisfaction:**
    The total quantity of goods shipped out from each factory must equal its fixed production volume.
    $$\sum_{j=0}^{N_2-1} X_{i,j} = C3_i \quad \forall i \in \{0, \dots, N_1-1\}$$

2.  **Demand Satisfaction:**
    The total quantity of goods received by each customer must exactly meet its demand.
    $$\sum_{i=0}^{N_1-1} X_{i,j} = C4_j \quad \forall j \in \{0, \dots, N_2-1\}$$

3.  **Logical Linking (Fixed Charge):**
    Goods can only be shipped on a route if the route is opened (i.e., the fixed cost is incurred). If $Y_{i,j} = 0$, then $X_{i,j}$ must be 0.
    Let $M_{i,j}$ be a sufficiently large upper bound (e.g., $\min(C3_i, C4_j)$).
    $$X_{i,j} \le M_{i,j} \cdot Y_{i,j} \quad \forall i, j$$

4.  **Variable Domains:**
    $$X_{i,j} \ge 0 \quad \forall i, j$$
    $$Y_{i,j} \in \{0, 1\} \quad \forall i, j$$