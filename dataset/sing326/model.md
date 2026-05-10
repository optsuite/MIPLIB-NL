# Reference Model (Answer Key): Slot Coverage with Policy Identities

This document is a **reference answer** describing how to rebuild the optimization model using only:

- `instance.json`
- the CSV files under `data/`

## 1. Entities (interpreting the data)

### Slots
- `data/slots.csv` defines the set of slots \u03a3, indexed by `slot_id`.
- Each slot `s` has an exact requirement `requirement[s]`.

### Adjustable segments
- `data/segments.csv` defines the set of adjustable segments \u0393, indexed by `segment_id`.
- Each segment `g` is associated with one slot `slot[g]`.
- Each segment has thresholds `low[g]`, `high[g]` and unit price `unit_price[g]`.

### Discrete actions
- `data/actions.csv` defines the set of actions \u0391, indexed by `action_id`.
- Each action has a fixed price `fixed_price[a]`.
- `data/action_contributions.csv` defines contributions `contribution[a,s]` (missing pairs are treated as 0).

### Fallback
- `data/fallback.csv` provides a single number `fallback_unit_price`.

### Policy nodes and identities
- `data/nodes.csv` defines binary nodes \u039d, indexed by `node_id`.
  - `node_kind = segment_switch` means the node references a `segment_id` in `ref_id`.
  - `node_kind = action_switch` means the node references an `action_id` in `ref_id`.
  - `node_kind = aux` means the node is an auxiliary internal state with no external reference.
  - `price[node]` is an optional fixed charge if the node is set to 1.
- `data/equations.csv` + `data/equation_terms.csv` define identities over nodes.

## 2. Decision quantities

### Node selections
For every node `n \u2208 \u039d`, introduce a binary decision:
- `y[n] \u2208 {0,1}`

### Segment delivered coverage
For every segment `g \u2208 \u0393`, introduce a nonnegative delivered amount:
- `x[g] \u2265 0`

Let `u[g]` be the activation switch for segment `g`, obtained from `nodes.csv`:
- Find the unique node `n` with `node_kind = segment_switch` and `ref_id = g`.
- Define `u[g] := y[n]`.

### Action triggering
Let `z[a]` be the trigger switch for action `a`, obtained from `nodes.csv`:
- Find the unique node `n` with `node_kind = action_switch` and `ref_id = a`.
- Define `z[a] := y[n]`.

### Fallback per slot
For every slot `s \u2208 \u03a3`, introduce fallback usage:
- `f[s] \u2265 0`

## 3. Objective (minimize total cost)

Minimize

\u2211_{g \u2208 \u0393} unit_price[g] \u00b7 x[g]\n+ \u2211_{a \u2208 \u0391} fixed_price[a] \u00b7 z[a]\n+ \u2211_{n \u2208 \u039d} price[n] \u00b7 y[n]\n+ fallback_unit_price \u00b7 \u2211_{s \u2208 \u03a3} f[s].

Notes:
- `price[n]` is typically 0 for most nodes, but it must be included to match the instance's intended accounting.

## 4. Constraints

### 4.1 Segment activation thresholds
For every segment `g \u2208 \u0393`:

- `x[g] \u2264 high[g] \u00b7 u[g]`
- `x[g] \u2265 low[g] \u00b7 u[g]`

This enforces:
- if `u[g]=0` then `x[g]=0`;
- if `u[g]=1` then `x[g] \u2208 [low[g], high[g]]`.

### 4.2 Slot coverage balance (exact matching)
For every slot `s \u2208 \u03a3`:

\u2211_{g \u2208 \u0393: slot[g]=s} x[g]\n+ \u2211_{a \u2208 \u0391} contribution[a,s] \u00b7 z[a]\n+ f[s]\n= requirement[s].

Implementation detail:
- Build a sparse mapping from `action_contributions.csv` and treat missing `(a,s)` pairs as 0.

### 4.3 Policy identities over nodes
For every identity `e` in `data/equations.csv`:

\u2211_{(e,n,\u03c3) \u2208 Terms} \u03c3 \u00b7 y[n] = rhs[e],

where `Terms` are all rows in `data/equation_terms.csv` having the same `eq_id = e`,
and `\u03c3` is the integer `sign` in that table (expected values are `+1` or `-1`).

## 5. Completeness checklist (data-to-model)

- Slots and requirements: `slots.csv`
- Adjustable segments, thresholds, unit prices, and slot assignment: `segments.csv`
- Discrete actions and fixed prices: `actions.csv`
- Action contribution patterns: `action_contributions.csv`
- Fallback unit price: `fallback.csv`
- Binary node inventory and mapping to segments/actions: `nodes.csv`
- Policy identities: `equations.csv` + `equation_terms.csv`

