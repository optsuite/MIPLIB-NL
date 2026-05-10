# Mathematical Model

## Problem Description

We are given $n$ jobs to be processed on a single machine. The jobs are divided into $m$ groups.
Each job $j$ has an arrival time $r_j$ and belongs to a group $g_j$.

The processing constraints are:
1.  **Group Order**: Jobs within the same group must be processed in the order of their indices.
2.  **Same Group Interval**: The start time interval between adjacent jobs in the same group must be at least $p$.
3.  **Different Group Interval**: The start time interval between any two jobs from different groups must be at least $S$.
4.  **Arrival Time**: A job cannot start before its arrival time.

The objective is to minimize the sum of the start times of all jobs.

## Sets and Parameters

*   $J = \{0, 1, \dots, n-1\}$: Set of jobs.
*   $G_k \subseteq J$: Set of jobs belonging to group $k$, for $k \in \{0, \dots, m-1\}$.
*   $r_j$: Arrival time of job $j$.
*   $p$: Minimum time interval between adjacent jobs in the same group.
*   $S$: Minimum time interval between any two jobs from different groups.
*   $M$: A sufficiently large constant (Big-M).

## Decision Variables

*   $t_j \ge 0$: Start time of job $j$, for $j \in J$.
*   $y_{ij} \in \{0, 1\}$: Binary variable for sequencing jobs $i$ and $j$ where $g_i \neq g_j$.
    *   $y_{ij} = 1$ if job $i$ precedes job $j$ (i.e., $t_j - t_i \ge S$).
    *   $y_{ij} = 0$ if job $j$ precedes job $i$ (i.e., $t_i - t_j \ge S$).
    *   Defined for pairs $(i, j)$ such that $g_i < g_j$.

## Objective Function

Minimize the total start time:
$$
\text{Minimize } \sum_{j \in J} t_j
$$

## Constraints

1.  **Arrival Time Constraints**:
    $$
    t_j \ge r_j, \quad \forall j \in J
    $$

2.  **Same Group Sequence Constraints**:
    For each group $k$, let the jobs in $G_k$ be sorted by index. Let $j$ be a job in $G_k$ and $prev(j)$ be the job immediately preceding $j$ in $G_k$.
    $$
    t_j \ge t_{prev(j)} + p, \quad \forall k, \forall j \in G_k \setminus \{\text{first job of } G_k\}
    $$

3.  **Different Group Separation Constraints**:
    For every pair of jobs $(i, j)$ such that $g_i \neq g_j$ (assume $g_i < g_j$ to avoid duplication):
    $$
    t_j \ge t_i + S - M(1 - y_{ij})
    $$
    $$
    t_i \ge t_j + S - M y_{ij}
    $$
    
    These constraints ensure that either $t_j \ge t_i + S$ (if $y_{ij}=1$) or $t_i \ge t_j + S$ (if $y_{ij}=0$).

## Solution Approach

This problem is modeled as a Mixed-Integer Linear Programming (MILP) problem.
The continuous variables $t_j$ determine the schedule, while the binary variables $y_{ij}$ resolve the disjunctive constraints for jobs in different groups.
The "Same Group" constraints are linear and enforce the fixed order within groups.
The "Different Group" constraints ensure the required separation $S$ regardless of the order, using the Big-M method.
We use the Gurobi Optimizer to solve this MILP.
