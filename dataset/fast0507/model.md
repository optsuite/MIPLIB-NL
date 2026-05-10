# Mathematical Model

## Problem Description
The problem asks us to select a subset of crew packages to cover all train tasks such that the total cost is minimized. Each package has a specific cost based on its difficulty ('easy' = 1, 'hard' = 2). This is a classic Set Covering Problem.

## Sets and Indices
*   $J = \{1, \dots, n\_packages\}$: Set of all available crew packages.
*   $I = \{1, \dots, n\_tasks\}$: Set of all train tasks to be covered.
*   $P_i \subseteq J$: Set of packages that cover task $i$. This is derived from the `package_task` data.

## Parameters
*   $c_j$: Cost of package $j$.
    *   $c_j = 1$ if package $j$ is 'easy'.
    *   $c_j = 2$ if package $j$ is 'hard'.

## Decision Variables
*   $x_j \in \{0, 1\}$: Binary variable.
    *   $x_j = 1$ if package $j$ is selected.
    *   $x_j = 0$ otherwise.

## Objective Function
Minimize the total cost of selected packages:
$$
\text{Minimize } Z = \sum_{j \in J} c_j x_j
$$

## Constraints
1.  **Task Coverage Constraints**: Each task $i$ must be covered by at least one selected package.
    $$
    \sum_{j \in P_i} x_j \ge 1, \quad \forall i \in I
    $$
