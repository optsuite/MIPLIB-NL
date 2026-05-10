### Problem Description
- Given a set of $N$ locations (including a depot and customers) and a cost matrix representing travel costs (or distances) between any pair of locations, find the optimal route that starts from the depot, visits every other location exactly once, and returns to the depot, such that the total travel cost is minimized. The problem includes subtour elimination constraints to ensure a single continuous loop.

### Parameter Description
- $N$: Total number of locations (nodes).
- $c_{ij}$: Travel cost (or distance) from location $i$ to location $j$.

### Decision Variables
- $x_{ij}$: Binary variable, where $x_{ij} = 1$ if the vehicle travels directly from location $i$ to location $j$, and 0 otherwise.
- $u_i$: Continuous auxiliary variable representing the visiting sequence order of location $i$ (used for subtour elimination), defined for $i \in \{2, \dots, N\}$.

### Objective Function

$$ 
\text{Minimize} \quad \sum_{i=1}^{N} \sum_{j=1}^{N} c_{ij} x_{ij} 
$$ 

### Constraints
1. Leave Constraints (Each location must be left exactly once): 
$$\sum_{j=1, j \neq i}^{N} x_{ij} = 1, \quad \forall i \in \{1, \dots, N\}$$

2. Enter Constraints (Each location must be entered exactly once): 
$$\sum_{i=1, i \neq j}^{N} x_{ij} = 1, \quad \forall j \in \{1, \dots, N\}$$

3. Subtour Elimination Constraints (MTZ formulation): 
$$u_i - u_j + N \cdot x_{ij} \le N - 1, \quad \forall i, j \in \{2, \dots, N\}, i \neq j$$

4. Variable Bounds: 
$$x_{ij} \in \{0, 1\}$$
$$1 \le u_i \le N - 1, \quad \forall i \in \{2, \dots, N\}$$