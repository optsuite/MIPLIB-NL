# Mathematical Model: Multi-Dimensional Project Selection Problem

## Problem Overview

The multi-dimensional project selection problem involves selecting an optimal subset of projects to minimize the maximum deviation from target requirements across multiple resource dimensions.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{P}$: Set of projects, indexed by $i \in \mathcal{P}$
- $\mathcal{D}$: Set of resource dimensions, indexed by $k \in \mathcal{D}$

### 2. Decision Variables

- $z_i \in \{0, 1\}$: Binary variable, 1 if project $i$ is selected, 0 otherwise
- $d \geq 0$: Continuous variable, maximum deviation across all dimensions
- $p_k \geq 0$: Continuous variable, positive deviation for dimension $k$
- $n_k \geq 0$: Continuous variable, negative deviation for dimension $k$

### 3. Parameters

- $c_{ik} \geq 0$: Contribution of project $i$ to dimension $k$
- $T_k > 0$: Target requirement for dimension $k$

### 4. Objective Function

$$
\text{minimize} \quad Z = d
$$

**Objective Explanation:**
Minimize the maximum absolute deviation across all dimensions.

### 5. Constraints

#### 5.1 Resource Balance Constraints

$$
\sum_{i \in \mathcal{P}} c_{ik} z_i + p_k - n_k = T_k, \quad \forall k \in \mathcal{D}
$$

**Interpretation:**

- Total contribution from selected projects plus positive deviation minus negative deviation equals target
- $p_k$ represents excess over target (actual > target)
- $n_k$ represents shortfall from target (actual < target)

#### 5.2 Maximum Deviation Constraints

$$
d \geq p_k, \quad \forall k \in \mathcal{D}
$$

$$
d \geq n_k, \quad \forall k \in \mathcal{D}
$$

**Interpretation:**

- Maximum deviation must be at least as large as any individual deviation
- Ensures $d$ bounds both positive and negative deviations

#### 5.3 Variable Type Constraints

$$
z_i \in \{0, 1\}, \quad \forall i \in \mathcal{P}
$$

$$
d \geq 0, \quad p_k \geq 0, \quad n_k \geq 0, \quad \forall k \in \mathcal{D}
$$

### 6. Complete Mathematical Model

$$
\begin{align}
\text{minimize} \quad & Z = d \\
\text{subject to} \quad & \sum_{i \in \mathcal{P}} c_{ik} z_i + p_k - n_k = T_k, & \forall k \in \mathcal{D} \\
& d \geq p_k, & \forall k \in \mathcal{D} \\
& d \geq n_k, & \forall k \in \mathcal{D} \\
& z_i \in \{0, 1\}, & \forall i \in \mathcal{P} \\
& d \geq 0, p_k \geq 0, n_k \geq 0, & \forall k \in \mathcal{D}
\end{align}
$$

### 7. Absolute Value Reformulation

The constraints effectively implement $| \sum_{i \in \mathcal{P}} c_{ik} z_i - T_k | \leq d$ for all $k \in \mathcal{D}$, where:

- When $\sum_{i} c_{ik} z_i \geq T_k$: $p_k = \sum_{i} c_{ik} z_i - T_k$, $n_k = 0$
- When $\sum_{i} c_{ik} z_i \leq T_k$: $p_k = 0$, $n_k = T_k - \sum_{i} c_{ik} z_i$

## Model Extensions

### 1. Weighted Min-Max Objective

$$
\text{minimize} \quad Z = \sum_{k \in \mathcal{D}} w_k d_k
$$

where $w_k > 0$ is the weight for dimension $k$ and $d_k$ is the deviation for that dimension.

### 2. Budget Constraint

$$
\sum_{i \in \mathcal{P}} b_i z_i \leq B
$$

where $b_i > 0$ is the cost of project $i$ and $B$ is the total budget.

### 3. Cardinality Constraint

$$
\sum_{i \in \mathcal{P}} z_i \leq K
$$

where $K$ is the maximum number of projects that can be selected.

### 4. Minimum Selection Constraint

$$
\sum_{i \in \mathcal{P}} z_i \geq L
$$

where $L$ is the minimum number of projects that must be selected.

### 5. Deviation Tolerance

$$
d \leq \tau
$$

where $\tau > 0$ is the maximum allowable deviation, converting the problem to a feasibility problem.
