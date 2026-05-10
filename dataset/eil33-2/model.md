### Problem Description
- This is a standard Capacitated Vehicle Routing Problem (CVRP). The background involves a logistics distribution scenario where a central depot coordinates a fleet of delivery vehicles to serve $N$ geographically scattered customers. Each customer has a specific demand for goods. The vehicles originate from the depot, deliver goods to a sequence of customers, and return to the depot.
- Each vehicle has a maximum load capacity $Q$. The total demand of customers on any single route must not exceed this capacity. The goal is to design an optimal set of routes to serve all customers such that the total travel distance (or cost) is minimized, satisfying both demand and capacity requirements.

### Parameter Description
- $N$: The number of customers requiring service (indexed $1, \dots, N$). Node $0$ represents the central depot. The set of all nodes is $V = \{0, 1, \dots, N\}$.
- $K$: The number of available vehicles in the fleet.
- $Q$: The maximum load capacity of a single vehicle.
- $d_i$: The demand of customer $i$ (where $d_0 = 0$).
- $c_{ij}$: The travel cost (or distance) from node $i$ to node $j$.

### Decision Variables
- $x_{ij}$: A binary variable; it is 1 if a vehicle travels directly from node $i$ to node $j$, otherwise 0.
- $u_i$: A continuous auxiliary variable representing the accumulated load of the vehicle upon arriving at customer $i$ (used for subtour elimination and capacity constraints).

### Objective Function
The goal is to minimize the total travel cost of the fleet.
$$ 
\min \quad \sum_{i=0}^{N} \sum_{j=0, j \neq i}^{N} c_{ij} x_{ij}
$$ 

### Constraints
1. **Service Constraint**: Each customer $i$ must be visited exactly once by exactly one vehicle.
$$ 
\sum_{j=0, j \neq i}^{N} x_{ij} = 1 \quad \forall i \in \{1, \dots, N\}
$$
$$ 
\sum_{i=0, i \neq j}^{N} x_{ij} = 1 \quad \forall j \in \{1, \dots, N\}
$$

2. **Flow Conservation**: The number of vehicles leaving the depot must equal the number of vehicles returning to the depot, and must not exceed the fleet size $K$.
$$ 
\sum_{j=1}^{N} x_{0j} = \sum_{i=1}^{N} x_{i0} \le K
$$

3. **Capacity and Subtour Elimination Constraints (MTZ formulation)**: These constraints ensure that the vehicle capacity is respected and that no isolated subtours (routes not connecting to the depot) are formed.
$$ 
u_i - u_j + Q \cdot x_{ij} \le Q - d_j \quad \forall i, j \in \{1, \dots, N\}, i \neq j
$$
$$ 
d_i \le u_i \le Q \quad \forall i \in \{1, \dots, N\}
$$

4. **Variable Constraints**: The decision variables must satisfy their domains.
$$ 
x_{ij} \in \{0, 1\} \quad \forall i, j \in V
$$
$$ 
u_i \ge 0 \quad \forall i \in \{1, \dots, N\}
$$