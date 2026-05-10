# Chromatic Index Model

## Problem Description
We want to find the minimum number of colors required to color the edges of a graph such that no two edges incident to the same vertex share the same color. The graph is constructed based on the problem parameters.

## Sets
- $V$: Set of vertices.
- $E$: Set of edges.
- $C$: Set of available colors, $C = \{0, 1, 2, 3\}$. Since the maximum degree $\Delta(G) = 3$, by Vizing's Theorem, the chromatic index is either 3 or 4.

## Variables
- $x_{e,c} \in \{0, 1\}$: Binary variable, equal to 1 if edge $e \in E$ is assigned color $c \in C$, 0 otherwise.
- $u_c \in \{0, 1\}$: Binary variable, equal to 1 if color $c \in C$ is used by at least one edge, 0 otherwise.

## Objective Function
Minimize the total number of colors used:
$$ \min \sum_{c \in C} u_c $$

## Constraints
1. **Edge Coloring Constraint**: Each edge must be assigned exactly one color.
   $$ \sum_{c \in C} x_{e,c} = 1, \quad \forall e \in E $$

2. **Vertex Coloring Constraint & Color Usage**: For every vertex, edges incident to it must have distinct colors. Also, an edge can only use color $c$ if $u_c = 1$.
   $$ \sum_{e \in \delta(v)} x_{e,c} \le u_c, \quad \forall v \in V, \forall c \in C $$
   where $\delta(v)$ is the set of edges incident to vertex $v$. This constraint ensures that at most one edge incident to $v$ uses color $c$, and if $u_c=0$, no edge can use color $c$.
