# Boolean Network Attractor Problem (bnatt400)

## Problem Description
Given a Boolean network with $n$ nodes, where each node $i$ updates its state based on the states of three specific input nodes $(j, k, l)$ according to a given truth table. We want to find a **singleton attractor** (fixed point), which is a state $X = (x_1, \dots, x_n)$ such that the next state of every node is the same as its current state.

## Mathematical Model

### Sets and Indices
- $I = \{1, \dots, n\}$: Set of nodes.
- $M = \{0, \dots, 7\}$: Set of possible input configurations for a node (since there are 3 inputs).

### Parameters
- $n$: Number of nodes.
- For each node $i \in I$:
  - $j_i, k_i, l_i \in I$: Indices of the three input nodes for node $i$.
  - $b_{i,m} \in \{0, 1\}$ for $m \in M$: Truth table value for input configuration $m$.
    - $m=0 \implies (0,0,0)$
    - $m=1 \implies (0,0,1)$
    - ...
    - $m=7 \implies (1,1,1)$

### Decision Variables
- $x_i \in \{0, 1\}$: State of node $i$.
- $z_{i,m} \in \{0, 1\}$: Auxiliary binary variable, equal to 1 if the input configuration for node $i$ is $m$, and 0 otherwise.

### Objective Function
The goal is to find any feasible fixed point. We set a dummy objective:
$$ \min x_1 $$

### Constraints

1. **Unique Configuration Constraint**:
   For each node $i$, exactly one input configuration must be active.
   $$ \sum_{m=0}^7 z_{i,m} = 1, \quad \forall i \in I $$

2. **Input Consistency Constraints**:
   The active configuration $z_{i,m}$ must match the actual states of the input nodes $x_{j_i}, x_{k_i}, x_{l_i}$.
   
   - For the first input $j_i$ (corresponding to the most significant bit, weight 4):
     $$ x_{j_i} = \sum_{m \in \{4,5,6,7\}} z_{i,m}, \quad \forall i \in I $$
   
   - For the second input $k_i$ (corresponding to the middle bit, weight 2):
     $$ x_{k_i} = \sum_{m \in \{2,3,6,7\}} z_{i,m}, \quad \forall i \in I $$
   
   - For the third input $l_i$ (corresponding to the least significant bit, weight 1):
     $$ x_{l_i} = \sum_{m \in \{1,3,5,7\}} z_{i,m}, \quad \forall i \in I $$

3. **Fixed Point Constraint**:
   The state of node $i$ must equal the output of its update function given the inputs.
   $$ x_i = \sum_{m=0}^7 b_{i,m} z_{i,m}, \quad \forall i \in I $$

## Solution Approach
We model the problem as a Mixed-Integer Linear Programming (MILP) problem. The truth table logic is linearized using auxiliary variables $z_{i,m}$ which select the active row of the truth table for each node. The constraints ensure that the selected row corresponds to the actual values of the input nodes, and that the node's own value matches the function output.
