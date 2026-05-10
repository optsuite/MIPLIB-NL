### Problem Description
- Given a set of flight legs that must be operated and a set of feasible crew pairings, select a subset of pairings to minimize the total operational cost while ensuring that every flight leg is covered exactly once.
- This is a classic Set Partitioning Problem (SPP).

### Parameter Description
- $N1$: Number of flight legs to be covered (Rows/Constraints).
- $N2$: Number of possible crew pairings generated (Columns/Variables).
- $c_j$: Operational cost associated with pairing $j$.
- $a_{ij}$: Binary parameter (0 or 1). $a_{ij} = 1$ if pairing $j$ covers flight leg $i$, and 0 otherwise.

### Decision Variables
- $x_j$: 0-1 variable indicating whether pairing $j$ is selected. 
  - $x_j = 1$ if pairing $j$ is included in the solution.
  - $x_j = 0$ otherwise.

### Objective Function

$$ 
\minimize \quad \sum_{j=1}^{N2} c_j x_j 
$$ 

### Constraints
1. Set Partitioning Constraint (Every flight leg must be covered exactly once):
   $$\sum_{j=1}^{N2} a_{ij} x_j = 1 \quad \forall i \in \{1, \dots, N1\}$$

2. Binary Constraint:
   $$x_j \in \{0, 1\} \quad \forall j \in \{1, \dots, N2\}$$