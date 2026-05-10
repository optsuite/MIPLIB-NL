# Investment Portfolio Optimization Model

## Problem Description
We aim to maximize the total expected return from $n$ types of investment projects. Each project has a specific expected return per unit. The investments are subject to $m$ risk factors, each with a maximum allowable threshold. The impact of each project on each risk factor is given by a set of coefficients.

## Decision Variables
- $x_i$: The number of units to invest in project $i$, where $i \in \{1, 2, \dots, n\}$.
- $x_i \in \mathbb{Z}_{\ge 0}$ (Integer units).

## Objective Function
Maximize the total expected return:
$$\max Z = \sum_{i=1}^{n} r_i x_i$$
where $r_i$ is the expected return per unit of project $i$.

## Constraints
For each risk factor $j \in \{1, 2, \dots, m\}$, the total weighted impact must not exceed its threshold $T_j$:
$$\sum_{i=1}^{n} c_{ij} x_i \le T_j, \quad \forall j \in \{1, 2, \dots, m\}$$
where $c_{ij}$ is the impact coefficient of project $i$ on risk factor $j$.

## Solution Approach
The problem is formulated as an Integer Linear Programming (ILP) problem. We use the Gurobi optimizer to find the optimal integer values for $x_i$ that maximize the objective function while satisfying all risk factor constraints.
