# Mathematical Model: Fixed-Charge Network Flow

## Problem Overview

Select a subset of directed links in a network. Activating a link incurs a fixed cost. Flow can be sent only on activated links, and each link has a capacity limit. The goal is to satisfy node balance requirements at minimum total fixed cost.

## Sets and Indices

- $\mathcal{N}$: set of nodes
- $\mathcal{A}$: set of directed arcs
- $i \in \mathcal{N}$: node index
- $(i,j) \in \mathcal{A}$: arc from node $i$ to node $j$

## Decision Variables

- $x_{ij} \ge 0$: amount of flow sent on arc $(i,j)$
- $y_{ij} \in \{0,1\}$: 1 if arc $(i,j)$ is activated, 0 otherwise

## Parameters

- $f_{ij} \ge 0$: fixed cost of activating arc $(i,j)$
- $u_{ij} > 0$: capacity of arc $(i,j)$
- $b_i \in \mathbb{R}$: net balance requirement at node $i$ (positive supply, negative demand)
- $\delta^{+}(i)$: arcs leaving node $i$
- $\delta^{-}(i)$: arcs entering node $i$

## Objective

$$\min \sum_{(i,j)\in\mathcal{A}} f_{ij} y_{ij}$$

## Constraints

### Flow balance

For all $i \in \mathcal{N}$:

$$\sum_{(i,j)\in\delta^{+}(i)} x_{ij} - \sum_{(j,i)\in\delta^{-}(i)} x_{ji} = b_i$$

### Capacity with activation

For all $(i,j) \in \mathcal{A}$:

$$x_{ij} \le u_{ij} y_{ij}$$

