# Mathematical Model: Technical Support Case Selection Problem

## Problem Overview

A large-scale binary integer programming problem for optimizing the deployment of technical support cases to satisfy customer requirements while minimizing total deployment cost.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{I}$: Set of technical support cases, $|\mathcal{I}| = n$
- $\mathcal{J}$: Set of customer requirements, $|\mathcal{J}| = m$
- $\mathcal{I}_c \subseteq \mathcal{I}$: Set of cost cases with positive deployment costs, $|\mathcal{I}_c| = p$
- $\mathcal{I}_z \subseteq \mathcal{I}$: Set of zero-cost cases, $|\mathcal{I}_z| = q$ where $p + q = n$

where:
- $i \in \mathcal{I}$: Index for technical support cases
- $j \in \mathcal{J}$: Index for customer requirements

### 2. Decision Variables

- $x_i \in \{0, 1\}$: Binary variable, 1 if support case $i$ is deployed, 0 otherwise

### 3. Parameters

- $c_i \geq 0$: Deployment cost of support case $i$
- $a_{ij} \geq 0$: Coverage value provided by case $i$ for requirement $j$
- $b_j$: Minimum coverage threshold required for requirement $j$
- $\mathcal{I}^* \subset \mathcal{I}$: Special set of cases involved in general constraints
- $\mathcal{I}^+ \subset \mathcal{I}$: Cost subset cases (first 7 cases with power-of-2 costs)
- $\mathcal{I}^- \subset \mathcal{I}$: Flexibility cases (remaining cases except special ones)

### 4. Objective Function

$$\text{minimize} \quad Z = \sum_{i \in \mathcal{I}} c_i \cdot x_i$$

### 5. Constraints

#### 5.1 Coverage Requirements

For each customer requirement $j \in \mathcal{J}$:

$$\sum_{i \in \mathcal{I}} a_{ij} \cdot x_i \geq b_j$$

#### 5.2 General Constraints (Indicator Constraints)

**Constraint 5.2.1:** If the special zero-cost case $i^*$ is not selected, then at least one cost case must be selected:

$$x_{i^*} = 0 \rightarrow \sum_{i \in \mathcal{I}^+} x_i \geq 1$$

**Constraint 5.2.2:** If the special zero-cost case $i^*$ is selected, then all flexibility cases must be zero:

$$x_{i^*} = 1 \rightarrow \sum_{i \in \mathcal{I}^-} x_i = 0$$

### 6. Complete Mathematical Model

$$
\begin{align}
\text{minimize} \quad & Z = \sum_{i \in \mathcal{I}} c_i \cdot x_i \\
\text{subject to} \quad & \sum_{i \in \mathcal{I}} a_{ij} \cdot x_i \geq b_j \quad \forall j \in \mathcal{J} \\
& x_{i^*} = 0 \rightarrow \sum_{i \in \mathcal{I}^+} x_i \geq 1 \\
& x_{i^*} = 1 \rightarrow \sum_{i \in \mathcal{I}^-} x_i = 0 \\
& x_i \in \{0, 1\} \quad \forall i \in \mathcal{I}
\end{align}
$$

## Problem Characteristics

- **Problem Type**: Binary Integer Programming (BIP) with indicator constraints
- **Problem Class**: Set covering problem with hierarchical cost structure
- **Complexity**: NP-Hard (set cover is NP-complete)
- **Search Space**: $2^{24} \approx 16.8$ million possible solutions
- **Constraint Density**: Dense coverage matrix with approximately 52.7% non-zero coefficients