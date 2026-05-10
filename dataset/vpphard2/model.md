# Reference Model (Answer Key): Vehicle Positioning with Pooled Quotas and Operational Windows (vpphard2)

This document is the reference optimization model that can be reconstructed from `instance.json` and the CSV files under `data/`.

## 1. Data and Derived Quantities

Read the following tables:

- `units.csv`: `(unit_id, start_location_id)`
- `targets.csv`: `(location_id, required_units)`
- `relocation_options.csv`: `(option_id, unit_id, dest_location_id, wave_id)`
- `quota_pools.csv`: `(pool_id, type_id, pool_size)`
- `option_quota_pools.csv`: `(option_id, pool_id)`
- `balance_rules.csv`: `(rule_id, location_id, wave_id, rule_kind)`
- `operation_windows.csv`: `(window_id, yard_id, location_id, stage_id, base_capacity, open_cost)`
- `steps.csv`: `(step_id, window_id)`
- `option_steps.csv`: `(option_id, step_id)`

Derived mappings:

- For each option `o`, define:
  - `unit(o)`, `dest(o)`, `wave(o)` from `relocation_options.csv`.
  - `start(o) = start_location_id[ unit(o) ]` using `units.csv`.
  - `pool(o)` from `option_quota_pools.csv`.
- For each step `s`, define `window(s)` using `steps.csv`.
- Define the window-requirement relation:
  - `RequiresWindow(o, w) = 1` iff there exists a step `s` such that `(o, s)` is in `option_steps.csv` and `window(s) = w`.

## 2. Decision Variables

- `x[o] ∈ {0,1}` for each relocation option `o`:
  - `x[o] = 1` means option `o` is selected and executed.
- `open[w] ∈ {0,1}` for each operational window `w`:
  - `open[w] = 1` means an additional unit of capacity is activated for window `w`.

## 3. Objective

Minimize total operational-window opening cost:

\[
\min \sum_{w} open\_cost[w] \cdot open[w].
\]

## 4. Constraints

### 4.1 Exactly one option per unit

Each vehicle must be assigned exactly one relocation option:

\[
\sum_{o : unit(o)=u} x[o] = 1, \quad \forall u.
\]

### 4.2 Morning placement requirements

Each location must receive exactly the required number of vehicles:

\[
\sum_{o : dest(o)=\ell} x[o] = required\_units[\ell], \quad \forall \ell.
\]

### 4.3 Quota pool requirements (pooled availability)

Each quota pool must select exactly its required number of options:

\[
\sum_{o : pool(o)=p} x[o] = pool\_size[p], \quad \forall p.
\]

### 4.4 Exchange-only hub accounting rules

For each rule row `(location_id=\ell, wave_id=t)` with `rule_kind = EXCHANGE_ONLY`, require that in wave `t` the number of selected arrivals equals the number of selected departures:

\[
\sum_{o : dest(o)=\ell,\, wave(o)=t} x[o] - \sum_{o : start(o)=\ell,\, wave(o)=t} x[o] = 0.
\]

Only pairs `(\ell,t)` listed in `balance_rules.csv` are constrained.

### 4.5 Operational-window capacity and activation

Each operational window provides a baseline capacity, and opening it activates one additional unit of capacity. For each window:

\[
\sum_{o : RequiresWindow(o,w)=1} x[o] \le base\_capacity[w] + open[w], \quad \forall w.
\]

With binary `open[w]`, this means the window can accommodate `base_capacity[w]` options without paying, and paying buys one extra slot for that window.

## 5. Notes for Implementation

- The model is a binary integer program.
- The main difficulty is building the relations by joins:
  - compute `start(o)` by joining `relocation_options.csv` with `units.csv`;
  - compute `RequiresWindow(o,w)` by joining `option_steps.csv` → `steps.csv`;
  - enforce pooled quota via `option_quota_pools.csv` and `quota_pools.csv`.

