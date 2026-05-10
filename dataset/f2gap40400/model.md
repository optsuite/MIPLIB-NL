# Optimization Model: Housekeeping Service Staffing Optimization

## 1. Problem Description

A housekeeping service company faces a staffing optimization decision. The company needs to handle $N_1$ different tasks and has a talent pool of $N_2$ candidate employees.

Key factors in this decision process include:
1.  **Salaries**: Each candidate has an expected salary. Notably, some candidates are interns willing to pay for the opportunity, resulting in negative salary values (representing revenue for the company).
2.  **Contribution**: Each employee has a specific competency or contribution level for each task. Once hired, an employee contributes to multiple tasks simultaneously. However, some employees may have a negative impact (negative contribution) on certain tasks.
3.  **Task Thresholds**: Each task has a minimum required completion threshold.

The objective is to determine the optimal subset of employees to hire such that the cumulative contribution of all hired employees for each task meets or exceeds the task's threshold, while minimizing the total salary cost to the company.

## 2. Sets and Indices

* $J = \{0, 1, \dots, N_2-1\}$: Set of candidate employees.
* $I = \{0, 1, \dots, N_1-1\}$: Set of tasks.

## 3. Parameters

Based on the provided data files:

* $S_j \in \mathbb{R}$: Salary of employee $j$ (from `C1.csv`).
    * If $S_j < 0$, the employee is a paying intern.
* $C_{ji} \in \mathbb{R}$: Contribution of employee $j$ to task $i$ (from `C2.csv`).
    * $C_{ji}$ is the value at the intersection of employee $j$'s row and task $i$'s column.
* $T_i \in \mathbb{R}^+$: Minimum contribution threshold required for task $i$ (from `C3.csv`).

## 4. Decision Variables

Define binary decision variable $x_j$:

$$
x_j = \begin{cases} 
1, & \text{if employee } j \text{ is hired} \\
0, & \text{otherwise}
\end{cases}, \quad \forall j \in J
$$

## 5. Objective Function

The objective is to minimize the total hiring cost (total salaries):

$$
\text{Minimize } Z = \sum_{j \in J} S_j \cdot x_j
$$

## 6. Constraints

### 6.1 Task Completion Constraints
For every task $i$, the sum of contributions from all hired employees must be greater than or equal to the task's threshold $T_i$:

$$
\sum_{j \in J} C_{ji} \cdot x_j