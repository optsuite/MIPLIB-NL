# Wachplan Problem Model

## Problem Description
The problem asks us to schedule a cyclic watch roster for a crew on a sailing vessel. We need to assign crew members to time slots while satisfying safety, rest, and social constraints, maximizing the equal number of shifts each crew member serves.

## Sets
*   $I = \{1, \dots, N\}$: Set of crew members, where $N$ is `n_crew`.
*   $T = \{1, \dots, S\}$: Set of time slots, where $S$ is `n_slots`.

## Parameters
*   $L$: Minimum number of crew members on duty per slot (`min_on_duty`).
*   $U$: Maximum number of crew members on duty per slot (`max_on_duty`).
*   $W$: Size of the rolling window (`window_size`).
*   $K$: Maximum shifts allowed in any rolling window (`max_shifts_in_window`).
*   $P_t$: Set of crew members pre-assigned to slot $t$.
    *   $P_1 = \{1, 2, 3\}$
    *   $P_2 = \{4, 5\}$

## Decision Variables
*   $x_{i,t} \in \{0, 1\}$: Binary variable, equal to 1 if crew member $i$ is on duty in slot $t$, 0 otherwise.
*   $z_{i,j,t} \in \{0, 1\}$: Auxiliary binary variable for linearization, equal to 1 if both crew members $i$ and $j$ are on duty in slot $t$. (Defined for $i < j$).
*   $Z \in \mathbb{Z}_{\ge 0}$: The total number of shifts served by each crew member.

## Objective Function
Maximize the number of shifts per crew member:
$$ \text{Maximize } Z $$

## Constraints

1.  **Crew Size per Slot:**
    For each slot $t \in T$, the number of crew on duty must be between $L$ and $U$.
    $$ L \le \sum_{i \in I} x_{i,t} \le U, \quad \forall t \in T $$

2.  **No Consecutive Shifts:**
    No crew member can work two consecutive slots. Since the schedule is cyclic, slot $S$ is followed by slot 1.
    $$ x_{i,t} + x_{i, (t \pmod S) + 1} \le 1, \quad \forall i \in I, \forall t \in T $$

3.  **Rolling Window Constraint:**
    In any sequence of $W$ consecutive slots, a crew member can work at most $K$ times.
    $$ \sum_{k=0}^{W-1} x_{i, ((t+k-1) \pmod S) + 1} \le K, \quad \forall i \in I, \forall t \in T $$

4.  **Fairness (Equal Shifts):**
    Every crew member must work exactly $Z$ shifts.
    $$ \sum_{t \in T} x_{i,t} = Z, \quad \forall i \in I $$

5.  **Social Goal (Pairwise Integration):**
    Every pair of crew members must serve together on at least one watch.
    $$ \sum_{t \in T} z_{i,j,t} \ge 1, \quad \forall i, j \in I, i < j $$

    To enforce $z_{i,j,t} = 1 \iff x_{i,t}=1 \land x_{j,t}=1$, we add the following linearization constraints:
    $$ z_{i,j,t} \le x_{i,t} $$
    $$ z_{i,j,t} \le x_{j,t} $$
    $$ z_{i,j,t} \ge x_{i,t} + x_{j,t} - 1 $$

6.  **Pre-assignments:**
    Fixed assignments based on the problem statement.
    $$ x_{i,t} = 1, \quad \forall t \in \{1, 2\}, \forall i \in P_t $$
