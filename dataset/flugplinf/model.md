# ### Problem Description
- We need to develop an optimal pilot recruitment and scheduling plan for an airline company over $T$ operational periods (months).
- The goal is to minimize the total operational cost, which includes the salaries of regular pilots, the wages of trainee pilots, and the costs associated with overtime work.
- The schedule must satisfy several operational constraints: workforce flow balance (considering attrition and training completion), task demand satisfaction (adjusting for training overhead), overtime capacity limits, and workforce size restrictions.

### Parameter Description
- $T$: Number of planning periods (months) ($N2 = 6$).
- $N1$: Initial number of regular pilots ($N1 = 60$).
- $N3$: Regular task capacity per pilot ($N3 = 150$).
- $N4$: Monthly salary of a regular pilot ($N4 = 2700$).
- $N5$: Attrition rate of regular pilots per month ($N5 = 0.1$).
- $N6$: Task load overhead (reduction) per trainee ($N6 = 100$).
- $N7$: Monthly salary of a trainee pilot ($N7 = 1500$).
- $N8$: Maximum number of trainees recruited per month ($N8 = 18$).
- $N9$: Maximum total number of regular pilots ($N9 = 75$).
- $N10$: Minimum total number of regular pilots ($N10 = 57$).
- $N11$: Maximum overtime factor per regular pilot ($N11 = 20$).
- $N12$: Cost per unit of task completed via overtime ($N12 = 30$).
- $D_t$: Task demand in month $t$ defined in task.csv.

### Decision Variables
- $STM_t$: Integer variable, number of regular (skilled) pilots in month $t$.
- $ANM_t$: Integer variable, number of newly hired trainee pilots in month $t$.
- $UE_t$: Continuous variable, amount of task units completed via overtime in month $t$.

### Objective Function

$$
\text{Minimize} \quad \sum_{t=1}^{T} (N4 \cdot STM_t + N7 \cdot ANM_t + N12 \cdot UE_t)
$$

### Constraints

1.  **Staff Flow Balance:**
    The number of regular pilots in the next month equals the retained pilots from the current month plus the trainees who have completed their one-month training.
    Let retention rate $R = 1 - N5$.
    $$STM_{t+1} = R \cdot STM_t + ANM_t \quad \forall t \in \{1, \dots, T-1\}$$
    $$STM_1 = N1$$

2.  **Task Demand Satisfaction:**
    The total effective capacity (regular work hours minus time spent training new hires plus overtime hours) must meet or exceed the monthly task demand.
    $$N3 \cdot STM_t - N6 \cdot ANM_t + UE_t \ge D_t \quad \forall t$$

3.  **Overtime Capacity Limit:**
    The total volume of tasks completed via overtime cannot exceed a fixed multiple of the regular pilot workforce.
    $$UE_t \le N11 \cdot STM_t \quad \forall t$$

4.  **Hiring Limit:**
    The number of new trainees recruited each month is capped.
    $$0 \le ANM_t \le N8 \quad \forall t$$

5.  **Workforce Size Limits:**
    The total number of regular pilots must remain within the specified minimum and maximum bounds.
    $$N10 \le STM_t \le N9 \quad \forall t$$