# Resource Constrained Project Portfolio Selection Model

## 1. Problem Description
We aim to select a subset of candidate projects to maximize the total Net Present Value (NPV), subject to resource capacity limits and technical dependency constraints.

## 2. Mathematical Model

### Sets and Indices
*   $P = \{1, \dots, n\}$: Set of candidate projects.
*   $R = \{1, \dots, m\}$: Set of resource types.
*   $D \subseteq P \times P$: Set of dependency pairs, where $(i, k) \in D$ means project $i$ requires project $k$.

### Parameters
*   $v_i$: Net Present Value (NPV) of project $i \in P$.
*   $c_{ij}$: Consumption of resource $j \in R$ by project $i \in P$.
*   $K$: Uniform capacity limit for each resource type.

### Decision Variables
*   $x_i \in \{0, 1\}$: Binary variable, equal to 1 if project $i$ is selected, 0 otherwise.

### Objective Function
Maximize the total NPV of selected projects:
$$
\text{Maximize} \quad Z = \sum_{i \in P} v_i x_i
$$

### Constraints

1.  **Resource Capacity Constraints**:
    The total consumption of each resource type by the selected projects must not exceed the available capacity.
    $$
    \sum_{i \in P} c_{ij} x_i \le K, \quad \forall j \in R
    $$

2.  **Dependency Constraints**:
    If project $i$ is selected, then its required project $k$ must also be selected.
    $$
    x_i \le x_k, \quad \forall (i, k) \in D
    $$

3.  **Variable Domains**:
    $$
    x_i \in \{0, 1\}, \quad \forall i \in P
    $$
