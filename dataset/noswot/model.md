# Noswot Problem Model

## Problem Description
The goal is to maximize the total production quantity across $n$ parallel production lines (machines) and $m$ stages, subject to capacity, quantity, and temporal constraints.

## Mathematical Model

### Indices and Sets
- $I = \{1, \dots, n\}$: Set of machines (production lines).
- $J = \{1, \dots, m\}$: Set of stages.

### Parameters
- $C_i$: Capacity (available time) for machine $i$.
- $F_{i,j}$: Fixed setup time for machine $i$ at stage $j$.
- $U_{i,j}$: Unit variable time for machine $i$ at stage $j$.
- $Q^{\max}_{i,j}$: Maximum single production quantity for machine $i$ at stage $j$.
- $S^{\min}_j, S^{\max}_j$: Minimum and maximum total quantity for stage $j$ across all machines.
- $G$: Global total quantity limit.
- $T^{\text{limit}}$: Time window limit for interval between adjacent stages.

### Decision Variables
- $x_{i,j} \in \mathbb{Z}_{\ge 0}$: Quantity produced by machine $i$ at stage $j$.
- $z_{i,j} \in \{0, 1\}$: Binary variable indicating if machine $i$ produces at stage $j$ ($1$ if $x_{i,j} > 0$, $0$ otherwise).

### Objective Function
Maximize the total quantity produced:
$$ \max \sum_{i \in I} \sum_{j \in J} x_{i,j} $$

### Constraints

1.  **Machine Capacity Constraint**:
    The total production duration (fixed + variable) on each machine need not exceed its capacity.
    $$ \sum_{j \in J} (F_{i,j} \cdot z_{i,j} + U_{i,j} \cdot x_{i,j}) \le C_i, \quad \forall i \in I $$

2.  **Production Quantity Limits**:
    If production occurs ($z_{i,j}=1$), the quantity is bounded by the maximum task quantity.
    $$ x_{i,j} \le \lfloor Q^{\max}_{i,j} \rfloor \cdot z_{i,j}, \quad \forall i \in I, j \in J $$
    $$ x_{i,j} \ge z_{i,j}, \quad \forall i \in I, j \in J \quad (\text{Optional, ensures } z=1 \text{ if } x>0) $$
    *(Note: Since we pay a Fixed Cost for $z=1$, the solver will naturally set $z=0$ if $x=0$ to save capacity, provided $F_{i,j} > 0$. Strictly, the constraint $x \le M z$ is sufficient).*

3.  **Stage Quantity Limits**:
    Total production for each stage must be within the specified range.
    $$ S^{\min}_j \le \sum_{i \in I} x_{i,j} \le S^{\max}_j, \quad \forall j \in J $$

4.  **Global Quantity Limit**:
    Total production across all machines and stages must not exceed the global limit.
    $$ \sum_{i \in I} \sum_{j \in J} x_{i,j} \le G $$

5.  **Time Window Constraint**:
    The problem states that the interval between adjacent stages in a selected path must not exceed $T^{\text{limit}}$.
    Modeling the processing of stages as a sequence, the minimal interval (gap) between the completion of one stage and the start of the next is 0. Since $0 \le T^{\text{limit}}$ (assuming $T^{\text{limit}} \ge 0$), this constraint is satisfied by scheduling stages immediately one after another.
    If the constraint implies that the *duration* of the preceding stage ($T_{i,j} = F_{i,j}z_{i,j} + U_{i,j}x_{i,j}$) limits the start of the next, i.e., $Start_{j+1} - Start_j \le T^{\text{limit}}$, then effectively $T_{i,j} \le T^{\text{limit}}$.
    Given that $C_i \le 20$ and $T^{\text{limit}} = 21$, the condition $T_{i,j} \le C_i < T^{\text{limit}}$ is always satisfied. Thus, this constraint is non-binding for this specific instance.

## Solution Approach
The problem is modeled as a Mixed Integer Linear Programming (MILP) problem and solved using the Gurobi Optimizer.
