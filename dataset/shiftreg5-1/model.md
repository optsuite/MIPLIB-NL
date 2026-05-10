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

The clean rebuild is identical in structure to the one described in `shiftreg2-7.md`, except that this instance has a different number of employees and service lines.

## Notes

- The original MPS was generated from a compact \"regular-language style\" rulebook; the extracted `automaton_*.csv` captures that compact structure in a reusable way.
- When a solver hits a time limit, objective values may differ between equivalent model encodings; to certify equivalence you should compare at optimality or validate feasibility/objective mappings.
