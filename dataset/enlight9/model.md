# Mathematical Model: EnLight Grid Switching Game (9×9 Instance)

## Problem Overview

Consider a rectangular grid of lights arranged in \(R \times C\) cells. Each cell \((i,j)\) has a local switch that, when activated exactly once, toggles the light state (on/off) of a fixed plus-shaped neighborhood: the cell itself and its orthogonal neighbors (up, down, left, right) if they exist. The grid starts from a given initial on/off configuration and the goal is to find the smallest set of switches to toggle so that every cell ends in the OFF state.

The instance `enlight9` corresponds to a \(9 \times 9\) grid; the initial configuration is specified in `data/grid.csv` by the `initial_state` field.

## Sets and Indices

- \(\mathcal{I} = \{1,\dots,R\}\): row indices
- \(\mathcal{J} = \{1,\dots,C\}\): column indices
- \(\mathcal{C} = \mathcal{I} \times \mathcal{J}\): set of cells (also potential moves)
- \(\mathcal{N}(i,j) \subseteq \mathcal{C}\): plus-shaped neighborhood of cell \((i,j)\), including \((i,j)\) itself and its orthogonal neighbors

## Parameters

- \(R\): number of rows (here \(R = 9\))
- \(C\): number of columns (here \(C = 9\))
- \(\text{init}_{i,j} \in \{0,1\}\): initial light state of cell \((i,j)\) (1 = ON, 0 = OFF)

## Decision Variables

- \(x_{i,j} \in \{0,1\}\): 1 if the switch at cell \((i,j)\) is toggled exactly once, 0 otherwise

## Derived Quantities

For each cell \((p,q)\), let \(\mathcal{M}(p,q) = \{(i,j) \in \mathcal{C} : (p,q) \in \mathcal{N}(i,j)\}\) be the set of switches that affect cell \((p,q)\).

## Objective Function

Minimize the number of toggled switches:
\[
  \min \sum_{(i,j) \in \mathcal{C}} x_{i,j}.
\]

## Constraints

1. **Parity of toggles at each cell**

   Each cell \((p,q)\) must end in the OFF state. Its final state is the initial state plus the number of times it is toggled (modulo 2). For every \((p,q) \in \mathcal{C}\),
   \[
     \text{init}_{p,q} + \sum_{(i,j) \in \mathcal{M}(p,q)} x_{i,j}
     \equiv 0 \pmod{2}.
   \]

   In a mixed-integer linear formulation, this can be enforced using auxiliary integer variables \(y_{p,q} \ge 0\):
   \[
     \text{init}_{p,q} + \sum_{(i,j) \in \mathcal{M}(p,q)} x_{i,j}
     = 2 \, y_{p,q}, \quad \forall (p,q) \in \mathcal{C}.
   \]

2. **Binary switch decisions**

   \[
     x_{i,j} \in \{0,1\}, \quad \forall (i,j) \in \mathcal{C}.
   \]

## Notes on Data Mapping

- The grid dimensions \(R\) and \(C\), together with the initial state \(\text{init}_{i,j}\), are provided in `data/grid.csv`.
- The set of potential moves \((i,j)\) is given in `data/moves.csv`.
- The neighborhood relation \(\mathcal{M}(p,q)\) is encoded in `data/move_effects.csv` by listing, for each move, which cells it affects.
- The MPS file `enlight9.mps` implements exactly this structure using binary variables for moves and integer slack variables to linearize the parity constraints.

