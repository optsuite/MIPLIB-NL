# Mathematical Model

## Solution Approach
The problem is modeled as a **Fixed-Charge Network Flow Problem**, which is a variation of the Minimum Cost Flow problem. Since we pay a fixed cost to construct an edge (pipeline) and then have infinite capacity, we use binary variables to represent the construction decision and continuous variables to represent the flow. This results in a **Mixed-Integer Linear Programming (MILP)** model.

The core components are:
1.  **Network Structure**: Nodes represent locations (oil fields, refinery, transshipment points) and edges represent potential pipelines.
2.  **Flow Conservation**: Ensures that for every node, the flow in plus production equals flow out plus demand.
3.  **Fixed-Charge Logic**: We use "Big-M" constraints to link the flow variables to the binary construction variables. If an edge is not constructed (binary = 0), flow must be 0. If constructed (binary = 1), flow is bounded only by the total supply (effectively infinite).

## Problem Description
The problem asks to select a subset of directed pipeline routes to construct a network that transports oil from multiple oil fields to a single refinery. The goal is to minimize the total construction cost. Once a pipeline is built, it has infinite capacity.

## Sets
*   $N$: Set of nodes (locations).
*   $E$: Set of candidate directed edges (pipeline routes).

## Parameters
*   $b_i$: Net oil production at node $i \in N$.
    *   $b_i > 0$: Oil field (Source).
    *   $b_i < 0$: Refinery (Sink/Demand).
    *   $b_i = 0$: Transshipment point.
*   $c_{ij}$: Construction cost of edge $(i, j) \in E$.
*   $M$: A sufficiently large constant, representing the total amount of oil in the system (sum of all positive $b_i$).

## Decision Variables
*   $y_{ij} \in \{0, 1\}$: Binary variable. Equal to 1 if edge $(i, j)$ is selected for construction, 0 otherwise.
*   $x_{ij} \ge 0$: Continuous variable. Represents the amount of oil flow on edge $(i, j)$.

## Objective Function
Minimize the total construction cost:
$$ \min \sum_{(i,j) \in E} c_{ij} y_{ij} $$

## Constraints

### 1. Flow Conservation
For each node $i \in N$, the net flow out of the node must equal its net production:
$$ \sum_{j: (i,j) \in E} x_{ij} - \sum_{j: (j,i) \in E} x_{ji} = b_i, \quad \forall i \in N $$

### 2. Linking Constraints (Big-M)
Flow is only allowed on constructed edges. Since capacity is infinite if constructed, we use a Big-M constraint where $M$ is the total supply:
$$ x_{ij} \le M \cdot y_{ij}, \quad \forall (i,j) \in E $$

### 3. Variable Domains
$$ x_{ij} \ge 0, \quad \forall (i,j) \in E $$
$$ y_{ij} \in \{0, 1\}, \quad \forall (i,j) \in E $$
