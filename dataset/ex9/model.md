# Mathematical Model for Puzzle Reconstruction

## Problem Description
The problem asks to reconstruct an $n \times n$ puzzle using a given set of $n^2$ pieces. Each piece has four edges (top, right, bottom, left), each marked with a number. An edge value of 0 represents a boundary edge. Positive integers represent internal connections. The rules for a valid layout are:
1. Adjacent pieces must have matching edge values on their shared interface.
2. Boundary edges of the grid must have value 0.
3. Internal edges of the grid must have non-zero values.
4. Each piece can be rotated 0, 90, 180, or 270 degrees counter-clockwise.

## Sets and Indices
- $P = \{0, 1, \dots, n^2-1\}$: Set of puzzle pieces.
- $I = \{0, 1, \dots, n-1\}$: Set of row indices.
- $J = \{0, 1, \dots, n-1\}$: Set of column indices.
- $R = \{0, 1, 2, 3\}$: Set of rotations (0, 90, 180, 270 degrees counter-clockwise).

## Parameters
- $n$: Dimension of the puzzle grid (e.g., $n=9$).
- $E_{p, k}$: Value of the $k$-th edge of piece $p$ in its original orientation ($k=0$: Top, $k=1$: Right, $k=2$: Bottom, $k=3$: Left).
- $Edge(p, r, k)$: Value of the $k$-th edge of piece $p$ after rotation $r$.
  - $Edge(p, 0, k) = E_{p, k}$
  - $Edge(p, 1, k) = E_{p, (k+1) \pmod 4}$
  - $Edge(p, 2, k) = E_{p, (k+2) \pmod 4}$
  - $Edge(p, 3, k) = E_{p, (k+3) \pmod 4}$

## Variables
- $b_{p,i,j,r} \in \{0, 1\}$: Binary variable, equal to 1 if piece $p$ is placed at position $(i, j)$ with rotation $r$, and 0 otherwise.

## Constraints

### 1. Assignment Constraints
Each position $(i, j)$ must contain exactly one piece with one rotation:
$$ \sum_{p \in P} \sum_{r \in R} b_{p,i,j,r} = 1, \quad \forall i \in I, \forall j \in J $$

Each piece $p$ must be used exactly once in the grid:
$$ \sum_{i \in I} \sum_{j \in J} \sum_{r \in R} b_{p,i,j,r} = 1, \quad \forall p \in P $$

### 2. Boundary Constraints
Pieces placed at the boundaries must have 0 on the boundary-facing edges.
- Top boundary ($i=0$):
  $$ \sum_{p \in P} \sum_{r \in R} b_{p,0,j,r} \cdot Edge(p, r, 0) = 0, \quad \forall j \in J $$
- Bottom boundary ($i=n-1$):
  $$ \sum_{p \in P} \sum_{r \in R} b_{p,n-1,j,r} \cdot Edge(p, r, 2) = 0, \quad \forall j \in J $$
- Left boundary ($j=0$):
  $$ \sum_{p \in P} \sum_{r \in R} b_{p,i,0,r} \cdot Edge(p, r, 3) = 0, \quad \forall i \in I $$
- Right boundary ($j=n-1$):
  $$ \sum_{p \in P} \sum_{r \in R} b_{p,i,n-1,r} \cdot Edge(p, r, 1) = 0, \quad \forall i \in I $$

(Note: In implementation, these constraints are enforced by restricting the domain of valid $(p, i, j, r)$ tuples.)

### 3. Adjacency Matching Constraints
Adjacent pieces must have matching edge values.
- Horizontal matching (Right of $(i, j)$ == Left of $(i, j+1)$):
  $$ \sum_{p \in P} \sum_{r \in R} b_{p,i,j,r} \cdot Edge(p, r, 1) = \sum_{q \in P} \sum_{s \in R} b_{q,i,j+1,s} \cdot Edge(q, s, 3), \quad \forall i \in I, \forall j \in \{0, \dots, n-2\} $$

- Vertical matching (Bottom of $(i, j)$ == Top of $(i+1, j)$):
  $$ \sum_{p \in P} \sum_{r \in R} b_{p,i,j,r} \cdot Edge(p, r, 2) = \sum_{q \in P} \sum_{s \in R} b_{q,i+1,j,s} \cdot Edge(q, s, 0), \quad \forall i \in \{0, \dots, n-2\}, \forall j \in J $$

## Objective Function
Maximize the number of successfully placed pieces (which is equivalent to finding a feasible assignment for all $n^2$ positions).
$$ \text{Maximize } \sum_{p \in P} \sum_{i \in I} \sum_{j \in J} \sum_{r \in R} b_{p,i,j,r} $$
(Since we enforce equality in assignment constraints, the objective value will be constant $n^2$ for any feasible solution. The solver's goal is to satisfy the constraints.)
