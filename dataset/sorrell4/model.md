# Maximum Size Code Set with LCS Constraint

## Problem Description
The problem asks for the maximum number of binary sequences of length $n$ such that the Longest Common Subsequence (LCS) of any pair of selected sequences is strictly less than a threshold $K$.

## Mathematical Model

This problem can be modeled as a **Maximum Independent Set** problem on a specific graph.

### Sets and Parameters
*   $n$: Length of the binary sequences (`n_bits`).
*   $K$: The LCS threshold (`lcs_threshold`).
*   $V$: The set of all possible binary sequences of length $n$. The size of $V$ is $2^n$.
*   $LCS(u, v)$: The length of the longest common subsequence between sequence $u$ and sequence $v$.

### Graph Construction
Construct an undirected graph $G = (V, E)$ where:
*   The vertices $V$ correspond to all $2^n$ binary sequences.
*   An edge $(u, v) \in E$ exists between two distinct sequences $u$ and $v$ if and only if $LCS(u, v) \ge K$.

The condition "LCS strictly less than $K$" means we cannot select both $u$ and $v$ if $LCS(u, v) \ge K$. This corresponds to the independent set constraint on graph $G$.

### Decision Variables
Let $x_i$ be a binary decision variable for each sequence $i \in V$:
$$
x_i = \begin{cases} 
1 & \text{if sequence } i \text{ is selected} \\
0 & \text{otherwise}
\end{cases}
$$

### Objective Function
Maximize the total number of selected sequences:
$$
\text{Maximize } \sum_{i \in V} x_i
$$

### Constraints
For every pair of sequences $(i, j)$ such that they have an edge in $G$ (i.e., $LCS(i, j) \ge K$):
$$
x_i + x_j \le 1 \quad \forall (i, j) \in E
$$

This ensures that no two sequences with an LCS of length $K$ or greater are selected simultaneously.
