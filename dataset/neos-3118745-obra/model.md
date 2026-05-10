### Problem Description
- Given a large construction project decomposed into $N_1$ sub-tasks and $N_2$ available subcontractors, select exactly one subcontractor for each task to minimize the "unrealized profit" (opportunity cost) while respecting global capacities and local zone limits.
- The project is divided into $M$ zones. Each zone contains a contiguous block of tasks.
- Minimizing unrealized profit is mathematically equivalent to maximizing total profit.

### Parameter Description
- $N_1$: Number of distinct sub-tasks
- $N_2$: Number of available subcontractors
- $M$: Number of zones (phases)
- $Y$: Total potential value of the project (Target Revenue constant)
- $P_{ij}$: Profit generated if task $i$ is assigned to subcontractor $j$
- $G_{ij}$: Global resource consumption if task $i$ is assigned to subcontractor $j$
- $L_{ij}$: Local resource consumption if task $i$ is assigned to subcontractor $j$
- $C_j$: Maximum global resource capacity for subcontractor $j$
- $Lim_k$: Maximum local resource limit for zone $k$
- $Z_k$: The set of tasks belonging to zone $k$

### Decision Variables
- $x_{ij}$: 0-1 variable indicating whether task $i$ is assigned to subcontractor $j$. $x_{ij} = 1$ if assigned, 0 otherwise.
- $U$: Continuous variable representing the unrealized profit (C0001).

### Objective Function

$$ 
\text{minimize} \quad U 
$$

Where $U$ is defined by the relationship:
$$ 
U = Y - \sum_{i=1}^{N_1} \sum_{j=1}^{N_2} P_{ij} x_{ij} 
$$

### Constraints

1. **Assignment Constraint**: Each task must be assigned to exactly one subcontractor.
$$\sum_{j=1}^{N_2} x_{ij} = 1 \quad \forall i \in \{1, \dots, N_1\}$$

2. **Global Capacity Constraint**: The total global resources used by each subcontractor must not exceed their capacity.
$$\sum_{i=1}^{N_1} G_{ij} x_{ij} \le C_j \quad \forall j \in \{1, \dots, N_2\}$$

3. **Local Zone Resource Constraint**: The total local resources used by tasks within a specific zone must not exceed that zone's limit.
$$\sum_{i \in Z_k} \sum_{j=1}^{N_2} L_{ij} x_{ij} \le Lim_k \quad \forall k \in \{1, \dots, M\}$$

4. **Binary Constraint**:
$$x_{ij} \in \{0, 1\}$$