### Problem Description (Reference Modeling Document)

This problem characterizes the dispatch/chassis planning in a port drayage scenario: a batch of transport orders needs to be completed and a batch of available chassis exists, requiring one-to-one matching; simultaneously, timestamps for several key events must be maintained to satisfy operational rules (such as time difference consistency and shared facility aggregation limits).

Data are provided in `instances/drayage-100-23/data/*.csv`; dimensions and unified default constants are provided by `problem_structure.csv`.

---

## Key Conventions

- `order_id`, `chassis_id`, and `time_id` are all zero-based.
- In principle, matching allows arbitrary combinations (full `N×M` selectable); `assignment_costs.csv` only lists explicit cost entries, and pairs not appearing use the implied baseline cost.
- Two types of rule tables in this instance adopt a "unified direction/unified constant" design: direction codes, thresholds, and large adjustment constants are all provided by `problem_structure.csv`.

---

## Decision Objects (Expressed in Business Terms)

1) **Matching Selection**
Select a chassis for each order, and each chassis is used by exactly one order.

2) **Key Event Times**
Select a timestamp for each `time_id`, and the timestamp must fall within the allowable interval.

---

## Optimization Objective

Minimize total cost while satisfying rules:
- If a specific order-chassis combination appears in `assignment_costs.csv`, use that explicit cost;
- If it does not appear, use the implied baseline cost.

---

## Rule Structure (Can be directly reconstructed as linear constraints)

To facilitate reproduction, equivalent linear templates are written below using "matching indicators" and "timestamps". Any solver (Gurobi, CPLEX, etc.) can be used for implementation.

### 1) One-to-One Matching Rules

- Each order must be covered once: for each `order_id`, the sum of its selections across all `chassis_id` equals 1.
- Each chassis must be used once: for each `chassis_id`, the sum of its selections across all `order_id` equals 1.

### 2) Timestamp Allowable Intervals

For each `time_id`:
- `lower_bound <= time[time_id] <= upper_bound`, where bounds come from `time_bounds.csv`.

### 3) Time Difference Consistency Rules (`pair_time_link_rules.csv`)

Each record describes: when the same order switches between two chassis choices, the requirement for the time difference between two events "shifts".

For each rule record (containing `order_id, chassis_alternative, time_from, time_to, fixed_choice_coefficient, rhs`), this instance adopts a convention: **the "primary chassis" for an order is the chassis with the same ID number**. Combined with the following given in `problem_structure.csv`:
- Unified direction code (comparison direction)
- Unified large adjustment constant

The linear template is:

```
(time[time_to] - time[time_from])
  + fixed_choice_coefficient * assign(order_id, primary_chassis)
  - (large_adjustment_constant) * assign(order_id, chassis_alternative)
  (comparison_direction) rhs
```

### 4) Aggregation Usage Limit Rules (`chassis_time_rules.csv` + `order_groups.csv`)

This instance uses only one order set: `order_groups.csv` lists the `order_id` contained in this set (the set may cover only a subset of orders).

For each aggregation rule record (containing `chassis_id, time_id, assignment_coefficient`), use the following given in `problem_structure.csv`:
- Unified direction code (comparison direction)
- Unified threshold

The linear template is:

```
time[time_id]
  + assignment_coefficient * sum_{order in order_groups.csv} assign(order, chassis_id)
  (comparison_direction) (threshold)
```

---

## Data File Reference

- `assignment_costs.csv`: Explicit cost entries (sparse); non-appearing pairs use baseline cost.
- `time_bounds.csv`: Timestamp lower and upper bounds.
- `pair_time_link_rules.csv`: Time difference consistency rule records (direction and large constant in `problem_structure.csv`).
- `order_groups.csv`: Single order set member table.
- `chassis_time_rules.csv`: Aggregation rule records (direction and threshold in `problem_structure.csv`).
- `problem_structure.csv`: Dimensions and unified default constants.