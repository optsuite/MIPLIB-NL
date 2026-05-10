### Problem Description
- This is a set cover problem with cardinality constraints. The background involves a smart city security scenario where $N$ automated drone hangars are deployed to cover $M$ key surveillance points. Each hangar can cover a specific subset of these surveillance points. The goal is to select a subset of hangars to enable (binary decision: 0 or 1) such that all surveillance points are covered at least once.
- Additionally, the system has total capacity constraints: the total number of enabled hangars must be at least $K1$ and at most $K2$. The objective is to minimize the total number of enabled hangars while satisfying both the coverage and capacity requirements.

### Parameter Description
- $M$: The number of surveillance points (Locations) to be covered.
- $N$: The number of candidate drone hangars available for selection.
- $K1$: The minimum required total capacity (minimum number of enabled hangars).
- $K2$: The maximum allowed total capacity (maximum number of enabled hangars).
- $a_{ij}$: A binary parameter; it is 1 if hangar $j$ can cover surveillance point $i$, otherwise 0.

### Decision Variables
- $x_j$: A binary variable; it is 1 if hangar $j$ is enabled, otherwise 0.

### Objective Function
The goal is to minimize the total investment (number of enabled hangars).
$$ 
\min \quad \sum_{j=1}^{N} x_j
$$ 

### Constraints
1. **Coverage Constraint**: Each surveillance point $i$ must be covered by at least one enabled hangar.
$$ 
\sum_{j=1}^{N} a_{ij} x_j \ge 1 \quad \forall i \in \{1, \dots, M\}
$$

2. **Capacity Constraint**: The total number of enabled hangars must be within the range $[K1, K2]$.
$$ 
K1 \le \sum_{j=1}^{N} x_j \le K2
$$

3. **Binary Constraint**: The decision variables must be binary.
$$ 
x_j \in \{0, 1\} \quad \forall j \in \{1, \dots, N\}
$$