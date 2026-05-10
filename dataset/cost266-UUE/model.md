# Network Design Problem Model

## Problem Description
Given a telecommunications network with cities (nodes) and potential links, the goal is to install capacity modules on links to satisfy traffic demands between cities at minimum total cost. The total cost consists of the fixed installation cost of modules and the variable routing cost of traffic.

## Mathematical Model

### Sets
*   $N$: Set of nodes (cities).
*   $E$: Set of potential links (undirected).
*   $K$: Set of traffic demands.
*   $M$: Set of available capacity modules.

### Parameters
*   $h^k$: Traffic volume required by demand $k \in K$.
*   $s^k$: Source node of demand $k$.
*   $t^k$: Destination node of demand $k$.
*   $c_{ij}$: Routing cost per unit flow on link $\{i,j\} \in E$.
*   $u_m$: Capacity of module type $m \in M$.
*   $f_{ij}^m$: Fixed cost of installing module type $m$ on link $\{i,j\} \in E$.

### Variables
*   $x_{ij}^k \ge 0$: Flow of demand $k$ on arc $(i,j)$. Note that for each undirected link $\{i,j\} \in E$, we consider two directed arcs $(i,j)$ and $(j,i)$.
*   $y_{ij}^m \in \{0, 1\}$: Binary variable, equal to 1 if module type $m$ is installed on link $\{i,j\}$, 0 otherwise.

### Objective Function
Minimize the total cost, which is the sum of module installation costs and traffic routing costs:
$$ \min \sum_{\{i,j\} \in E} \sum_{m \in M} f_{ij}^m y_{ij}^m + \sum_{k \in K} \sum_{(i,j) \in A} c_{ij} x_{ij}^k $$
where $A$ is the set of all directed arcs corresponding to links in $E$.

### Constraints

1.  **Flow Conservation:**
    For each demand $k \in K$ and each node $i \in N$:
    $$ \sum_{j: (i,j) \in A} x_{ij}^k - \sum_{j: (j,i) \in A} x_{ji}^k = \begin{cases} h^k & \text{if } i = s^k \\ -h^k & \text{if } i = t^k \\ 0 & \text{otherwise} \end{cases} $$

2.  **Capacity Constraints:**
    The total flow on a link (sum of flows in both directions) must not exceed the capacity of the installed module.
    $$ \sum_{k \in K} (x_{ij}^k + x_{ji}^k) \le \sum_{m \in M} u_m y_{ij}^m \quad \forall \{i,j\} \in E $$

3.  **Module Selection:**
    At most one module type can be installed on any link.
    $$ \sum_{m \in M} y_{ij}^m \le 1 \quad \forall \{i,j\} \in E $$

4.  **Variable Domains:**
    $$ x_{ij}^k \ge 0 \quad \forall (i,j) \in A, k \in K $$
    $$ y_{ij}^m \in \{0, 1\} \quad \forall \{i,j\} \in E, m \in M $$
