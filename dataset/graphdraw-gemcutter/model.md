# Mathematical Model: Graph Drawing (Phase 1 — Entity Placement)

## Problem Overview

In the first phase of an automated diagram layout pipeline, a set of entities (symbols) must be placed on a discrete 2D grid. The placement should be readable and visually coherent: entities must not overlap, and connected entities should be close to reduce edge lengths. The model selects a consistent relative placement (above/below/left/right) for every pair of entities, enforces minimum separations derived from symbol sizes, and minimizes a weighted sum of connection lengths with a small centering term.

## Sets and Indices

- $\mathcal{N}$: entities (nodes), indexed by $i,j,k$
- $\mathcal{A} = \{r,c\}$: axes (row and column), indexed by $a$
- $\mathcal{P} = \{(i,j) \in \mathcal{N}\times\mathcal{N}: i<j\}$: unordered entity pairs
- $\mathcal{E} \subseteq \mathcal{P}$: edges (relationships to be shortened), indexed by $(u,v)$
- $\mathcal{D} = \{\text{lb},\text{rt}\}$: opposite directions along an axis, indexed by $d$

## Parameters

- $L^{\min}_{a,i} \le L^{\max}_{a,i}$: inclusive bounds for entity $i$ on axis $a$
- $\Delta_{a,d,i,j} \ge 0$: minimum coordinate difference activated by selecting direction $d$ on axis $a$ for pair $(i,j)$
- $\rho_{u,v} \ge 0$: lower bound on the Manhattan separation for edge $(u,v)$
- $\alpha \ge 0$: edge-length weight in the objective
- $\beta \ge 0$: centering weight in the objective
- $(A_{\text{row},i}, A_{\text{col},i})$: preferred anchor coordinates for entity $i$
- $\Gamma \ge 0$: a lower bound on the total centering term (as present in the source MPS)
- Edge-axis constants (from data): $\kappa^{(1)}_{a,u,v}$, $\kappa^{(2)}_{a,u,v}$ and $\eta_{a,u,v}$ used in the distance linearization for edge $(u,v)$ on axis $a$

## Decision Variables

- $\text{row}_i \in \mathbb{Z}$: row coordinate of entity $i$
- $\text{col}_i \in \mathbb{Z}$: column coordinate of entity $i$
- $z^{\text{row}\rightarrow}_{i,j} \in \{0,1\}$: 1 if $i$ is placed before $j$ on the row axis (so $\text{row}_j-\text{row}_i$ is enforced)
- $z^{\text{row}\leftarrow}_{i,j} \in \{0,1\}$: 1 if $j$ is placed before $i$ on the row axis
- $z^{\text{col}\rightarrow}_{i,j} \in \{0,1\}$: 1 if $i$ is placed before $j$ on the column axis
- $z^{\text{col}\leftarrow}_{i,j} \in \{0,1\}$: 1 if $j$ is placed before $i$ on the column axis
- $d^{\text{row}}_{u,v} \ge 0$: auxiliary row distance for edge $(u,v)$
- $d^{\text{col}}_{u,v} \ge 0$: auxiliary column distance for edge $(u,v)$
- $c^{\text{row}}_i \ge 0$, $c^{\text{col}}_i \ge 0$: absolute deviations from the preferred anchor

## Objective Function

Minimize weighted edge length plus a centering term:
$$
\min \; \alpha \sum_{(u,v)\in\mathcal{E}} \sum_{a\in\mathcal{A}} d_{a,u,v}
\;+\; \beta \sum_{i\in\mathcal{N}} \sum_{a\in\mathcal{A}} c_{a,i}.
$$

## Constraints

1. **Bounds (placement window)**
$$
L^{\min}_{\text{row},i} \le \text{row}_i \le L^{\max}_{\text{row},i}, \quad \forall i\in\mathcal{N},
$$
$$
L^{\min}_{\text{col},i} \le \text{col}_i \le L^{\max}_{\text{col},i}, \quad \forall i\in\mathcal{N}.
$$

2. **Exactly one relative relation per pair**

For each unordered pair $(i,j)$, select exactly one of four relation types:
$$
z^{\text{row}\rightarrow}_{i,j} + z^{\text{row}\leftarrow}_{i,j} + z^{\text{col}\rightarrow}_{i,j} + z^{\text{col}\leftarrow}_{i,j} = 1,
\quad \forall (i,j)\in\mathcal{P}.
$$

3. **Minimum separation if a relation is chosen**

