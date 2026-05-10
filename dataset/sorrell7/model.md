# Maximum Independent Set for Error Detection Code

## Problem Description
The problem asks for the maximum number of binary sequences of length $n$ (codewords) that can be selected such that the set is capable of detecting any single bit flip or single bit swap error. This requirement implies that no two selected codewords can be transformed into each other by a single bit flip or a single bit swap.

This can be modeled as a Maximum Independent Set problem on a graph where vertices represent all possible binary sequences, and edges represent the "conflicting" relationships defined by the error types.

## Graph Construction
Let $G=(V, E)$ be a graph where the vertex set $V = \{0, 1\}^n$ represents all binary sequences of length $n$.
Two vertices $u, v \in V$ are connected by an edge $(u, v) \in E$ if they satisfy one of the following conditions:
1.  **Bit Flip Conflict**: The Hamming distance between $u$ and $v$ is exactly 1.
    $$ d_H(u, v) = 1 $$
2.  **Bit Swap Conflict**: The Hamming distance between $u$ and $v$ is exactly 2, and they have the same Hamming weight (number of 1s). This corresponds to swapping a 0 and a 1 at different positions.
    $$ d_H(u, v) = 2 \quad \text{and} \quad w(u) = w(v) $$

## Mathematical Model

### Variables
Let $x_i$ be a binary decision variable for each sequence $i \in V$:
$$
x_i = \begin{cases} 
1 & \text{if sequence } i \text{ is selected} \\
0 & \text{otherwise}
\end{cases}
$$

### Objective Function
Maximize the total number of selected codewords:
$$ \text{Maximize} \quad \sum_{i \in V} x_i $$

### Constraints
For every pair of conflicting sequences (connected by an edge), at most one can be selected:
$$ x_i + x_j \le 1 \quad \forall (i, j) \in E $$

### Variable Domains
$$ x_i \in \{0, 1\} \quad \forall i \in V $$
