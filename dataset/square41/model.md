# Mathematical Model: Square Tiling (square41)

## Problem
Tile a 41×41 grid with minimum number of axis-aligned integer-sized squares (1 to 40).

## Variables
$$x_{i,j,s} \in \{0,1\}$$ - square of size s at position (i,j)

## Objective
$$\min \sum_{i,j,s} x_{i,j,s}$$

## Constraints
Each cell (r,c) covered exactly once.

## Key Insight
- courtyard_side = 41 → sizes 1 to 40 are all valid
- slab_samples.csv shows only samples, NOT the complete size list
- labor_rates.csv is completely irrelevant

## Optimal Value
**15 blocks**
