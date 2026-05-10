# Crew Scheduling Problem (Rail507)

## Problem Description

The problem asks us to select a subset of crew work plans (packages) to cover a set of train tasks at minimum cost. Each package covers a specific set of tasks and has an associated cost based on its difficulty ('easy' or 'hard'). There is also a constraint on the maximum number of 'hard' packages that can be selected.

## Mathematical Model

### Sets and Indices

*   $J = \{1, \dots, n\_packages\}$: The set of all available crew packages.
*   $I = \{1, \dots, n\_tasks\}$: The set of all train tasks to be covered.
*   $J_{easy} \subset J$: The set of 'easy' packages.
*   $J_{hard} \subset J$: The set of 'hard' packages.
*   $P_i \subseteq J$: The set of packages that cover task $i \in I$.

### Parameters

*   $c_j$: The cost of package $j \in J$.
    *   $c_j = 1$ if $j \in J_{easy}$.
    *   $c_j = 2$ if $j \in J_{hard}$.
*   $L$: The maximum allowed number of 'hard' packages (`hard_packages_limit`).

### Decision Variables

*   $x_j \in \{0, 1\}$: A binary variable equal to 1 if package $j$ is selected, and 0 otherwise.

### Objective Function

Minimize the total cost of the selected packages:

$$
\text{Minimize} \quad Z = \sum_{j \in J} c_j x_j
$$

### Constraints

1.  **Task Coverage Constraints**: Each task $i$ must be covered by at least one selected package.

    $$
    \sum_{j \in P_i} x_j \ge 1, \quad \forall i \in I
    $$

2.  **Resource Constraint (Hard Packages Limit)**: The total number of selected 'hard' packages must not exceed the limit $L$.

    $$
    \sum_{j \in J_{hard}} x_j \le L
    $$

3.  **Binary Constraints**:

    $$
    x_j \in \{0, 1\}, \quad \forall j \in J
    $$
