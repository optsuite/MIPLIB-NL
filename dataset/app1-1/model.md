# Mathematical Model

## Problem Description

The goal is to determine the weights for a set of Key Performance Indicators (KPIs) such that the weighted score of the "preferred supplier" is minimized in as many regions as possible. The weighted score is calculated as the sum of the products of the KPI weights and the supplier's scores on those KPIs. A lower weighted score is better.

## Sets and Indices

*   $I = \{1, \dots, N_{regions}\}$: Set of regions (departments).
*   $J = \{1, \dots, N_{suppliers}\}$: Set of suppliers per region.
*   $K = \{1, \dots, N_{kpis}\}$: Set of KPIs.

## Parameters

*   $S_{ijk}$: Score of supplier $j$ in region $i$ on KPI $k$.
*   $P_i$: The ID of the preferred supplier for region $i$.
*   $M$: A sufficiently large positive constant (Big-M).

## Decision Variables

*   $w_k$: Continuous variable representing the weight of KPI $k$. $w_k \in [0, 1]$.
*   $y_i$: Binary variable. $y_i = 1$ if the preferred supplier $P_i$ has the minimum weighted score in region $i$ (i.e., "wins"), and $y_i = 0$ otherwise.

## Objective Function

Maximize the total number of regions where the preferred supplier wins:

$$ \text{Maximize } Z = \sum_{i \in I} y_i $$

## Constraints

1.  **Weight Normalization:**
    The sum of all KPI weights must equal 1.
    $$ \sum_{k \in K} w_k = 1 $$

2.  **Winning Condition:**
    For each region $i$, if $y_i = 1$, then the weighted score of the preferred supplier $P_i$ must be less than or equal to the weighted score of any other supplier $j$ in that region.
    
    Let the weighted score of supplier $j$ in region $i$ be $Score_{ij} = \sum_{k \in K} w_k S_{ijk}$.
    
    The condition is:
    $$ Score_{i, P_i} \le Score_{ij} \quad \forall j \in J, j \ne P_i $$
    
    Using the Big-M formulation to relax this constraint when $y_i = 0$:
    $$ Score_{ij} - Score_{i, P_i} \ge -M (1 - y_i) \quad \forall i \in I, \forall j \in J, j \ne P_i $$
    
    Substituting the definition of $Score$:
    $$ \sum_{k \in K} w_k (S_{ijk} - S_{i, P_i, k}) \ge -M (1 - y_i) \quad \forall i \in I, \forall j \in J, j \ne P_i $$

3.  **Variable Bounds:**
    $$ w_k \ge 0 \quad \forall k \in K $$
    $$ y_i \in \{0, 1\} \quad \forall i \in I $$
