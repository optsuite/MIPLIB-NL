# Fleet Assignment Problem

## Problem Description
Assume you are the scheduling director of a large logistics company. You need to deliver goods to $N_1$ different destinations, and you have $N_2$ different types of vehicles. The quantity of each vehicle type is limited. Each vehicle type has a specific transportation cost and cargo capacity depending on the destination it is assigned to. Each destination has a specific demand for goods that must be met. The objective is to determine the optimal number of vehicles of each type to assign to each destination so that the total transportation cost is minimized while satisfying all demands and vehicle inventory constraints.

## Sets and Indices
* $I = \{1, 2, \dots, N_2\}$: Set of vehicle types.
* $J = \{1, 2, \dots, N_1\}$: Set of destinations.
* $i \in I$: Index for vehicle type.
* $j \in J$: Index for destination.

## Parameters
* $S_i$: The available quantity (supply) of vehicle type $i$ (Data from Table C1).
* $C_{ij}$: The transportation cost of assigning one vehicle of type $i$ to destination $j$ (Data from Table C2).
* $K_{ij}$: The quantity of goods (capacity) that one vehicle of type $i$ can transport to destination $j$ (Data from Table C3).
* $D_j$: The total quantity of goods required by destination $j$ (Data from Table C4).

## Decision Variables
* $x_{ij}$: The number of vehicles of type $i$ assigned to destination $j$ (Integer).

## Objective Function
The objective is to minimize the total transportation cost:
$$
\min Z = \sum_{i \in I} \sum_{j \in J} C_{ij} \cdot x_{ij}
$$

## Constraints
1.  **Vehicle Availability Constraints**:
    For each vehicle type $i$, the total number of vehicles assigned to all destinations cannot exceed the available inventory $S_i$.
    $$
    \sum_{j \in J} x_{ij} \leq S_i, \quad \forall i \in I
    $$

2.  **Demand Satisfaction Constraints**:
    For each destination $j$, the total quantity of goods transported by all assigned vehicles must be at least the required demand $D_j$.
    $$
    \sum_{i \in I} K_{ij} \cdot x_{ij} \geq D_j, \quad \forall j \in J
    $$

3.  **Integer Constraints**:
    The number of vehicles assigned must be a non-negative integer.
    $$
    x_{ij} \in \mathbb{Z}_{\geq 0}, \quad \forall i \in I, \forall j \in J
    $$