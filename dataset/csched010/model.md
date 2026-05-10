# Mathematical Model: Cumulative Scheduling with Start-Time Targets

## Problem Overview

A set of independent tasks must be scheduled on a single renewable resource with limited cumulative capacity. Each task has a fixed processing duration, a resource demand, an earliest start time, a latest allowable start time, and a reference start-time target. While a task is running it continuously consumes its resource demand; at any discrete time point, the sum of resource consumptions of all running tasks cannot exceed the resource capacity. The objective is to choose a start time for each task so that all time-window and capacity rules are satisfied and the total start-time delay (sum of positive deviations of chosen start times beyond their targets) is minimized.

## Sets and Indices

- $\mathcal{J}$: set of tasks, indexed by $j$
- $\mathcal{T}$: set of discrete time points, indexed by $t$

## Parameters

- $p_j$: processing duration of task $j$
- $r_j$: resource demand of task $j$
- $e_j$: earliest permissible start time of task $j$
- $\ell_j$: latest permissible start time of task $j$
- $d_j$: reference start-time target of task $j$ (used to compute start-time delay)
- $C$: cumulative resource capacity of the machine
- $T_{\min}$, $T_{\max}$: lower and upper bounds of the discrete time horizon

## Decision Variables

- $x_{j,t} \in \{0,1\}$: 1 if task $j$ starts at time $t$, 0 otherwise
- $s_j \ge 0$: start time of task $j$
- $\text{delay}_j \ge 0$: start-time delay of task $j$ beyond its target start time

## Objective Function

Minimize total start-time delay:
$$
\min \sum_{j \in \mathcal{J}} \text{delay}_j.
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

3. **Start-time delay definition**
$$
\text{delay}_j \ge s_j - d_j, \quad \forall j \in \mathcal{J},
$$
and
$$
\text{delay}_j \ge 0, \quad \forall j \in \mathcal{J}.
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
s_j \ge 0, \ \text{delay}_j \ge 0, \quad \forall j \in \mathcal{J}.
$$

## Notes

- The model can be implemented purely with $x_{j,t}$; the capacity constraint above directly sums the demands of tasks whose execution intervals cover time $t$.
- All problem-specific numerical values (number of tasks, capacity, durations, release times, deadlines, horizon, etc.) are provided in the associated CSV and JSON data files.
