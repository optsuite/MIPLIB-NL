# Water Supply Network Optimization Model

## Problem Overview
The goal is to construct a water supply network to transport water from a single source node to multiple demand nodes in a drought-stricken region. The network must form a tree structure (specifically, an arborescence rooted at the source), where each node has at most one incoming edge. The objective is to minimize the total cost, which consists of fixed construction costs for the pipelines and variable costs based on the volume of water flow.

## Mathematical Model

### Sets and Indices
- $V$: Set of nodes, $V = \{1, 2, \dots, n\}$.
- $E$: Set of potential undirected edges $\{i, j\}$ provided in the data.
- $A$: Set of directed arcs $(i, j)$ and $(j, i)$ for each $\{i, j\} \in E$.
- $S \in V$: The source node (ID specified in `parameters`).

### Parameters
- $d_i$: Net supply or demand at node $i$. $d_i > 0$ for supply, $d_i < 0$ for demand, and $d_i = 0$ for transit nodes.
- $FC_{ij}$: Fixed construction cost for edge $\{i, j\}$.
- $VC_{ij}$: Variable cost per unit of flow for edge $\{i, j\}$.
- $M$: A large constant (Big-M), typically the total supply available at the source.

### Decision Variables
- $x_{ij} \in \{0, 1\}$: Binary variable, 1 if a pipeline is constructed between nodes $i$ and $j$, 0 otherwise.
- $y_{ij} \in \{0, 1\}$: Binary variable, 1 if water flows from node $i$ to node $j$, 0 otherwise.
- $q_{ij} \ge 0$: Continuous variable representing the quantity of water flowing from node $i$ to node $j$.

### Objective Function
Minimize the total cost (Construction Cost + Flow Cost):
$$ \min Z = \sum_{\{i, j\} \in E} FC_{ij} x_{ij} + \sum_{(i, j) \in A} VC_{ij} q_{ij} $$

### Constraints

1. **Flow Balance:**
   For each node $i \in V$:
   $$ \sum_{j: (i, j) \in A} q_{ij} - \sum_{j: (j, i) \in A} q_{ji} = d_i $$

2. **Capacity and Fixed Charge Linking:**
   For each directed arc $(i, j) \in A$:
   $$ q_{ij} \le M \cdot y_{ij} $$
   This ensures that flow only occurs if the directed arc is active.

3. **Edge and Arc Relationship:**
   For each edge $\{i, j\} \in E$:
   $$ y_{ij} + y_{ji} = x_{ij} $$
   This ensures that if a pipeline is built, it is used in exactly one direction (consistent with a tree structure flowing away from the source), and if not built, no flow can occur in either direction.

4. **Tree Structure (Arborescence):**
   Each node (except the source) can have at most one incoming edge:
   For each node $i \in V \setminus \{S\}$:
   $$ \sum_{j: (j, i) \in A} y_{ji} \le 1 $$
   For the source node $S$:
   $$ \sum_{j: (j, S) \in A} y_{jS} = 0 $$

5. **Variable Domains:**
   - $x_{ij} \in \{0, 1\}$ for all $\{i, j\} \in E$
   - $y_{ij} \in \{0, 1\}$ for all $(i, j) \in A$
   - $q_{ij} \ge 0$ for all $(i, j) \in A$
