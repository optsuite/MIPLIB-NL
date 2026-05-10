# Mathematical Model: Square Tiling (square37)

## Problem
Tile a 37×37 grid with minimum number of axis-aligned integer-sized squares (1 to 36).

## Variables
$$x_{i,j,s} \in \{0,1\}$$ - square of size s at position (i,j)

## Objective
$$\min \sum_{i,j,s} x_{i,j,s}$$

## Constraints
Each cell (r,c) covered exactly once:
$$\sum_{\{(i,j,s): i \le r \le i+s-1, j \le c \le j+s-1\}} x_{i,j,s} = 1$$

## Key Insight for Modelers
- courtyard_side = 37 → sizes 1 to 36 are all valid
- slab_samples.csv shows only 15 samples, NOT the complete size list
- labor_rates.csv is completely irrelevant
- "any whole-cubit size that fits" = sizes 1 to n-1

## Optimal Value
**15 blocks**
