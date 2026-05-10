# Index Tracking Portfolio Optimization (Mean Absolute Deviation)

## Problem Description
This problem addresses the construction of an investment portfolio designed to track a target market index. The objective is to minimize the Mean Absolute Deviation (MAD) between the portfolio's aggregated sensitivity to various economic indicators and the target index's sensitivity values. The selection process is subject to strict diversification rules (industry coverage and sector limits) and quality control thresholds (fundamental scores).

## Sets and Indices
* $i \in I = \{1, \dots, N_1\}$: Set of candidate stocks.
* $j \in J = \{1, \dots, N_2\}$: Set of distinct industries.
* $k \in K = \{1, \dots, N_3\}$: Set of broad sectors.
* $m \in M = \{1, \dots, N_4\}$: Set of quality metrics (e.g., liquidity, ESG).
* $l \in L = \{1, \dots, N_5\}$: Set of economic indicators for tracking.

## Parameters
The problem parameters are derived from the following data tables:

* **Stock Classifications (from Table C1):**
    * $Ind_i$: The industry ID that stock $i$ belongs to.
    * $Sec_i$: The sector ID that stock $i$ belongs to.

* **Sector Limits (from Table C2):**
    * $Limit_k$: The maximum number of stocks allowed to be selected from sector $k$.

* **Quality Scores (from Table C3):**
    * $Q_{m,i}$: The weighted score of stock $i$ on quality metric $m$.

* **Economic Sensitivities (from Table C4):**
    * $S_{l,i}$: The sensitivity coefficient of stock $i$ to economic indicator $l$.

* **Target Index Values (from Table C5):**
    * $T_l$: The target aggregated sensitivity value for economic indicator $l$.

## Decision Variables
* $x_i \in \{0, 1\}$: Binary variable. Equal to 1 if stock $i$ is selected in the portfolio, 0 otherwise.
* $y^+_l \ge 0$: Continuous variable. Represents the positive deviation of the portfolio from the target for indicator $l$.
* $y^-_l \ge 0$: Continuous variable. Represents the negative deviation of the portfolio from the target for indicator $l$.

## Mathematical Formulation

### Objective Function
Minimize the Total Absolute Deviation (equivalent to MAD) across all economic indicators:

$$
\min \quad \sum_{l \in L} (y^+_l + y^-_l)
$$

### Constraints

1.  **Industry Coverage Constraint:**
    Exactly one stock must be selected from each industry to ensure diversification.
    $$
    \sum_{i \in I, Ind_i = j} x_i = 1, \quad \forall j \in J
    $$

2.  **Sector Concentration Constraint:**
    The number of stocks selected from each broad sector must not exceed the specified limit.
    $$
    \sum_{i \in I, Sec_i = k} x_i \le Limit_k, \quad \forall k \in K
    $$

3.  **Quality Threshold Constraint:**
    The aggregated quality score of the portfolio for each metric must be non-negative.
    $$
    \sum_{i \in I} Q_{m,i} \cdot x_i \ge 0, \quad \forall m \in M
    $$

4.  **Deviation Calculation Constraints:**
    These constraints linearize the absolute difference $| \sum S_{l,i} x_i - T_l |$.
    $$
    \sum_{i \in I} S_{l,i} \cdot x_i - (y^+_l - y^-_l) = T_l, \quad \forall l \in L
    $$
    *(This is equivalent to: $\sum_{i \in I} S_{l,i} \cdot x_i + y^-_l - y^+_l = T_l$)*

5.  **Variable Domains:**
    $$
    x_i \in \{0, 1\}, \quad \forall i \in I
    $$
    $$
    y^+_l, y^-_l \ge 0, \quad \forall l \in L
    $$