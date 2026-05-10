# Composite Shielding System Design Model

## Problem Overview
The goal is to design a composite shielding system for a space station by selecting the number of layers for various shielding materials. Each material has a specific unit cost and provides different levels of attenuation against various types of cosmic radiation. The system must ensure that the total attenuation for each radiation type meets or exceeds a predefined minimum threshold while minimizing the total cost of the materials used.

## Mathematical Model

### Sets and Indices
- $I = \{1, 2, \dots, n\}$: Set of available shielding materials, where $n$ is the number of materials.
- $J = \{1, 2, \dots, m\}$: Set of cosmic radiation types, where $m$ is the number of radiation types.

### Parameters
- $c_i$: Unit cost of one layer of material $i \in I$ (from `materials.csv`).
- $T_j$: Minimum required attenuation threshold for radiation type $j \in J$ (from `radiations.csv`).
- $A_{i,j}$: Attenuation provided by one layer of material $i \in I$ against radiation type $j \in J$ (from `interactions.csv`).

### Decision Variables
- $x_i \in \mathbb{Z}_{\ge 0}$: The number of layers of material $i \in I$ to be used in the shielding system.

### Objective Function
Minimize the total cost of the composite shielding system:
$$\min Z = \sum_{i \in I} c_i x_i$$

### Constraints
1. **Attenuation Requirement**: For each radiation type $j$, the total attenuation provided by all selected material layers must be at least the required threshold:
   $$\sum_{i \in I} A_{i,j} x_i \ge T_j, \quad \forall j \in J$$

2. **Non-negativity and Integrality**: The number of layers for each material must be a non-negative integer:
   $$x_i \in \{0, 1, 2, \dots\}, \quad \forall i \in I$$

## Solution Approach
The problem is formulated as an Integer Linear Programming (ILP) model. Since the decision variables represent the number of layers (which must be discrete), and both the objective function and constraints are linear, we can use an ILP solver like Gurobi to find the optimal number of layers for each material.
