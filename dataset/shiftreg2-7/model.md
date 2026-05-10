# Multi-Service Shift Scheduling with a Compact Sequence Rulebook

## Business interpretation

This instance models a one-day staffing plan for multiple service lines. The day is divided into equal time slots. For each service line and each time slot when it is open, the business sets a target staffing level (required headcount working on that line in that slot).

The schedule may fall short of or exceed the target, but it pays a penalty that is charged per person-slot of deviation (one person-slot means one missing or extra employee in one time slot for a particular service line). The penalty rates are time-dependent and service-line-dependent (see `demand.csv`).

Each employee either stays off duty all day or works a shift that must follow a compact rulebook of allowed daily status sequences. In each time slot, the employee is in exactly one of:

- off duty,
- short break,
- meal break,
- working on exactly one service line.

The rulebook is provided as a small transition graph (states and labeled transitions) that captures operational feasibility, such as when work can start, how work can continue without interruption, when breaks can happen, and how the shift can end and remain off duty afterwards.

## Data mapping

The instance is described by `instance.json` and the CSV files in `data/`:

- `demand.csv`: required staffing and deviation penalties per (time slot, service line)
- `work_cost.csv`: per-employee labor cost per (time slot, service line)
- `label_time_windows.csv`: when each rulebook label is allowed
- `automaton_transitions.csv`: the compact sequence rulebook
- `rulebook_edges.csv`: a pruned time expansion for exact reproduction

## Reference optimization model (clean rebuild)

### Sets

- Employees: \(e \in \mathcal{E}\)
- Time slots: \(t \in \mathcal{T}\)
- Service lines: \(a \in \mathcal{A}\)
- Rulebook states: \(s \in \mathcal{S}\)
- Rulebook transitions: \((s,\ell,s') \in \mathcal{R}\), with labels \(\ell\) in \(\{\text{off},\text{short\_break},\text{meal\_break}\} \cup \{\text{activity codes}\}\)

### Parameters

- Required staff: \(d_{t,a}\) (from `demand.csv`)
- Under/over penalty rates: \(\pi^{under}_{t,a}\), \(\pi^{over}_{t,a}\) (from `demand.csv`)
- Work cost: \(c_{e,t,a}\) (from `work_cost.csv`)
- Shift policy parameters (from `instance.json`)

### Decision variables

- \(w_e \in \{0,1\}\): 1 if employee \(e\) is scheduled to work at all
- \(u_e \in \{0,1\}\): 1 if employee \(e\) is on a long shift (otherwise short shift), only meaningful when \(w_e=1\)
- \(x_{e,t,a} \in \{0,1\}\): 1 if employee \(e\) works on service line \(a\) in time slot \(t\)
- \(b^{short}_{e,t} \in \{0,1\}\): 1 if employee \(e\) is on a short break in time slot \(t\)
- \(b^{meal}_{e,t} \in \{0,1\}\): 1 if employee \(e\) is on a meal break in time slot \(t\)
- \(o_{e,t} \in \{0,1\}\): 1 if employee \(e\) is off duty in time slot \(t\)
- Under/over amounts: \(m_{t,a} \ge 0\) (understaffing), \(p_{t,a} \ge 0\) (overstaffing)
- Rulebook flow variables on the (pruned) time-expanded graph (see `rulebook_edges.csv`)

### Core relationships

Service-line coverage balance (soft demand):

\[
\sum_{e \in \mathcal{E}} x_{e,t,a} + m_{t,a} - p_{t,a} = d_{t,a} \quad \forall (t,a) \text{ in demand.csv}.
\]

One status per employee and time slot (conditional on being scheduled):

\[
o_{e,t} + b^{short}_{e,t} + b^{meal}_{e,t} + \sum_{a \in \mathcal{A}} x_{e,t,a} = w_e \quad \forall e,t.
\]

Shift policy totals (in working-slot units):

Let \(H_e = \sum_{t,a} x_{e,t,a}\).

The instance enforces short/long classification by total working slots, as well as the required number of short-break slots and (for long shifts) the required number of meal-break slots.

Compact rulebook (sequence feasibility):

The rulebook is a transition graph. At each time slot, the employee's chosen label must be supported by a valid transition out of the current state, and states must connect over time via flow conservation. `solver.py` uses `rulebook_edges.csv` to reproduce the exact pruned expansion used by this instance.

### Objective

\[
\min \sum_{e,t,a} c_{e,t,a} x_{e,t,a} + \sum_{t,a} \pi^{under}_{t,a} m_{t,a} + \sum_{t,a} \pi^{over}_{t,a} p_{t,a}.
\]

## Notes

- The original MPS was generated from a compact \"regular-language style\" rulebook; the extracted `automaton_*.csv` captures that compact structure in a reusable way.
- When a solver hits a time limit, objective values may differ between equivalent model encodings; to certify equivalence you should compare at optimality or validate feasibility/objective mappings.
