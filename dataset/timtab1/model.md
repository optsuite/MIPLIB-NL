# Mathematical Formulation: Transport Timetabling Problem

## Problem Description

This is a transport timetabling optimization problem that minimizes total operational cost while balancing service supply and demand across different time periods or locations. The problem combines continuous service level decisions with integer frequency decisions representing the number of vehicles operating in each period.

## Sets and Indices

- $\mathcal{S}$: Set of service lines (indexed by $i$), $|\mathcal{S}| = 226$
- $\mathcal{F}$: Set of frequency periods (indexed by $j$), $|\mathcal{F}| = 171$
- $\mathcal{C}$: Set of constraints (indexed by $c$), $|\mathcal{C}| = 171$

## Parameters

### Service Parameters

- $c_i$: Operational cost per unit of service $i \in \mathcal{S}$
- $L_i^s$: Lower bound for service level $i \in \mathcal{S}$
- $U_i^s$: Upper bound for service level $i \in \mathcal{S}$

### Frequency Parameters

- $L_j^f$: Lower bound for frequency $j \in \mathcal{F}$
- $U_j^f$: Upper bound for frequency $j \in \mathcal{F}$

### Constraint Parameters

- $a_{ic}$: Coefficient of service $i$ in constraint $c$
- $b_{jc}$: Coefficient of frequency $j$ in constraint $c$ (typically $-60$)
- $r_c$: Right-hand side (demand/requirement) for constraint $c$

## Decision Variables

### Continuous Variables

$$
x_i \in [L_i^s, U_i^s], \quad \forall i \in \mathcal{S}
$$

Where $x_i$ represents the service level for service line $i$.

### Integer Variables

$$
y_j \in \mathbb{Z} \cap [L_j^f, U_j^f], \quad \forall j \in \mathcal{F}
$$

Where $y_j$ represents the number of vehicles/services operating in frequency period $j$.

## Objective Function

Minimize the total operational cost:

$$
\min \quad Z = \sum_{i \in \mathcal{S}} c_i \cdot x_i
$$

## Constraints

### Service Balance Constraints

For each constraint $c \in \mathcal{C}$:

$$
\sum_{i \in \mathcal{S}} a_{ic} \cdot x_i + \sum_{j \in \mathcal{F}} b_{jc} \cdot y_j = r_c
$$

These constraints ensure that the combination of service levels and vehicle frequencies satisfies the demand/requirement at each time period or location.

## Complete Formulation

$$
\begin{align}
\min \quad & Z = \sum_{i \in \mathcal{S}} c_i \cdot x_i \\
\text{s.t.} \quad & \sum_{i \in \mathcal{S}} a_{ic} \cdot x_i + \sum_{j \in \mathcal{F}} b_{jc} \cdot y_j = r_c, \quad \forall c \in \mathcal{C} \\
& L_i^s \leq x_i \leq U_i^s, \quad \forall i \in \mathcal{S} \\
& L_j^f \leq y_j \leq U_j^f, \quad \forall j \in \mathcal{F} \\
& x_i \in \mathbb{R}_{+}, \quad \forall i \in \mathcal{S} \\
& y_j \in \mathbb{Z}_{+}, \quad \forall j \in \mathcal{F}
\end{align}
$$
