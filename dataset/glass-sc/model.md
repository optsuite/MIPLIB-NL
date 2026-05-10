### Problem Description
- This is a multi-set cover problem, where the goal is to select the minimum number of sets such that each integer from 1 to I is covered a certain number of times. The sets available for selection are stored in sets S1 and S2, and each set lists the integers it covers. Sets in S1 can only be selected 0 or 1 time. Each set in S2 can be selected continuously, with the selection count being a real number not less than 0 and not more than 1. Whenever a set is selected a non-integer number of times, the integers it contains are also considered to be covered the corresponding non-integer number of times.

### Parameter Description
- $I$: The number of integers that need to be covered; each integer from 1 to I needs to be covered once.
- $S1$: A family of "sets" available for selection; $s \in S1$ can be selected either 0 or 1 time.
- $S2$: A family of "sets" available for selection; $s \in S2$ can be selected a continuous number of times, with the selection count being a real number not less than 0 and not more than 1.
- $a_{es}$: A binary parameter; it is 1 if integer $e$ belongs to set $s$, otherwise 0.
- $r_e$: The minimum number of times integer $e$ needs to be covered (redundancy or requirement degree).

### Decision Variables
- $x_s$: A binary variable; it is 1 if set $s$ is selected for coverage, otherwise 0.

### Objective Function
The goal is to minimize the total cost of all selected sets.
$$ 
\minimize \quad \sum_{s\in S1}  x_s \label{eq:objective}
$$ 

### Constraints
1. Multi-Cover Constraint: For each element $e$, the total number of all selected sets that contain this element must be at least equal to the coverage requirement $r_e$ of that element. $$ \sum_{s \in S} a_{es} \cdot x_s \geq r_e \quad \forall e \in E $$