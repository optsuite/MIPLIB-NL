# Mathematical Model: Fixed-Charge Network Flow Problem

## Problem Overview

A fixed-charge network flow problem where selecting an arc incurs a fixed cost, and flow through the arc is limited by a capacity constraint.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{N}$: Set of nodes in the network, $|\mathcal{N}| = n$
- $\mathcal{A}$: Set of arcs in the network, $|\mathcal{A}| = m$
- $i \in \mathcal{N}$: Index for nodes
- $(i,j) \in \mathcal{A}$: Index for arcs connecting node $i$ to node $j$

### 2. Decision Variables

- $x_{ij} \geq 0$: Continuous variable, flow on arc $(i,j)$
- $y_{ij} \in \{0,1\}$: Binary variable, 1 if arc $(i,j)$ is used, 0 otherwise

### 3. Parameters

- $f_{ij} \geq 0$: Fixed cost for using arc $(i,j)$
- $u_{ij} > 0$: Capacity of arc $(i,j)$ (maximum flow if arc is used)
- $b_i \in \mathbb{R}$: Flow balance requirement at node $i$ (supply if positive, demand if negative)
- $\delta^{+}(i)$: Set of arcs leaving node $i$
- $\delta^{-}(i)$: Set of arcs entering node $i$

### 4. Objective Function

$$\text{minimize} \quad Z = \sum_{(i,j) \in \mathcal{A}} f_{ij} y_{ij}$$

### 5. Constraints

#### 5.1 Flow Balance Constraints

For each node $i \in \mathcal{N}$:

$$\sum_{(i,j) \in \delta^{+}(i)} x_{ij} - \sum_{(j,i) \in \delta^{-}(i)} x_{ji} = b_i$$

#### 5.2 Capacity Constraints

For each arc $(i,j) \in \mathcal{A}$:

$$x_{ij} \leq u_{ij} y_{ij}$$

#### 5.3 Variable Type Constraints

$$x_{ij} \geq 0, \quad \forall (i,j) \in \mathcal{A}$$
$$y_{ij} \in \{0,1\}, \quad \forall (i,j) \in \mathcal{A}$$

### 6. Complete Mathematical Model

$$
\begin{align}
\text{minimize} \quad & Z = \sum_{(i,j) \in \mathcal{A}} f_{ij} y_{ij} \\
\text{subject to} \quad & \sum_{(i,j) \in \delta^{+}(i)} x_{ij} - \sum_{(j,i) \in \delta^{-}(i)} x_{ji} = b_i, \quad \forall i \in \mathcal{N} \\
& x_{ij} \leq u_{ij} y_{ij}, \quad \forall (i,j) \in \mathcal{A} \\
& x_{ij} \geq 0, \quad \forall (i,j) \in \mathcal{A} \\
& y_{ij} \in \{0,1\}, \quad \forall (i,j) \in \mathcal{A}
\end{align}
$$

## Model Properties

- **Problem Type**: Mixed-Integer Linear Programming (MILP)
- **Objective**: Minimize total fixed costs of selected arcs
- **Structure**: Network flow with fixed charges
- **Complexity**: NP-hard due to binary decisions

## Key Insights

1. **Fixed-Charge Nature**: Binary variable $y_{ij}$ acts as a switch - if $y_{ij} = 0$, no flow can pass through arc $(i,j)$; if $y_{ij} = 1$, the arc incurs fixed cost $f_{ij}$ and can carry flow up to capacity $u_{ij}$.

2. **Flow Conservation**: Each node must satisfy flow balance - total inflow equals total outflow plus any supply/demand at the node.

3. **Economic Interpretation**: This models transportation or distribution network design where opening a route (arc) incurs a fixed cost but allows unlimited flow up to capacity.