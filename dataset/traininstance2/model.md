# Mathematical Model: Single-Corridor Train Rescheduling with Passenger Demand

## Problem Overview

The single-corridor train rescheduling problem considers a line of stations served by multiple trains, where each train has a planned timetable and limited passenger capacity. During operations, disturbances or tactical decisions may require delaying some trains. Delays applied at upstream stations propagate downstream, modifying arrival and departure times along the corridor.

Passengers wait at stations and wish to board passing trains. If a train is too crowded or arrives too late, some passengers may remain unserved at the platform. The goal is to decide how much to delay each train and how many passengers to board at each stop, balancing schedule adherence against passenger service quality under capacity limitations.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{T}$: set of trains, indexed by $t$.
- $\mathcal{S}$: ordered set of stations along the corridor, indexed by $s$ (from origin to destination).
- $\mathcal{E}$: set of directed track segments connecting consecutive stations, indexed by $e = (s, s+1)$.

Depending on the formulation, trains traverse all stations in $\mathcal{S}$ or a subset defined by their routes.

### 2. Parameters

Timetable and running times:

- $A^{0}_{t,s}$: planned (scheduled) arrival time of train $t$ at station $s$.
- $D^{0}_{t,s}$: planned (scheduled) departure time of train $t$ from station $s$.
- $\tau_{s,s+1}$: nominal running time from station $s$ to $s+1$ on segment $(s,s+1)$.

Delay-control parameters:

- $\Delta$: basic time unit for delay decisions (delay step).
- $D^{\max}_t$: maximum total delay (in time units) allowed for train $t$.
- $K^{\max}$: maximum number of trains that may receive a nonzero delay (optional).

Passenger demand and capacity:

- $Q^{0}_{s}$: number of passengers initially waiting at station $s$ at the beginning of the horizon.
- $Q^{\text{inc}}_{s}$: additional passengers arriving at station $s$ between successive departures of trains.
- $C_t$: passenger capacity (number of seats) of train $t$.

Evaluation parameters (penalty weights):

- $w^{\text{delay}}_t \ge 0$: penalty weight associated with schedule deviation (delay) of train $t$.
- $w^{\text{unserved}}_s \ge 0$: penalty weight associated with passengers left unserved at station $s$.

### 3. Decision Variables

Delay and timing:

- $d_t \in \mathbb{Z}_{\ge 0}$: number of delay steps applied to train $t$.
- $A_{t,s} \ge 0$: actual arrival time of train $t$ at station $s$.
- $D_{t,s} \ge 0$: actual departure time of train $t$ from station $s$.
- $z_t \in \{0,1\}$: indicator variable, 1 if train $t$ is delayed (used when limiting the number of delayed trains).

Passenger flows:

- $B_{t,s} \ge 0$: number of passengers boarding train $t$ at station $s$.
- $U_{t,s} \ge 0$: number of passengers remaining unserved at station $s$ after the departure of train $t$.

On-board loads:

- $L_{t,s} \ge 0$: number of passengers on board train $t$ immediately after departing station $s$.

### 4. Objective Function

A typical objective is to minimize a weighted combination of train delays and unserved passenger demand:

$$
\min Z
  = \sum_{t \in \mathcal{T}} w^{\text{delay}}_t \,\Delta d_t
    + \sum_{s \in \mathcal{S}} \sum_{t \in \mathcal{T}} w^{\text{unserved}}_s \, U_{t,s}.
$$

The first term penalizes deviations from the original timetable through delay decisions, while the second term penalizes passengers who remain waiting on the platform instead of boarding a train.

### 5. Constraints

#### 5.1 Timetable Consistency and Delay Propagation

Actual times must respect the scheduled times and applied delay:

$$
A_{t,s} \ge A^{0}_{t,s} + \Delta d_t,
\quad \forall t \in \mathcal{T}, \forall s \in \mathcal{S},
$$
$$
D_{t,s} \ge D^{0}_{t,s} + \Delta d_t,
\quad \forall t \in \mathcal{T}, \forall s \in \mathcal{S}.
$$

