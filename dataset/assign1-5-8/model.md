# Mathematical Model: Generalized Assignment Problem

## Problem Definition

The Generalized Assignment Problem (GAP) is a fundamental combinatorial optimization problem that involves assigning a set of tasks to a group of agents with limited capacities. Each task must be assigned to exactly one agent, and each agent has a maximum capacity of resources they can handle. The objective is to minimize the total cost of assignments while respecting all capacity constraints.

## Mathematical Formulation

### Sets and Indices

- **$I$**: Set of tasks, indexed by $i = 1, 2, \ldots, n$
- **$J$**: Set of agents, indexed by $j = 1, 2, \ldots, m$

### Parameters

- **$c_{ij}$**: Cost of assigning task $i$ to agent $j$
- **$r_{ij}$**: Resource requirement of task $i$ when assigned to agent $j$
- **$C_j$**: Maximum resource capacity of agent $j$

### Decision Variables

- **$x_{ij}$**: Binary variable
  - $x_{ij} = 1$ if task $i$ is assigned to agent $j$
  - $x_{ij} = 0$ otherwise

### Objective Function

**Minimize total assignment cost:**

$$
\min \sum_{i \in I} \sum_{j \in J} c_{ij} \cdot x_{ij}
$$

### Constraints

**1. Assignment Constraints (Task Assignment)**

Each task must be assigned to exactly one agent:

$$
\sum_{j \in J} x_{ij} = 1, \quad \forall i \in I
$$

**2. Capacity Constraints (Agent Capacity)**

The total resource requirements assigned to each agent cannot exceed its capacity:

$$
\sum_{i \in I} r_{ij} \cdot x_{ij} \leq C_j, \quad \forall j \in J
$$

**3. Binary Constraints**

$$
x_{ij} \in \{0, 1\}, \quad \forall i \in I, \forall j \in J
$$

## Problem Characteristics

### Computational Complexity

- **Complexity Class**: NP-hard
- **Solution Method**: Mixed-Integer Linear Programming (MILP)
- **Typical Solvers**: Gurobi, CPLEX, SCIP

### Problem Structure

- **Variables**: $|I| \times |J|$ binary variables
- **Constraints**: $|I|$ assignment constraints + $|J|$ capacity constraints
- **Sparsity**: Typically sparse constraint matrix
