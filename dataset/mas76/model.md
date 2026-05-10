# Mathematical Model: Cutting Stock with Pre-Generated Patterns

## Problem Overview

The instance `mas76` models a cutting stock (trim loss) problem for a paper mill. Large jumbo rolls of paper must be cut into smaller item types to satisfy demand. A finite set of pre-generated cutting patterns is available, and each pattern specifies how much of each item type is produced when that pattern is used. The planner must decide which patterns to use, subject to a limit on the total number of rolls that can be processed, so that the combined output of all selected patterns meets or exceeds the demand for every item type.

In addition, the instance includes an expensive emergency option that can cover remaining demand shortfalls. This emergency option contributes one unit to every item type simultaneously per unit of emergency usage and is penalized heavily in the objective.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{P}$: set of cutting patterns, indexed by $p$
- $\mathcal{I}$: set of item types, indexed by $i$

### 2. Decision Variables

- $x_p \in \{0,1\}$: 1 if pattern $p$ is selected (used at most once), 0 otherwise
- $y \ge 0$: emergency usage (continuous)

### 3. Parameters

- $a_{p,i} \ge 0$: quantity of item type $i$ produced when pattern $p$ is used once
- $d_i \ge 0$: demand for item type $i$
- $c_p \ge 0$: unit cost of using pattern $p$ (identical for all patterns in this instance)
- $C \ge 0$: unit cost of emergency usage
- $R$: maximum number of rolls that can be processed (maximum number of patterns that may be selected)

All parameter values (demands, pattern outputs, costs and $R$) are provided in the associated data files.

### 4. Objective Function

Minimize the number of rolls used (equivalently, the total pattern cost):
$$
\min \sum_{p \in \mathcal{P}} c_p \, x_p + C\,y.
$$

Since all $c_p$ are equal and positive, this is proportional to $\sum_{p} x_p$.

### 5. Constraints

#### 5.1 Roll capacity

The total number of selected patterns cannot exceed the available rolls:
$$
\sum_{p \in \mathcal{P}} x_p \le R.
$$

#### 5.2 Demand satisfaction

For each item type, total production from all selected patterns must cover demand:
$$
\sum_{p \in \mathcal{P}} a_{p,i} \, x_p + y \;\ge\; d_i,
\quad \forall i \in \mathcal{I}.
$$

#### 5.3 Integrality

$$
x_p \in \{0,1\}, \quad \forall p \in \mathcal{P}.
$$

## Notes

- The model is a binary integer linear program: each pattern is either used once or not used at all.
- In the concrete instance `mas76`, the pattern outputs $a_{p,i}$ are stored in `patterns.csv` and item demands $d_i$ in `items.csv`. Costs and the roll limit $R$ appear as constants in the MPS representation for this instance.
- The MPS file `mas76.mps` is consistent with this formulation and can be reconstructed from the data files. 
