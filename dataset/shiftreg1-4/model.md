# Single-Activity Shift Scheduling with a Compact Sequence Rulebook

## Business interpretation

This instance models a one-day staffing plan for a single operational activity. The day is divided into equal time slots. The operation has a target staffing level for each time slot in the service window.

The schedule is allowed to miss or exceed the target staffing level, but it pays a penalty that is charged per person-slot of deviation (one person-slot means one missing or extra employee in one time slot). The penalty rates are time-dependent: each time slot can have its own understaffing rate and overstaffing rate (see `demand.csv`).

Each employee either stays off duty all day or works a shift that must follow a compact rulebook of allowed daily status sequences. The rulebook is provided as a small transition graph (states and labeled transitions) that captures operational feasibility, such as:

- when work can start,
- how work can continue,
- when short breaks can be taken,
- when a longer meal break can be taken,
- and how the shift can end and remain off duty afterwards.

On top of that rulebook, the instance enforces simple totals that managers typically use: if an employee works at all, then the total number of working slots must lie in a specified range; the plan classifies the employee as either short-shift or long-shift based on total working slots; short shifts and long shifts require different numbers of short breaks; and long shifts additionally require a consecutive meal break.

## Data mapping

The instance is described by `instance.json` and the CSV files in `data/`:

- `demand.csv`: required staffing and deviation penalties per time slot
- `work_cost.csv`: per-employee labor cost per working slot
- `label_time_windows.csv`: when each status label is allowed
- `automaton_transitions.csv`: the compact sequence rulebook
- `rulebook_edges.csv`: a pruned time expansion for exact reproduction

## Reference optimization model (clean rebuild)

### Sets

- Employees: \(e \in \mathcal{E}\)
- Time slots: \(t \in \mathcal{T}\)
- Rulebook states: \(s \in \mathcal{S}\)
- Labels: \(\ell \in \{\text{off}, \text{work}, \text{short\_break}, \text{meal\_break}\}\)
- Rulebook transitions: \((s,\ell,s') \in \mathcal{A}\)

### Parameters

- Required staff: \(d_t\) (from `demand.csv`)
- Under/over penalties: \(\pi^{under}_t\), \(\pi^{over}_t\) (from `demand.csv`)
- Work cost: \(c_{e,t}\) (from `work_cost.csv`)
- Allowed label windows (from `label_time_windows.csv`)
- Shift-length rules: minimum/maximum working slots, and short/long classification thresholds (from `instance.json`)
- Required number of short-break slots and meal-break slots (from `instance.json`)

### Decision variables

- \(w_e \in \{0,1\}\): 1 if employee \(e\) is scheduled to work at all (otherwise they remain off duty all day).
- \(u_e \in \{0,1\}\): 1 if employee \(e\) is on a long shift (otherwise short shift); only meaningful when \(w_e=1\).
- \(x^{work}_{e,t} \in \{0,1\}\): 1 if employee \(e\) works in time slot \(t\).
- \(x^{short}_{e,t} \in \{0,1\}\): 1 if employee \(e\) is on a short break in time slot \(t\).
- \(x^{meal}_{e,t} \in \{0,1\}\): 1 if employee \(e\) is on a meal break in time slot \(t\).
- \(x^{off}_{e,t} \in \{0,1\}\): 1 if employee \(e\) is off duty in time slot \(t\).
- \(f_{e,t,s,\ell} \ge 0\): transition-use flow for the rulebook (from state \(s\) using label \(\ell\) at time \(t\)).
- Under/over amounts: \(m_t \ge 0\) (understaffing), \(p_t \ge 0\) (overstaffing).

### Core relationships

Coverage balance (soft demand):

\[
\sum_{e \in \mathcal{E}} x^{work}_{e,t} + m_t - p_t = d_t \quad \forall t \text{ in the service window}.
\]

Per-employee daily totals (in working-slot units):

Let \(H_e = \sum_{t \in \mathcal{T}} x^{work}_{e,t}\).

- If working, at least a minimum and at most a maximum:
\[
H_e \ge H^{min} w_e,\quad H_e \le H^{max} w_e.
\]
- Short vs long classification:
\[
H_e \le H^{short\_max} + (H^{max}-H^{short\_max})u_e,\quad H_e \ge H^{long\_min} u_e,\quad u_e \le w_e.
\]
- Short-break and meal-break requirements:
\[
\sum_{t \in \mathcal{T}} x^{short}_{e,t} = w_e + u_e,\quad \sum_{t \in \mathcal{T}} x^{meal}_{e,t} = B^{meal}\,u_e.
\]

One daily status per time slot (conditional on being scheduled):

\[
x^{off}_{e,t} + x^{work}_{e,t} + x^{short}_{e,t} + x^{meal}_{e,t} = w_e \quad \forall e,t,
\]
with labels restricted to their allowed windows.

Compact rulebook (sequence feasibility):

The rulebook is a transition graph. At each time slot, the employee's chosen label must be supported by a valid transition out of the current state, and states must connect over time via flow conservation. The linking constraints ensure that label indicators match the sum of rulebook transition-use variables with the corresponding label.

### Objective

\[
\min \sum_{e,t} c_{e,t} x^{work}_{e,t} + \sum_t \pi^{under}_t m_t + \sum_t \pi^{over}_t p_t.
\]

## Notes

- The original MPS was generated from a compact \"regular-language style\" rulebook; the extracted `automaton_*.csv` captures that compact structure in a reusable way.
- `solver.py` rebuilds the model from the CSV files and checks the objective value against `shiftreg1-4.mps`.
