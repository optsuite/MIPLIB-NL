# Mathematical Model: Market Share Optimization Problem

## Problem Overview

The market share optimization problem is a product selection problem where the objective is to minimize the total shortfall from target market shares across multiple markets by selecting an optimal subset of products.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{P}$: Set of products, $|\mathcal{P}| = n$
- $\mathcal{M}$: Set of markets, $|\mathcal{M}| = m$

where:

- $j \in \mathcal{P}$: Index for products
- $i \in \mathcal{M}$: Index for markets

### 2. Decision Variables

- $x_j \in \{0, 1\}$: Binary variable, 1 if product $j$ is selected, 0 otherwise
- $s_i \geq 0$: Continuous variable, shortfall in market $i$

### 3. Parameters

- $a_{ij} \geq 0$: Contribution value of product $j$ to market $i$
- $T_i > 0$: Target value for market $i$

### 4. Objective Function

$$
\text{minimize} \quad Z = \sum_{i \in \mathcal{M}} s_i
$$

**Objective Explanation:**
Minimize the total shortfall across all markets.

### 5. Constraints

#### 5.1 Market Target Constraints

$$
s_i + \sum_{j \in \mathcal{P}} a_{ij} x_j = T_i, \quad \forall i \in \mathcal{M}
$$

**Interpretation:**

- $s_i$ represents the shortfall from target in market $i$
- $\sum_{j \in \mathcal{P}} a_{ij} x_j$ is the total contribution from selected products to market $i$
- The sum of achieved contribution and shortfall equals the target

#### 5.2 Variable Type Constraints

$$
x_j \in \{0, 1\}, \quad \forall j \in \mathcal{P}
$$

$$
s_i \geq 0, \quad \forall i \in \mathcal{M}
$$

### 6. Complete Mathematical Model

$$
\begin{align}
\text{minimize} \quad & Z = \sum_{i \in \mathcal{M}} s_i \\
\text{subject to} \quad & s_i + \sum_{j \in \mathcal{P}} a_{ij} x_j = T_i, & \forall i \in \mathcal{M} \\
& x_j \in \{0, 1\}, & \forall j \in \mathcal{P} \\
& s_i \geq 0, & \forall i \in \mathcal{M}
\end{align}
$$