If $(i,j)$ is separated along axis $a$ in direction `lb`, then $j$ must be at least $\Delta_{a,\text{lb},i,j}$ units “after” $i$ on that axis:
$$
z^{\text{row}\rightarrow}_{i,j}=1 \;\Rightarrow\; \text{row}_j - \text{row}_i \ge \Delta_{\text{row},i\rightarrow j},
\quad \forall (i,j)\in\mathcal{P},
$$
Similarly for direction `rt`:
$$
z^{\text{row}\leftarrow}_{i,j}=1 \;\Rightarrow\; \text{row}_i - \text{row}_j \ge \Delta_{\text{row},j\rightarrow i},
\quad \forall (i,j)\in\mathcal{P},
$$
and analogously for the column axis using $z^{\text{col}\rightarrow}_{i,j}$ and $z^{\text{col}\leftarrow}_{i,j}$.

These implications can be implemented as indicator constraints (preferred for clarity) or as big-$M$ constraints. The values of $\Delta$ are provided directly in `data/pair_relations.csv` and match the original MPS.

4. **Consistency (transitivity) constraints**

The model includes triangle (cycle-prevention) inequalities over triples $(i,j,k)$ to avoid contradictory relations along a given axis. Intuitively, you cannot have $i$ before $j$, $j$ before $k$, and $k$ before $i$ on the same axis.

Using the directed relation binaries (e.g., $z^{\text{row}\rightarrow}_{i,j}$ for “$i$ before $j$ on rows”, and $z^{\text{row}\leftarrow}_{i,j}$ for “$j$ before $i$ on rows”), one convenient way to encode the same logic as the source MPS is:

For every axis (row/col) and every triple of distinct entities $(i,j,k)$, add both constraints:
$$
z_{i\rightarrow k} + z_{i\leftarrow j} + z_{j\leftarrow k} \le 2,
$$
$$
z_{i\rightarrow j} + z_{j\rightarrow k} + z_{i\leftarrow k} \le 2.
$$

Here $z_{\cdot}$ refers to the corresponding axis-specific relation variable (row or column). These two constraints rule out the two cyclic patterns that would otherwise be possible across three pairs.

5. **Edge distance linearization**

For each edge $(u,v)$ and axis $a$, define $d_{a,u,v}$ using two inequalities with constants taken from data:
$$
d^{\text{row}}_{u,v} + (\text{row}_v - \text{row}_u) \ge \kappa^{(1)}_{\text{row},u,v},
$$
$$
d^{\text{row}}_{u,v} + (\text{row}_u - \text{row}_v) \ge \kappa^{(2)}_{\text{row},u,v},
$$
and similarly for the column axis:
$$
d^{\text{col}}_{u,v} + (\text{col}_v - \text{col}_u) \ge \kappa^{(1)}_{\text{col},u,v},
$$
$$
d^{\text{col}}_{u,v} + (\text{col}_u - \text{col}_v) \ge \kappa^{(2)}_{\text{col},u,v}.
$$

Additionally, the model enforces an axis-specific minimum separation requirement $\eta_{a,u,v}$ for edge endpoints when they are separated along that axis (as used in the source MPS).

6. **Manhattan lower bound for edges**
$$
d^{\text{row}}_{u,v} + d^{\text{col}}_{u,v} \ge \rho_{u,v}, \quad \forall (u,v)\in\mathcal{E}.
$$

7. **Anchor preference (absolute deviation)**

For each entity $i$ and axis $a$, $c_{a,i}$ lower-bounds the absolute deviation from the anchor coordinate $A_{a,i}$:
$$
c^{\text{row}}_i \ge \text{row}_i - A_{\text{row},i},\quad
c^{\text{row}}_i \ge A_{\text{row},i} - \text{row}_i,
$$
$$
c^{\text{col}}_i \ge \text{col}_i - A_{\text{col},i},\quad
c^{\text{col}}_i \ge A_{\text{col},i} - \text{col}_i.
$$

The source MPS also includes:
$$
\sum_{i\in\mathcal{N}} \left(c^{\text{row}}_i + c^{\text{col}}_i\right) \ge \Gamma.
$$

## Notes on Data Mapping

- $\mathcal{N}$ and coordinate bounds $L^{\min}, L^{\max}$ come from `data/entities.csv`.
- $(A_{\text{row},i}, A_{\text{col},i})$ come from `data/entities.csv` (`preferred_row`, `preferred_col`); $\Gamma$ is given in `instance.json`.
- $\mathcal{E}$, $\rho_{u,v}$, and objective weight $\alpha$ come from `data/edges.csv`.
- $\kappa^{(1)}, \kappa^{(2)}, \eta$ and distance upper bounds come from `data/edge_distance_params.csv`.
- Pairwise minimum separations $\Delta$ come from `data/pair_relations.csv`.
