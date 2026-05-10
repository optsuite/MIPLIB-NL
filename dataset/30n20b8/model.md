# Mathematical Model

## Problem Description

The problem asks us to schedule $n$ jobs to minimize the total cost of hiring resources (Mechanics and Technicians). Each job requires a specific type of resource and can be executed in one of three modes (1, 2, or 3 persons), with different durations. Jobs have precedence constraints and periodic start time windows.

## Sets and Indices

*   $J = \{1, \dots, n\}$: Set of jobs.
*   $M = \{1, 2, 3\}$: Set of execution modes.
*   $T = \{0, \dots, \text{time\_limit}\}$: Set of time points.
*   $R = \{\text{Mechaniker}, \text{Techniker}\}$: Set of resource types.

## Parameters

*   $D_{j,m}$: Duration of job $j$ in mode $m$.
*   $Req_{j} \in R$: Resource type required by job $j$.
*   $K_{m} = m$: Number of persons required in mode $m$ (1, 2, or 3).
*   $L_{j,m}$: Allowed start offset limit for job $j$ in mode $m$. The job can only start at time $t$ if $(t \pmod{25}) < L_{j,m}$.
*   $C_{mech}, C_{tech}$: Cost of hiring one Mechaniker and one Techniker, respectively.
*   $Pred(j)$: Set of predecessors of job $j$.
*   $TL$: Time limit for the project.

## Decision Variables

*   $x_{j,m,t} \in \{0, 1\}$: Binary variable, equal to 1 if job $j$ starts at time $t$ in mode $m$, 0 otherwise.
*   $N_{mech} \in \mathbb{Z}_{\ge 0}$: Number of Mechanikers hired.
*   $N_{tech} \in \mathbb{Z}_{\ge 0}$: Number of Technikers hired.

## Objective Function

Minimize the total hiring cost:
$$ \text{Minimize } Z = C_{mech} \cdot N_{mech} + C_{tech} \cdot N_{tech} $$

## Constraints

1.  **Job Execution:** Each job must be executed exactly once in exactly one mode.
    $$ \sum_{m \in M} \sum_{t=0}^{TL - D_{j,m}} x_{j,m,t} = 1, \quad \forall j \in J $$

2.  **Precedence Constraints:** A job cannot start before its predecessors have finished.
    $$ \sum_{m \in M} \sum_{t=0}^{TL} (t + D_{j,m}) \cdot x_{i,m,t} \le \sum_{m \in M} \sum_{t=0}^{TL} t \cdot x_{j,m,t}, \quad \forall j \in J, i \in Pred(j) $$

3.  **Resource Capacity:** At any time $t$, the total number of resources of each type used by active jobs must not exceed the hired amount.
    For each resource type $r \in R$ and time $t \in T$:
    $$ \sum_{j: Req_j = r} \sum_{m \in M} \sum_{s=\max(0, t - D_{j,m} + 1)}^{t} K_{m} \cdot x_{j,m,s} \le N_{r} $$

4.  **Periodic Time Windows:** Jobs can only start within allowed offsets in each 25-unit cycle.
    $$ x_{j,m,t} = 0, \quad \forall j \in J, m \in M, t \text{ such that } (t \pmod{25}) \ge L_{j,m} $$

5.  **Project Deadline:** All jobs must finish by the time limit. (Implicitly handled by the range of $t$ in variables and constraints, but can be explicit).
    $$ \sum_{m \in M} \sum_{t=0}^{TL} (t + D_{j,m}) \cdot x_{j,m,t} \le TL, \quad \forall j \in J $$

6.  **Variable Domains:**
    $$ x_{j,m,t} \in \{0, 1\} $$
    $$ N_{mech}, N_{tech} \ge 0, \text{Integer} $$
