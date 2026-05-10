# ### Problem Description
- We need to develop an optimal substitution schedule for a basketball team consisting of $N_1$ players over a game duration of $N_2$ quarters.
- The goal is to maximize the fairness of the schedule by maximizing the playing time of the player with the least court time (Maximize Minimum Playing Time).
- The schedule must adhere to strict operational constraints: exactly $P$ players must be on the court at any time, and substitutions are only allowed at specific intervals (halfway through each quarter).

### Parameter Description
- $N_1$: Total number of players on the team ($N_1 = 11$).
- $N_2$: Number of quarters in a game ($N_2 = 4$).
- $P$: Number of players required on the court ($P = 5$).
- $T$: Total number of substitution slots. Since substitutions occur every half-quarter, $T = N_2 \times 2 = 8$.
- $Slots$: The set of time slots, indexed by $t \in \{0, \dots, T-1\}$.
- $Players$: The set of players, indexed by $i \in \{0, \dots, N_1-1\}$.

### Decision Variables
- $x_{i,t}$: Binary variable indicating whether player $i$ is on the court during time slot $t$. $x_{i,t} = 1$ if playing, and 0 otherwise.
- $z$: Integer variable representing the minimum playing time (in slots) among all players.

### Objective Function

The objective is to maximize the minimum playing time $z$:

$$
\maximize \quad z
$$

### Constraints

1. **Court Capacity Constraint:**
   For every time slot $t$, exactly $P$ players must be on the court.
   $$\sum_{i=0}^{N_1-1} x_{i,t} = P \quad \forall t \in \{0, \dots, T-1\}$$

2. **Minimum Playing Time Definition:**
   For every player $i$, the total playing time (sum of active slots) must be greater than or equal to $z$.
   $$\sum_{t=0}^{T-1} x_{i,t} \ge z \quad \forall i \in \{0, \dots, N_1-1\}$$

3. **Binary Constraints:**
   $$x_{i,t} \in \{0, 1\} \quad \forall i, t$$
   $$z \ge 0$$