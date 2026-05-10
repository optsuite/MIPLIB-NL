### Problem Description
- Given a large pool of pre-generated candidate routes (schedules), each with a specific operational cost, and a set of service requirements (constraints) that must be fulfilled.
- The goal is to select an optimal subset of these routes to minimize the total cost, such that every service requirement is covered exactly once.

### Parameter Description
- $N$: Number of candidate routes (variables)
- $M$: Number of service requirements (constraints)
- $c_j$: Cost associated with executing candidate route $j$
- $a_{ij}$: Binary parameter, where $a_{ij} = 1$ if route $j$ covers requirement $i$, and 0 otherwise

### Decision Variables
- $x_j$: 0-1 variable indicating whether candidate route $j$ is selected, where $x_j = 1$ if route $j$ is chosen, and 0 otherwise

### Objective Function

$$ 
\min \quad \sum_{j=1}^{N} c_j x_j 
$$ 

### Constraints
1. Set Partitioning Constraint (Exact Coverage): 
$$\sum_{j=1}^{N} a_{ij} x_j = 1 \quad \forall i \in \{1, \dots, M\}$$