# Mathematical Model for SupportCase33

## Problem Description
The problem involves scheduling two robotic arms to process a set of parts within a global time window $[0, 512]$. Each part has a specific demand (processing time), available time window, and recovery time. Parts can be processed multiple times to meet the demand. There are setup times between processing different parts and a maximum gap constraint between consecutive processings of the same part. Some parts are mutually exclusive. The objective is to maximize the total profit, which is the sum of demands of fully processed parts.

## Sets and Indices
- $P$: Set of parts, indexed by $p$.
- $K_p$: Set of potential processing steps for part $p$, indexed by $k$. The number of steps depends on the part's demand and the minimum arm processing time.
- $N$: Set of all processing nodes, $N = \{(p, k) \mid p \in P, k \in K_p\}$.
- $V$: Set of all nodes in the graph, $V = N \cup \{Source, Sink\}$.
- $I$: Set of robotic arms, $I = \{0, 1\}$.
- $M$: Set of mutually exclusive pairs of parts.

## Parameters
- $D_p$: Demand (required processing time) for part $p$.
- $[TW\_Start_p, TW\_End_p]$: Available time window for part $p$.
- $Rec_p$: Recovery time required after part $p$ is the last processed part.
- $ProcTime_i$: Processing time of arm $i$ (fixed per operation).
- $Setup_{p, q}$: Setup time required to switch from part $p$ to part $q$.
- $MaxGap$: Maximum allowed time gap between consecutive processings of the same part (5 minutes).
- $GlobalStart, GlobalEnd$: Global time horizon $[0, 512]$.

## Decision Variables
- $x_{u, v, i} \in \{0, 1\}$: Binary variable, equal to 1 if arm $i$ moves from node $u$ to node $v$, 0 otherwise.
- $c_{u} \ge 0$: Continuous (or integer) variable, representing the completion time of processing at node $u \in N$.
- $y_p \in \{0, 1\}$: Binary variable, equal to 1 if part $p$ is successfully processed (total processing time $\ge D_p$), 0 otherwise.

## Objective Function
Maximize the total profit:
$$ \text{Maximize} \quad \sum_{p \in P} D_p \cdot y_p $$

## Constraints

### 1. Flow Conservation
Each arm starts at the Source and ends at the Sink.
$$ \sum_{v \in N \cup \{Sink\}} x_{Source, v, i} = 1, \quad \forall i \in I $$
$$ \sum_{u \in N \cup \{Source\}} x_{u, Sink, i} = 1, \quad \forall i \in I $$
$$ \sum_{u \in V \setminus \{v\}} x_{u, v, i} = \sum_{w \in V \setminus \{v\}} x_{v, w, i}, \quad \forall v \in N, \forall i \in I $$

### 2. Node Capacity
Each processing node can be visited at most once by any arm.
$$ \sum_{i \in I} \sum_{u \in V \setminus \{v\}} x_{u, v, i} \le 1, \quad \forall v \in N $$

### 3. Time Windows
Processing at node $u=(p, k)$ must occur within the part's time window.
$$ TW\_Start_p + \sum_{i \in I} \sum_{v \in V} x_{v, u, i} \cdot ProcTime_i \le c_u \le TW\_End_p, \quad \forall u=(p, k) \in N $$
If a node is not visited, $c_u$ is unconstrained by this (handled via Big-M or indicator constraints).

### 4. Sequence Timing
If arm $i$ moves from $u$ to $v$, the completion time at $v$ must account for completion at $u$, setup time, and processing time at $v$.
Note that setup time $Setup_{p(u), p(v)}$ applies even if $p(u) = p(v)$ (i.e., the same arm processes the same part consecutively).
$$ c_u + Setup_{p(u), p(v)} + ProcTime_i - M(1 - x_{u, v, i}) \le c_v, \quad \forall u, v \in N, \forall i \in I $$
For moves from Source:
$$ GlobalStart + Setup_{Source, v} + ProcTime_i - M(1 - x_{Source, v, i}) \le c_v $$

### 5. Gap Constraint
For a part $p$, if both step $k$ and $k+1$ are performed, the gap between them must be small.
$$ c_{(p, k+1)} - \sum_{i} \sum_{u} x_{u, (p, k+1), i} \cdot ProcTime_i \le c_{(p, k)} + MaxGap + M(2 - z_{(p, k)} - z_{(p, k+1)}) $$
where $z_u = \sum_{i} \sum_{v} x_{v, u, i}$ indicates if node $u$ is visited.
Also, strict ordering:
$$ c_{(p, k)} \le c_{(p, k+1)} - \sum_{i} \sum_{u} x_{u, (p, k+1), i} \cdot ProcTime_i $$

### 6. Demand Satisfaction
A part $p$ is valid ($y_p=1$) only if the total processing time meets the demand.
$$ \sum_{k \in K_p} \sum_{i \in I} \sum_{u \in V} x_{u, (p, k), i} \cdot ProcTime_i \ge D_p \cdot y_p $$

### 7. Mutex Constraints
Mutually exclusive parts cannot both be processed.
$$ y_p + y_q \le 1, \quad \forall (p, q) \in M $$

### 8. Recovery Time
After the last part, the arm must recover before the global end time.
$$ c_u + Rec_{p(u)} - M(1 - x_{u, Sink, i}) \le GlobalEnd, \quad \forall u \in N, \forall i \in I $$
