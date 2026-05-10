# Mathematical Model: Capacitated Project-Facility Assignment Problem

## Problem Overview

The capacitated project-facility assignment problem involves selecting projects and allocating them to facilities to minimize net cost while respecting capacity constraints.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{P}$: Set of projects, indexed by $i \in \mathcal{P}$
- $\mathcal{F}$: Set of facilities, indexed by $j \in \mathcal{F}$

### 2. Decision Variables

- $z_i \in \{0, 1\}$: Binary variable, 1 if project $i$ is selected, 0 otherwise
- $l_{ij} \in [0, 1]$: Continuous variable, fraction of project $i$ assigned to facility $j$
- $f_i \geq 0$: Continuous auxiliary variable for project $i$

### 3. Parameters

- $c_i \geq 0$: Fixed cost of selecting project $i \in \mathcal{P}$
- $d_i > 0$: Demand requirement for project $i \in \mathcal{P}$
- $u_j > 0$: Capacity of facility $j \in \mathcal{F}$
- $p_{ij} \geq 0$: Profit from assigning project $i$ to facility $j$
- $a_{ij} \geq 0$: Demand coefficient for project $i$ at facility $j$
- $u_i > 0$: Upper bound for auxiliary variable $f_i$

### 4. Objective Function

$$\text{minimize} \quad Z = \sum_{i \in \mathcal{P}} c_i z_i - \sum_{i \in \mathcal{P}} \sum_{j \in \mathcal{F}} p_{ij} l_{ij}$$

**Objective Explanation:**
Minimize total fixed costs minus total assignment profits (net cost).

### 5. Constraints

#### 5.1 Facility Capacity Constraints

$$\sum_{i \in \mathcal{P}} a_{ij} l_{ij} \leq u_j, \quad \forall j \in \mathcal{F}$$

**Interpretation:**
- Total demand allocated to each facility cannot exceed its capacity
- Demand contribution weighted by assignment fractions

#### 5.2 Project Demand Constraints

$$d_i z_i + \sum_{j \in \mathcal{F}} a_{ij} l_{ij} + f_i = d_i, \quad \forall i \in \mathcal{P}$$

**Interpretation:**
- Links project selection with assignments and auxiliary variables
- When $z_i = 1$: $\sum_{j} a_{ij} l_{ij} + f_i = 0$
- When $z_i = 0$: $\sum_{j} a_{ij} l_{ij} + f_i = d_i$

#### 5.3 Variable Bounds

$$l_{ij} \geq 0, \quad \forall i \in \mathcal{P}, \forall j \in \mathcal{F}$$
$$l_{ij} \leq 1, \quad \forall i \in \mathcal{P}, \forall j \in \mathcal{F}$$
$$f_i \geq 0, \quad \forall i \in \mathcal{P}$$
$$f_i \leq u_i, \quad \forall i \in \mathcal{P}$$
$$z_i \in \{0, 1\}, \quad \forall i \in \mathcal{P}$$

### 6. Complete Mathematical Model

$$
\begin{align}
\text{minimize} \quad & Z = \sum_{i \in \mathcal{P}} c_i z_i - \sum_{i \in \mathcal{P}} \sum_{j \in \mathcal{F}} p_{ij} l_{ij} \\
\text{subject to} \quad & \sum_{i \in \mathcal{P}} a_{ij} l_{ij} \leq u_j, & \forall j \in \mathcal{F} \\
& d_i z_i + \sum_{j \in \mathcal{F}} a_{ij} l_{ij} + f_i = d_i, & \forall i \in \mathcal{P} \\
& 0 \leq l_{ij} \leq 1, & \forall i \in \mathcal{P}, \forall j \in \mathcal{F} \\
& 0 \leq f_i \leq u_i, & \forall i \in \mathcal{P} \\
& z_i \in \{0, 1\}, & \forall i \in \mathcal{P}
\end{align}
$$



## Model Extensions

### 1. Budget Constraint
$$\sum_{i \in \mathcal{P}} c_i z_i \leq B$$
where $B$ is the total available budget for project selection.

### 2. Minimum Assignment Requirement
$$\sum_{j \in \mathcal{F}} l_{ij} \geq \alpha z_i, \quad \forall i \in \mathcal{P}$$
where $\alpha \in [0, |\mathcal{F}|]$ is the minimum number of facilities required per selected project.

### 3. Maximum Projects Constraint
$$\sum_{i \in \mathcal{P}} z_i \leq K$$
where $K$ is the maximum number of projects that can be selected.

### 4. Profit Minimization Variant
$$\text{maximize} \quad Z = \sum_{i \in \mathcal{P}} \sum_{j \in \mathcal{F}} p_{ij} l_{ij} - \sum_{i \in \mathcal{P}} c_i z_i$$
Convert to a maximization problem focusing on net profit.