# Robust SVM with Feature Selection and Outlier Detection

## Problem Description
This problem aims to train a robust linear classifier that performs simultaneous feature selection (via L1 regularization) and outlier detection (via Big-M relaxation). The model identifies "normal" samples which must satisfy the classification margin (with Hinge Loss for violations) and "outlier" samples which are exempted from the margin requirement at the cost of a fixed penalty.

## Mathematical Model

### Sets and Indices
- $i \in \{1, \dots, n\}$: Index of samples (patients).
- $j \in \{1, \dots, d\}$: Index of features (genes).
- $S_+$: Set of positive samples (label +1).
- $S_-$: Set of negative samples (label -1).

### Parameters
- $x_{ij}$: Expression value of gene $j$ for patient $i$.
- $y_i \in \{+1, -1\}$: Diagnosis label for patient $i$.
- $C_{global}$: Global penalty parameter controlling the trade-off.
- $n_+$: Number of positive samples.
- $n_-$: Number of negative samples.
- $C_i$: Sample-specific weight.
  - If $y_i = +1$, $C_i = \frac{C_{global}}{n_+}$.
  - If $y_i = -1$, $C_i = \frac{C_{global}}{n_-}$.
- $M$: Large constant (Big-M) for outlier relaxation.
- $K$: Cost ratio for outliers (Fixed penalty multiplier, set to 2.0).
- $\lambda$: Regularization coefficient for L1 norm (Implicitly 1 in the problem statement, or part of the objective trade-off).

### Decision Variables
- $u_j \in \mathbb{R}$: Weight for feature $j$.
- $b \in \mathbb{R}$: Bias term (intercept).
- $\xi_i \ge 0$: Hinge loss slack variable for sample $i$. Represents the violation of the margin.
- $z_i \in \{0, 1\}$: Binary outlier indicator for sample $i$.
  - $z_i = 1$ if sample $i$ is treated as an outlier.
  - $z_i = 0$ if sample $i$ is treated as normal.
- $v_j \ge 0$: Auxiliary variable for $|u_j|$ to linearize the L1 norm.

### Objective Function
Minimize the weighted sum of regularization, hinge loss, and outlier penalties:

$$
\min \quad \sum_{j=1}^d v_j + \sum_{i=1}^n C_i \xi_i + \sum_{i=1}^n (K \cdot C_i) z_i
$$

### Constraints

1.  **Robust Classification Margin**:
    For each sample $i$:
    $$ y_i \left( \sum_{j=1}^d u_j x_{ij} + b \right) \ge 1 - \xi_i - M z_i $$
    
    *Explanation*: If $z_i = 0$ (normal), the standard margin $1 - \xi_i$ applies. If $z_i = 1$ (outlier), the margin requirement is relaxed by $M$, effectively ignoring the constraint as long as the violation is within $M$.

2.  **L1 Norm Linearization**:
    For each feature $j$:
    $$ -v_j \le u_j \le v_j $$
    (Equivalent to $v_j \ge |u_j|$)

3.  **Non-negativity**:
    $$ \xi_i \ge 0 \quad \forall i $$
    $$ v_j \ge 0 \quad \forall j $$

4.  **Binary Constraint**:
    $$ z_i \in \{0, 1\} \quad \forall i $$

## Solution Approach
The problem is formulated as a Mixed-Integer Linear Programming (MILP) model.
1.  **Preprocessing**: Data is reshaped into a Sample $\times$ Feature matrix. Weights $C_i$ are pre-calculated based on class balance.
2.  **Solver**: Gurobi Optimizer is used to solve the MILP.
3.  **Output**: The optimal weights $u$, bias $b$, and the set of identified outliers (where $z_i=1$).
