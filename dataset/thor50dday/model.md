# Steiner Tree Problem Model

## Problem Description
The problem asks us to find a minimum cost network that connects a specific subset of cities (core data centers) within a larger set of cities. This is a classic **Steiner Tree Problem** in graphs. We are given a graph $G=(V, E)$ with edge weights (distances), and a set of terminal nodes $S \subseteq V$. The goal is to find a subgraph $T$ that connects all nodes in $S$ such that the sum of edge weights in $T$ is minimized.

## Mathematical Formulation
We use a **Single-Commodity Flow** formulation to model the connectivity requirements.

### Sets and Parameters
*   $V$: Set of all cities (nodes), indexed $0$ to $n_{cities}-1$.
*   $E$: Set of possible fiber optic links (undirected edges).
*   $S \subseteq V$: Set of core cities (terminals) that must be connected.
*   $d_{ij}$: Distance (cost) of the link between city $i$ and city $j$.
*   $r \in S$: An arbitrarily selected root node from the set of core cities.

### Decision Variables
*   $x_{ij} \in \{0, 1\}$: Binary variable for each edge $\{i, j\} \in E$.
    *   $x_{ij} = 1$ if the edge $\{i, j\}$ is selected in the network.
    *   $x_{ij} = 0$ otherwise.
    *   Note: Since edges are undirected, $x_{ij}$ represents the connection between $i$ and $j$ regardless of direction. We assume $i < j$ for uniqueness.
*   $f_{ij} \ge 0$: Continuous variable representing the flow from city $i$ to city $j$.
    *   Defined for both directed arcs $(i, j)$ and $(j, i)$ corresponding to each edge $\{i, j\} \in E$.

### Objective Function
Minimize the total length of the fiber optic network:
$$ \min \sum_{\{i, j\} \in E} d_{ij} x_{ij} $$

### Constraints

1.  **Flow Conservation:**
    We treat the root node $r$ as a source of $|S|-1$ units of flow, and every other terminal node $t \in S \setminus \{r\}$ as a sink consuming 1 unit of flow. Non-terminal nodes (Steiner nodes) act as transshipment nodes with net flow 0.

    *   **Source (Root):**
        $$ \sum_{j: \{r, j\} \in E} (f_{rj} - f_{jr}) = |S| - 1 $$

    *   **Sinks (Other Terminals):**
        $$ \sum_{j: \{t, j\} \in E} (f_{jt} - f_{tj}) = 1 \quad \forall t \in S \setminus \{r\} $$

    *   **Transshipment (Non-Terminals):**
        $$ \sum_{j: \{k, j\} \in E} (f_{kj} - f_{jk}) = 0 \quad \forall k \in V \setminus S $$

2.  **Capacity / Coupling Constraints:**
    Flow is only allowed on an arc if the corresponding undirected edge is selected. The maximum possible flow on any link is $|S|-1$.
    $$ f_{ij} \le (|S| - 1) x_{ij} \quad \forall \{i, j\} \in E $$
    $$ f_{ji} \le (|S| - 1) x_{ij} \quad \forall \{i, j\} \in E $$

3.  **Variable Domains:**
    $$ x_{ij} \in \{0, 1\} $$
    $$ f_{ij} \ge 0 $$
