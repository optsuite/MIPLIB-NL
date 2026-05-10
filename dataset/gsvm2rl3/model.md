# Robust SVM with L1 Regularization (Feature Selection) and Outlier Detection

## Problem Description

This problem aims to train a robust linear classifier for medical diagnosis based on gene expression data. The model incorporates three key components:
1.  **L1 Regularization**: To perform feature selection by enforcing sparsity on the feature weights.
2.  **Weighted Hinge Loss**: To penalize classification errors on "normal" samples, with class-balanced weights.
3.  **Outlier Detection**: To explicitly handle noisy data by allowing the model to designate certain samples as "outliers". Outliers incur a fixed penalty instead of the hinge loss, effectively removing them from the margin constraints.

## Mathematical Model

### Sets and Indices

*   $I = \{1, \dots, n_{samples}\}$: Set of patient samples.
*   $J = \{1, \dots, n_{features}\}$: Set of gene features.

### Parameters

*   $X_{ij} \in \mathbb{R}$: Gene expression value for gene $j$ in patient $i$.
*   $Y_i \in \{+1, -1\}$: Diagnosis label for patient $i$.
*   $C_{global} \in \mathbb{R}^+$: Global regularization parameter scaling the loss term.
*   $n_{pos}, n_{neg}$: Number of positive and negative samples, respectively.
*   $W_i \in \mathbb{R}^+$: Weight for sample $i$ to balance classes.
    $$W_i = \begin{cases} \frac{C_{global}}{n_{pos}} & \text{if } Y_i = +1 \\ \frac{C_{global}}{n_{neg}} & \text{if } Y_i = -1 \end{cases}$$
*   $R_{outlier} \in \mathbb{R}^+$: Cost ratio for outliers (given as 2.0).
*   $P_i \in \mathbb{R}^+$: Fixed penalty cost for treating sample $i$ as an outlier.
    $$P_i = R_{outlier} \times W_i$$
*   $M \in \mathbb{R}^+$: A large constant (Big-M) for relaxing constraints on outliers.

### Decision Variables

*   $u_j \in \mathbb{R}$: Weight coefficient for gene feature $j$.
*   $b \in \mathbb{R}$: Bias (intercept) term.
*   $\xi_i \ge 0$: Hinge loss (slack variable) for patient $i$.
*   $z_i \in \{0, 1\}$: Binary variable indicating if patient $i$ is an outlier ($z_i=1$) or normal ($z_i=0$).
*   $\alpha_j \ge 0$: Auxiliary variable representing the absolute value of $u_j$ ($|u_j|$).

### Objective Function

Minimize the sum of L1 regularization, weighted hinge loss for normal samples, and fixed penalties for outliers:

$$ \min \sum_{j \in J} \alpha_j + \sum_{i \in I} (W_i \xi_i + P_i z_i) $$

### Constraints

1.  **Robust Classification Constraints (Big-M)**:
    If sample $i$ is normal ($z_i=0$), it must satisfy the margin requirement $Y_i(u^T x_i + b) \ge 1 - \xi_i$.
    If sample $i$ is an outlier ($z_i=1$), the constraint is relaxed by $M$.
    $$ Y_i \left( \sum_{j \in J} u_j X_{ij} + b \right) \ge 1 - \xi_i - M z_i, \quad \forall i \in I $$

2.  **L1 Norm Transformation**:
    Constraint to handle absolute values in the objective.
    $$ -\alpha_j \le u_j \le \alpha_j, \quad \forall j \in J $$

3.  **Non-negativity**:
    $$ \xi_i \ge 0, \quad \forall i \in I $$

### Summary
The solver will determine the optimal weights $u, b$ and the set of outliers $\{i | z_i = 1\}$ to minimize the total structural risk.
