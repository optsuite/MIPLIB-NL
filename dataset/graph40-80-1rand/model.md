# Maximum Independent Defense Lines Model

## Problem Description
The problem asks to find the maximum number of independent defense lines in a network. Each defense line is a cut that partitions the network into two disconnected regions. The defense lines must be edge-disjoint, meaning each link can belong to at most one defense line.

## Mathematical Model

### Sets and Indices
- $V$: Set of stations (nodes), indexed $0$ to $n-1$.
- $E$: Set of fiber optic links (edges).
- $K$: Set of potential defense lines, $K = \{1, \dots, m\}$. We use $m$ (total number of edges) as an upper bound on the number of cuts.

### Parameters
- $n$: Number of stations.
- $m$: Number of links.

### Variables
- $z_k \in \{0, 1\}$: Binary variable, equal to 1 if defense line $k$ is active, 0 otherwise.
- $x_{v,k} \in \{0, 1\}$: Binary variable, representing the partition of vertex $v$ in defense line $k$. We assume node 0 is always in the first set ($S_k$), so $x_{0,k}=0$. If $x_{v,k}=1$, then $v$ is in the second set ($\bar{S}_k$).
- $y_{e,k} \in \{0, 1\}$: Binary variable, equal to 1 if edge $e$ is part of defense line $k$, 0 otherwise.

### Objective Function
Maximize the number of active defense lines:
$$ \text{Maximize} \quad \sum_{k \in K} z_k $$

### Constraints

1. **Edge Disjointness**: Each edge can belong to at most one active defense line.
   $$ \sum_{k \in K} y_{e,k} \le 1 \quad \forall e \in E $$

2. **Cut Definition**: An edge $e=(u,v)$ is in cut $k$ if $u$ and $v$ are in different partitions.
   $$ y_{e,k} \ge x_{u,k} - x_{v,k} \quad \forall e=(u,v) \in E, \forall k \in K $$
   $$ y_{e,k} \ge x_{v,k} - x_{u,k} \quad \forall e=(u,v) \in E, \forall k \in K $$

3. **Active Cut Validity**: If defense line $k$ is active ($z_k=1$), it must define a non-trivial partition. We fix node 0 to be in $S_k$ ($x_{0,k}=0$). To ensure the partition is non-trivial (i.e., $\bar{S}_k \neq \emptyset$), we require at least one node to be in $\bar{S}_k$.
   $$ x_{0,k} = 0 \quad \forall k \in K $$
   $$ \sum_{v \in V} x_{v,k} \ge z_k \quad \forall k \in K $$

4. **Inactive Cut Handling**: If defense line $k$ is inactive ($z_k=0$), we force all $x_{v,k}$ to 0. This implies no edges are selected for this cut.
   $$ x_{v,k} \le z_k \quad \forall v \in V, \forall k \in K $$

5. **Symmetry Breaking**: To help the solver, we enforce that active cuts are selected in order.
   $$ z_k \ge z_{k+1} \quad \forall k \in \{1, \dots, m-1\} $$
