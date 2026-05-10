### Problem Description
- Given I items with weights and a knapsack with capacity W, select a subset of items to maximize/minimize the total value while respectingthe capacity constraint
### Parameter Description
- $I$:  Number of items to be packed
- $W$: Lower bound on the total weight of all packed items
- $W_e$:Weight of each item $e$


### Decision Variables
- $x_e$: 0-1 variable indicating whether each item is packed, where $x_e = 1$ if item $e$ is packed, and 0 otherwise

### Objective Function

$$ 
\minimize \quad \sum_{e}  W_e x_e 
$$ 

### Constraints
1. knapsack Constraint: $$ \sum_{e}  W_e x_e >= W $$