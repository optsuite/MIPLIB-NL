# Mathematical Model

## Problem Description
The problem is a classic Set Partitioning Problem (SPP). We are given a set of flights and a set of candidate crew pairings. Each pairing covers a subset of flights and has an associated cost. The goal is to select a subset of pairings such that every flight is covered exactly once, minimizing the total cost.

## Sets
*   $F$: Set of flights, indexed by $i = 1, \dots, n$.
*   $P$: Set of candidate pairings, indexed by $j = 1, \dots, m$.

## Parameters
*   $c_j$: The cost of pairing $j$.
*   $a_{ij}$: A binary parameter that is equal to 1 if flight $i$ is covered by pairing $j$, and 0 otherwise.

## Decision Variables
*   $x_j \in \{0, 1\}$: A binary variable that is equal to 1 if pairing $j$ is selected, and 0 otherwise.

## Objective Function
Minimize the total operational cost:
$$
\min \sum_{j \in P} c_j x_j
$$

## Constraints
**Flight Coverage Constraints:**
Each flight $i$ must be covered by exactly one selected pairing:
$$
\sum_{j \in P} a_{ij} x_j = 1, \quad \forall i \in F
$$
