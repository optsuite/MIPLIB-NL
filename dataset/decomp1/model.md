# Decomp2 Problem Model

## Problem Description
The problem asks us to deploy a set of microservices onto a set of racks. Each microservice requires a specific set of configuration policies. The deployment must satisfy policy constraints and maximize a weighted objective involving the number of active racks and policy violation penalties.

## Sets
- $S$: Set of microservices, indexed by $i \in \{0, \dots, n\_services-1\}$.
- $R$: Set of racks, indexed by $j \in \{0, \dots, n\_racks-1\}$.
- $P$: Set of policies, indexed by $k \in \{0, \dots, n\_policies-1\}$.
- $Req(i)$: Set of policies required by microservice $i$.

## Parameters
- $M$: Minimum average number of enabled policies per active rack (`min_policies_per_rack`).
- $W$: Weight for active racks (equal to $M$).

## Variables
- $x_{ij} \in \{0, 1\}$: 1 if microservice $i$ is deployed on rack $j$, 0 otherwise.
- $u_{kj} \in \{0, 1\}$: 1 if policy $k$ is enabled on rack $j$, 0 otherwise.
- $y_j \in \{0, 1\}$: 1 if rack $j$ is active, 0 otherwise.
- $z_k \in \{0, 1\}$: 1 if policy $k$ incurs a penalty (deployed on 2 racks), 0 otherwise.

## Objective Function
Maximize the weighted number of active racks minus the total policy violation penalties:
$$ \text{Maximize } Z = W \sum_{j \in R} y_j - \sum_{k \in P} z_k $$

## Constraints

1.  **Service Assignment**: Each microservice must be deployed to exactly one rack.
    $$ \sum_{j \in R} x_{ij} = 1, \quad \forall i \in S $$

2.  **Policy Requirement**: If microservice $i$ is deployed on rack $j$, all its required policies must be enabled on rack $j$.
    $$ x_{ij} \le u_{kj}, \quad \forall i \in S, j \in R, k \in Req(i) $$

3.  **Policy Deployment Limits**: A policy can be enabled on at most 2 racks.
    $$ \sum_{j \in R} u_{kj} \le 2, \quad \forall k \in P $$

4.  **Policy Penalty**: If a policy is enabled on 2 racks, it incurs a penalty of 1. (If enabled on 0 or 1 rack, penalty is 0).
    $$ z_k \ge \sum_{j \in R} u_{kj} - 1, \quad \forall k \in P $$
    (Since we maximize the objective (minimize penalty), $z_k$ will be 0 if sum is $\le 1$, and 1 if sum is 2).

5.  **Rack Activation**:
    - Policies can only be enabled on active racks.
      $$ u_{kj} \le y_j, \quad \forall k \in P, j \in R $$
    - A rack is active only if it contains at least one microservice (to prevent activating empty racks just to satisfy average constraints).
      $$ y_j \le \sum_{i \in S} x_{ij}, \quad \forall j \in R $$

6.  **Average Policies Constraint**: The average number of enabled policies per active rack must be at least $M$.
    $$ \frac{\sum_{j \in R} \sum_{k \in P} u_{kj}}{\sum_{j \in R} y_j} \ge M $$
    Linearized form:
    $$ \sum_{j \in R} \sum_{k \in P} u_{kj} \ge M \sum_{j \in R} y_j $$
