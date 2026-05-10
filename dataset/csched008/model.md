# Mathematical Model: Cumulative Scheduling with Makespan Objective

## Problem Overview

A set of independent tasks must be scheduled on a single renewable resource with limited cumulative capacity. Each task has a fixed processing duration, a resource demand, an earliest start time, and a latest allowable start time. While a task is running it continuously consumes its resource demand; at any discrete time point, the sum of resource consumptions of all running tasks cannot exceed the resource capacity. The objective is to choose start times for all tasks so that all time-window and capacity rules are satisfied and the overall completion time of the schedule (makespan) is minimized.

## Sets and Indices

- $\mathcal{J}$: set of tasks, indexed by $j$
- $\mathcal{T}$: set of discrete time points, indexed by $t$

## Parameters

- $p_j$: processing duration of task $j$
- $r_j$: resource demand of task $j$
- $e_j$: earliest permissible start time of task $j$
- $\ell_j$: latest permissible start time of task $j$
- $C$: cumulative resource capacity of the machine
- $T_{\min}$, $T_{\max}$: lower and upper bounds of the discrete time horizon

## Decision Variables

- $x_{j,t} \in \{0,1\}$: 1 if task $j$ starts at time $t$, 0 otherwise
- $s_j \ge 0$: start time of task $j$
- $M \ge 0$: makespan of the schedule (overall completion time, in discrete ticks)

## Objective Function

Minimize makespan:
$$
\min M.
$$

## Constraints

1. **Unique start time for each task**
$$
\sum_{t \in \mathcal{T} : e_j \le t \le \ell_j} x_{j,t} = 1, \quad \forall j \in \mathcal{J}.
$$

2. **Start time definition**
$$
s_j = \sum_{t \in \mathcal{T} : e_j \le t \le \ell_j} t \, x_{j,t}, \quad \forall j \in \mathcal{J}.
$$

3. **Makespan definition**

The makespan must be at least the completion tick of every task. In this discrete-time formulation, if a task starts at time $s_j$ and has duration $p_j$, then its last occupied tick is $s_j + p_j - 1$:
$$
M \ge s_j + p_j - 1, \quad \forall j \in \mathcal{J}.
$$

4. **Cumulative capacity constraints**

At every time point, total resource usage cannot exceed capacity:
$$
\sum_{j \in \mathcal{J}} r_j \left(\sum_{\tau \in \mathcal{T} : e_j \le \tau \le \ell_j,\ \tau \le t < \tau + p_j} x_{j,\tau}\right) \le C, \quad \forall t \in \mathcal{T}.
$$

5. **Time window bounds**
$$
e_j \le s_j, \quad \forall j \in \mathcal{J},
$$
and typically
$$
s_j \le \ell_j, \quad \forall j \in \mathcal{J}.
$$

6. **Variable domains**
$$
x_{j,t} \in \{0,1\}, \quad \forall j \in \mathcal{J}, \forall t \in \mathcal{T},
$$
$$
s_j \ge 0, \ M \ge 0, \quad \forall j \in \mathcal{J}.
$$

## Notes

- The model can be implemented purely with $x_{j,t}$; the capacity constraint above directly sums the demands of tasks whose execution intervals cover time $t$.
- All problem-specific numerical values (number of tasks, capacity, durations, release times, deadlines, horizon, etc.) are provided in the associated CSV and JSON data files.
