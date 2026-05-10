# Mathematical Model: Graph Drawing (Phase 1 — Entity Placement)

## Problem Overview

In the first phase of an automated diagram layout pipeline, a set of entities (symbols) must be placed on a discrete 2D grid. The placement should be readable and visually coherent: entities must not overlap, and connected entities should be close to reduce edge lengths. The model selects a consistent relative placement (above/below/left/right) for every pair of entities, enforces minimum separations derived from symbol sizes, and minimizes a weighted sum of connection lengths with a small centering term.

## Sets and Indices

- $\mathcal{N}$: entities (nodes), indexed by $i,j,k$
- $\mathcal{P} = \{(i,j) \in \mathcal{N}\times\mathcal{N}: i<j\}$: unordered entity pairs
- $\mathcal{E} \subseteq \mathcal{P}$: edges (relationships to be shortened), indexed by $(u,v)$

## Parameters

- $L^{\min}_{\text{row},i} \le L^{\max}_{\text{row},i}$: inclusive bounds for entity $i$ on the row axis
- $L^{\min}_{\text{col},i} \le L^{\max}_{\text{col},i}$: inclusive bounds for entity $i$ on the column axis
- $\Delta_{\text{row},i\rightarrow j}$, $\Delta_{\text{row},j\rightarrow i}$: minimum row separations for pair $(i,j)$ under the two row directions
- $\Delta_{\text{col},i\rightarrow j}$, $\Delta_{\text{col},j\rightarrow i}$: minimum column separations for pair $(i,j)$ under the two column directions
- $\rho_{u,v}$: lower bound on the Manhattan separation for edge $(u,v)$
- $\alpha_{u,v}$: edge-length weight in the objective (provided per edge)
- $\beta$: centering weight
- $(A_{\text{row},i}, A_{\text{col},i})$: preferred anchor coordinates for entity $i$
- $\Gamma$: a lower bound on the total centering deviation (as present in the source instance)

## Decision Variables

- $\text{row}_i \in \mathbb{Z}$: row coordinate of entity $i$
- $\text{col}_i \in \mathbb{Z}$: column coordinate of entity $i$
- For each pair $(i,j)$, one of four binary relations is selected:
  - `row_i_before_j`, `row_j_before_i`, `col_i_before_j`, `col_j_before_i`
- $d^{\text{row}}_{u,v} \ge 0$, $d^{\text{col}}_{u,v} \ge 0$: auxiliary distances for edge $(u,v)$
- $c^{\text{row}}_i \ge 0$, $c^{\text{col}}_i \ge 0$: deviations from the reference center

## Objective Function

Minimize weighted edge length plus a centering term:
$$
\min \sum_{(u,v)\in\mathcal{E}} \alpha_{u,v}\,\bigl(d^{\text{row}}_{u,v}+d^{\text{col}}_{u,v}\bigr)
\;+\; \beta \sum_{i\in\mathcal{N}} \left(c^{\text{row}}_i + c^{\text{col}}_i\right).
$$

## Constraints

1. **Bounds (placement window)**
$$
L^{\min}_{\text{row},i} \le \text{row}_i \le L^{\max}_{\text{row},i},\quad
L^{\min}_{\text{col},i} \le \text{col}_i \le L^{\max}_{\text{col},i}, \quad \forall i\in\mathcal{N}.
$$

2. **Exactly one relation per pair**
$$
z^{\text{row}\rightarrow}_{i,j} + z^{\text{row}\leftarrow}_{i,j} + z^{\text{col}\rightarrow}_{i,j} + z^{\text{col}\leftarrow}_{i,j} = 1,
\quad \forall (i,j)\in\mathcal{P}.
$$

3. **Minimum separation when a relation is chosen**

For example, if `row_i_before_j` is chosen then:
$$
\text{row}_j - \text{row}_i \ge \Delta_{\text{row},i\rightarrow j}.
$$
Analogous implications hold for the other three relations.

4. **Triangle (cycle-prevention) rules**

For every axis (row/col) and every triple of distinct entities $(i,j,k)$, add both inequalities:
$$
z_{i\rightarrow k} + z_{j\rightarrow i} + z_{k\rightarrow j} \le 2,\quad
z_{i\rightarrow j} + z_{j\rightarrow k} + z_{k\rightarrow i} \le 2,
$$
where $z_{\cdot}$ is the corresponding axis-specific directed relation variable.

5. **Edge distance linearization and Manhattan lower bound**

The instance provides constants that define linear inequalities linking $d^{\text{row}}_{u,v}$ and $d^{\text{col}}_{u,v}$ to endpoint coordinates, and enforces:
$$
d^{\text{row}}_{u,v} + d^{\text{col}}_{u,v} \ge \rho_{u,v}, \quad \forall (u,v)\in\mathcal{E}.
$$

6. **Anchor deviation**
$$
c^{\text{row}}_i \ge \text{row}_i - A_{\text{row},i},\quad c^{\text{row}}_i \ge A_{\text{row},i} - \text{row}_i,
$$
$$
c^{\text{col}}_i \ge \text{col}_i - A_{\text{col},i},\quad c^{\text{col}}_i \ge A_{\text{col},i} - \text{col}_i.
$$
and the source instance includes:
$$
\sum_{i\in\mathcal{N}} \left(c^{\text{row}}_i + c^{\text{col}}_i\right) \ge \Gamma.
$$

## Notes on Data Mapping

- $\mathcal{N}$ and coordinate bounds come from `data/entities.csv`.
- $\mathcal{E}$, $\rho_{u,v}$, and edge weights $\alpha_{u,v}$ come from `data/edges.csv`.
- Axis-specific distance constants and upper bounds come from `data/edge_distance_params.csv`.
- Pairwise minimum separations come from `data/pair_relations.csv`.
- Anchor coordinates come from `data/entities.csv` (`preferred_row`, `preferred_col`); $\Gamma$ is given in `instance.json`.