Propagation of timing along the corridor is governed by running times:

$$
A_{t,s+1} \ge D_{t,s} + \tau_{s,s+1},
\quad \forall t \in \mathcal{T}, \forall (s,s+1) \in \mathcal{E}.
$$

Departure from a station cannot occur before arrival:

$$
A_{t,s} \le D_{t,s},
\quad \forall t \in \mathcal{T}, \forall s \in \mathcal{S}.
$$

#### 5.2 Delay Bounds and Budget

Per-train delay bounds:

$$
0 \le \Delta d_t \le D^{\max}_t,
\quad \forall t \in \mathcal{T}.
$$

If a limit on the number of delayed trains is enforced, binary indicators and linking constraints can be imposed:

$$
d_t \le \bar{D}\, z_t,
\quad \forall t \in \mathcal{T},
$$
$$
\sum_{t \in \mathcal{T}} z_t \le K^{\max},
$$
where $\bar{D}$ is a sufficiently large bound on $d_t$.

#### 5.3 Passenger Balance at Stations

Passengers at each station either board a passing train or remain unserved. For each station $s$ and for trains ordered chronologically by their departure times at $s$, let $t_1, t_2, \dots$ denote the sequence of trains visiting $s$.

For the first train visiting station $s$:

$$
B_{t_1,s} + U_{t_1,s}
  = Q^{0}_{s} + Q^{\text{inc}}_{s}.
$$

For each subsequent train $t_k$ at station $s$:

$$
B_{t_k,s} + U_{t_k,s}
  = U_{t_{k-1},s} + Q^{\text{inc}}_{s}.
$$

These equations ensure that passengers are either boarded by some train or counted as unserved, while new arrivals are added between successive departures.

#### 5.4 Train Capacity and On-Board Load

The on-board load dynamics are defined by:

$$
L_{t,s} =
  \begin{cases}
    B_{t,s}, & \text{if } s \text{ is the origin of train } t, \\
    L_{t,s-1} + B_{t,s}, & \text{otherwise},
  \end{cases}
  \quad \forall t \in \mathcal{T}, \forall s \in \mathcal{S}.
$$

Capacity constraints on each train at each station:

$$
L_{t,s} \le C_t,
\quad \forall t \in \mathcal{T}, \forall s \in \mathcal{S}.
$$

These constraints ensure that the number of on-board passengers never exceeds train capacity while moving from station to station.

#### 5.5 Time Window and Horizon Constraints

All times must lie within the planning horizon:

$$
0 \le A_{t,s} \le H,
\quad 0 \le D_{t,s} \le H,
\quad \forall t \in \mathcal{T}, \forall s \in \mathcal{S},
$$
where $H$ is the length of the planning horizon.

#### 5.6 Variable Domains

Integrality and non-negativity constraints:

$$
d_t \in \mathbb{Z}_{\ge 0},
\quad z_t \in \{0,1\},
\quad \forall t \in \mathcal{T},
$$
$$
A_{t,s} \ge 0,\quad D_{t,s} \ge 0,\quad
B_{t,s} \ge 0,\quad U_{t,s} \ge 0,\quad
L_{t,s} \ge 0,
\quad \forall t \in \mathcal{T}, \forall s \in \mathcal{S}.
$$

### 6. Complete Model Sketch

Combining the objective in Section 4 with the constraints in Sections 5.1–5.6 yields a mixed-integer linear program for single-corridor train rescheduling with passenger demand. The model captures:

- propagation of train delays along a corridor,
- limits on total delay and number of delayed trains,
- passenger arrival, boarding and unserved demand at stations,
- and train capacity restrictions along the line.

Different applications can adjust the penalty weights and add further constraints (such as time windows, priority rules or robustness margins) while preserving this core structure.

