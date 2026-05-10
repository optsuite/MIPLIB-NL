# Mathematical Model: Multi-Period Fleet Planning Problem

## Problem Overview

A multi-period optimization problem where an organization must make strategic decisions about fleet composition and capacity allocation over a planning horizon of consecutive time periods. The problem involves balancing fleet management, asset acquisition, and capacity utilization to meet demand requirements while minimizing total operational costs.

## Mathematical Formulation

### 1. Sets and Indices

- $\mathcal{T}$: Set of time periods, $|\mathcal{T}| = T$
- $t \in \mathcal{T}$: Index for time periods

### 2. Decision Variables

- $S_t$: Number of standard fleet units in period $t$
- $A_t$: Number of new assets purchased in period $t$
- $U_t$: Overtime capacity used in period $t$

### 3. Parameters

- $c_S > 0$: Cost per standard fleet unit per period
- $c_A > 0$: Cost per new asset purchased
- $c_U > 0$: Cost per unit of overtime capacity
- $h_S > 0$: Capacity provided by each standard fleet unit per period
- $h_A > 0$: Capacity consumed by each new asset for training/integration
- $u_{max} > 0$: Maximum overtime capacity allowed per standard fleet unit
- $\rho \in (0,1)$: Fleet retention rate between periods
- $S_1^{init} > 0$: Initial fleet size in period 1
- $A_{min} \geq 0$: Minimum new asset purchases per period
- $A_{max} > 0$: Maximum new asset purchases per period
- $S_{min} > 0$: Minimum standard fleet size for periods 2 to T
- $S_{max} > 0$: Maximum standard fleet size for periods 2 to T
- $D_t > 0$: Required capacity in period $t$

### 4. Objective Function

$$
\text{minimize} \quad Z = \sum_{t \in \mathcal{T}} \left( c_S \cdot S_t + c_A \cdot A_t + c_U \cdot U_t \right)
$$

### 5. Constraints

#### 5.1 Fleet Balance Constraints

**Period 1 (Initial Condition):**

$$
S_1 = S_1^{init}
$$

**Periods 2 to T (Fleet Evolution):**

$$
S_t = \rho \cdot S_{t-1} + A_{t-1}, \quad \forall t \in \{2,3,\ldots,T\}
$$

#### 5.2 Demand Requirements

$$
h_S \cdot S_t - h_A \cdot A_t + U_t \geq D_t, \quad \forall t \in \mathcal{T}
$$

#### 5.3 Overtime Capacity Constraints

$$
U_t \leq u_{max} \cdot S_t, \quad \forall t \in \mathcal{T}
$$

#### 5.4 Variable Bounds Constraints

**New Asset Purchase Bounds:**

$$
A_{min} \leq A_t \leq A_{max}, \quad \forall t \in \mathcal{T}
$$

**Standard Fleet Bounds (Periods 2 to T):**

$$
S_{min} \leq S_t \leq S_{max}, \quad \forall t \in \{2,3,\ldots,T\}
$$

#### 5.5 Variable Type Constraints

$$
S_t \in \mathbb{Z}_{+}, \quad \forall t \in \{2,3,\ldots,T\}
$$

$$
A_t \in \mathbb{Z}_{+}, \quad \forall t \in \mathcal{T}
$$

$$
S_1 \in \mathbb{R}_{+}, \quad U_t \in \mathbb{R}_{+}, \quad \forall t \in \mathcal{T}
$$

### 6. Complete Mathematical Model

$$
\begin{align}
\text{minimize} \quad & Z = \sum_{t \in \mathcal{T}} \left( c_S \cdot S_t + c_A \cdot A_t + c_U \cdot U_t \right) \\
\text{subject to} \quad & S_1 = S_1^{init} \\
& S_t = \rho \cdot S_{t-1} + A_{t-1}, & \forall t \in \{2,3,\ldots,T\} \\
& h_S \cdot S_t - h_A \cdot A_t + U_t \geq D_t, & \forall t \in \mathcal{T} \\
& U_t \leq u_{max} \cdot S_t, & \forall t \in \mathcal{T} \\
& A_{min} \leq A_t \leq A_{max}, & \forall t \in \mathcal{T} \\
& S_{min} \leq S_t \leq S_{max}, & \forall t \in \{2,3,\ldots,T\} \\
& S_t \in \mathbb{Z}_{+}, & \forall t \in \{2,3,\ldots,T\} \\
& A_t \in \mathbb{Z}_{+}, & \forall t \in \mathcal{T} \\
& S_1 \in \mathbb{R}_{+}, \quad U_t \in \mathbb{R}_{+}, & \forall t \in \mathcal{T}
\end{align}
$$
