# Mathematical Model for Secure Lab Assignment

## Problem Description
We need to assign researchers to secure labs to maximize the total number of assigned researchers, subject to capacity constraints and team cohesion rules. Specifically, if a researcher is assigned to a secure lab, all project teams they belong to must be associated with that same lab (meaning other members of those teams cannot be in a different lab).

## Sets
*   $I = \{0, 1, \dots, n-1\}$: Set of researchers.
*   $J = \{0, 1, \dots, m-1\}$: Set of project teams.
*   $L = \{0, 1, \dots, k-1\}$: Set of secure labs.
*   $R_i \subseteq J$: Set of teams researcher $i$ belongs to.

## Parameters
*   $c$: Capacity of each lab (maximum number of researchers).

## Variables
*   $x_{i,l} \in \{0, 1\}$: Binary variable, equal to 1 if researcher $i$ is assigned to lab $l$, 0 otherwise.
*   $z_{j,l} \in \{0, 1\}$: Binary variable, equal to 1 if team $j$ is assigned to lab $l$, 0 otherwise.

## Objective Function
Maximize the total number of researchers assigned to secure labs:
$$ \max \sum_{i \in I} \sum_{l \in L} x_{i,l} $$

## Constraints

1.  **Researcher Assignment:** Each researcher can be assigned to at most one lab.
    $$ \sum_{l \in L} x_{i,l} \le 1 \quad \forall i \in I $$

2.  **Lab Capacity:** The number of researchers in each lab cannot exceed its capacity.
    $$ \sum_{i \in I} x_{i,l} \le c \quad \forall l \in L $$

3.  **Team Assignment:** Each team can be associated with at most one lab.
    $$ \sum_{l \in L} z_{j,l} \le 1 \quad \forall j \in J $$

4.  **Team Cohesion:** If a researcher $i$ is assigned to lab $l$, then all teams they belong to must be associated with lab $l$. This ensures that no two members of the same team are in different labs.
    $$ x_{i,l} \le z_{j,l} \quad \forall i \in I, \forall l \in L, \forall j \in R_i $$
