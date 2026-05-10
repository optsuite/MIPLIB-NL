# Personnel Rostering Optimization Model

This document outlines the mathematical formulation for the Personnel Rostering Problem with soft constraints on workload and labor costs.

## Sets and Indices

* $I = \{1, \dots, N_1\}$: Set of employees, indexed by $i$.
* $J = \{1, \dots, N_2\}$: Set of shift patterns, indexed by $j$.

## Parameters

The problem is defined by the following parameters, corresponding to the provided data files:

* $N_1$: Total number of employees (derived from the number of columns in Table C1/C2).
* $N_2$: Total number of shift patterns (derived from the number of rows in Table C1/C2).
* $w_{ji}$: The workload contribution of employee $i$ if assigned to shift pattern $j$ (Data from **Table C1**).
* $c_{ji}$: The labor cost incurred by employee $i$ if assigned to shift pattern $j$ (Data from **Table C2**).
* $W_j^{\max}$: The maximum allowable total workload for shift pattern $j$ (Data from **Table C3**, column 'MaxWorkload').
* $C_j^{\max}$: The maximum allowable total labor cost for shift pattern $j$ (Data from **Table C3**, column 'MaxCost').

## Decision Variables

* $x_{ij} \in \{0, 1\}$: Binary variable. Equal to 1 if employee $i$ is assigned to shift pattern $j$, and 0 otherwise.
* $s^w_j \ge 0$: Continuous variable representing the **excess workload violation** for shift pattern $j$.
* $s^c_j \ge 0$: Continuous variable representing the **excess labor cost violation** for shift pattern $j$.

## Objective Function

The objective is to minimize the total penalty incurred by violating the soft constraints (workload and labor cost limits) across all shift patterns.

$$
\text{Minimize } Z = \sum_{j \in J} \left( s^w_j + s^c_j \right)
$$

## Constraints

### 1. Employee Assignment Constraint
Each employee must be assigned to exactly one shift pattern.

$$
\sum_{j \in J} x_{ij} = 1, \quad \forall i \in I
$$

### 2. Shift Coverage Constraint
Each shift pattern must be covered by at least one employee.

$$
\sum_{i \in I} x_{ij} \ge 1, \quad \forall j \in J
$$

### 3. Workload Soft Constraint
The total workload for shift $j$ minus the slack variable must be less than or equal to the maximum allowed workload. If the total workload exceeds $W_j^{\max}$, the variable $s^w_j$ will take a positive value to satisfy the equality.

$$
\sum_{i \in I} w_{ji} x_{ij} - s^w_j \le W_j^{\max}, \quad \forall j \in J
$$

### 4. Labor Cost Soft Constraint
The total labor cost for shift $j$ minus the slack variable must be less than or equal to the maximum allowed labor cost. If the total cost exceeds $C_j^{\max}$, the variable $s^c_j$ will take a positive value.

$$
\sum_{i \in I} c_{ji} x_{ij} - s^c_j \le C_j^{\max}, \quad \forall j \in J
$$

### 5. Variable Domains

$$
x_{ij} \in \{0, 1\}, \quad \forall i \in I, \forall j \in J
$$

$$
s^w_j \ge 0, \quad s^c_j \ge 0, \quad \forall j \in J
$$