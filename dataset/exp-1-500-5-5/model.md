# Production Scheduling Model for exp-1-500-5-5

## Problem Description
The goal is to schedule the production of multiple products over a series of periods using a single machine. The machine can produce at most one type of product per period. Each product has a specific production capacity. Costs involved include production costs, setup costs, inventory holding costs, and backlog penalty costs. The objective is to minimize the total cost while ensuring that all demands are met by the end of the final period, with no remaining inventory or backlog.

## Mathematical Model

### Indices
- $i \in \{1, \dots, I\}$: Index for products (where $I = 5$).
- $t \in \{1, \dots, T\}$: Index for time periods (where $T = 50$).

### Parameters
- $D_{it}$: Demand for product $i$ in period $t$.
- $C_{it}$: Unit production cost for product $i$ in period $t$.
- $S_{it}$: Setup cost for product $i$ in period $t$.
- $H_{it}$: Unit inventory holding cost for product $i$ in period $t$.
- $P_{it}$: Unit backlog penalty cost for product $i$ in period $t$.
- $Cap_i$: Maximum production capacity for product $i$ per period.

### Decision Variables
- $x_{it} \ge 0$: Quantity of product $i$ produced in period $t$.
- $y_{it} \in \{0, 1\}$: Binary variable, 1 if product $i$ is produced in period $t$, 0 otherwise.
- $I_{it} \ge 0$: Inventory level of product $i$ at the end of period $t$.
- $B_{it} \ge 0$: Backlog level of product $i$ at the end of period $t$.

### Objective Function
Minimize the total cost, which is the sum of production, setup, holding, and backlog costs:
$$ \min \sum_{i=1}^I \sum_{t=1}^T \left( C_{it} x_{it} + S_{it} y_{it} + H_{it} I_{it} + P_{it} B_{it} \right) $$

### Constraints
1. **Inventory Balance:**
   For each product $i$ and period $t$:
   $$ I_{i,t-1} - B_{i,t-1} + x_{it} - D_{it} = I_{it} - B_{it} $$
   where $I_{i,0} = 0$ and $B_{i,0} = 0$.

2. **Production Capacity and Setup:**
   Production can only occur if the machine is set up for product $i$, and it cannot exceed the capacity:
   $$ x_{it} \le Cap_i \cdot y_{it} \quad \forall i, t $$

3. **Single Machine Constraint:**
   The machine can produce at most one type of product in any given period:
   $$ \sum_{i=1}^I y_{it} \le 1 \quad \forall t $$

4. **Terminal Condition:**
   No inventory or backlog should remain at the end of the final period $T$:
   $$ I_{iT} = 0, \quad B_{iT} = 0 \quad \forall i $$

## Solution Approach
The problem is formulated as a Mixed-Integer Linear Programming (MILP) model. The binary variables $y_{it}$ handle the setup decisions and the single-machine constraint. The continuous variables $x_{it}$, $I_{it}$, and $B_{it}$ manage the production quantities and the flow of products over time. The model can be solved using a standard MILP solver like Gurobi.
