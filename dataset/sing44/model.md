# sing44 — Reference Optimization Model (Answer Key)

This document specifies a clean mathematical model that can be rebuilt from:
- `data/slots.csv`
- `data/segments.csv`
- `data/actions.csv`
- `data/action_contributions.csv`
- `data/fallback.csv`
- `data/nodes.csv`
- `data/equations.csv`
- `data/equation_terms.csv`

The model is equivalent (in structure and values) to `sing44.mps`, but uses opaque identifiers and business-facing tables.

---

## Sets

- Slots: \u03a3, indexed by `slot_id`, from `slots.csv`.
- Segments: \u0393, indexed by `segment_id`, from `segments.csv`.
- Actions: \u0391, indexed by `action_id`, from `actions.csv`.
- Fallback options: \u03a6, indexed by `fallback_id`, from `fallback.csv`.
- Bounded fallback options: \u03a6_b \u2286 \u03a6, indexed by `fallback_id`, from `fallback_bounds.csv`.
- Policy nodes: \u039d, indexed by `node_id`, from `nodes.csv`.
- Policy equations: \u0395, indexed by `eq_id`, from `equations.csv`.

Define helper mappings:
- `slot(seg)`: the slot associated with a segment, from `segments.csv`.
- `slot(fb)`: the slot associated with a fallback option, from `fallback.csv`.
- `switch(seg)`: node_id that toggles a segment, from `nodes.csv` where `node_kind = segment_switch` and `ref_id = segment_id`.
- `switch(act)`: node_id that toggles an action, from `nodes.csv` where `node_kind = action_switch` and `ref_id = action_id`.

---

## Parameters

From `slots.csv`:
- Requirement `req[s]` for each slot `s \u2208 \u03a3`.

From `segments.csv`:
- Lower threshold `L[seg]`, upper threshold `U[seg]`, unit price `c_seg[seg]`.

From `actions.csv`:
- Fixed price `c_act[act]`.

From `action_contributions.csv`:
- Contribution `a[act,s]` for the listed (act, slot) pairs. (Pairs not present imply 0.)

From `fallback.csv`:
- Unit price `c_fb[fb]` for each fallback option `fb \u2208 \u03a6`.

From `fallback_bounds.csv` (subset):
- Minimum required amount `fb_min[fb]` and maximum allowed amount `fb_max[fb]` for each `fb \u2208 \u03a6_b`.

From `nodes.csv`:
- Additional fixed price `c_node[n]` for each node `n \u2208 \u039d` (often nonzero only for `aux`).

From `equations.csv` and `equation_terms.csv`:
- RHS `rhs[e] \u2208 {-1,0,1}` for each policy equation `e \u2208 \u0395`.
- Signed incidence `sign[e,n] \u2208 {-1,+1}` for each listed term (missing pairs imply 0).

---

## Decision Variables

- Segment delivered coverage: `x[seg] \u2265 0` for all `seg \u2208 \u0393`.
- Fallback purchased amount: `f[fb] \u2265 0` for all `fb \u2208 \u03a6`.
- Policy node selection: `b[n] \u2208 {0,1}` for all `n \u2208 \u039d`.

---

## Objective

Minimize total cost:

\u2003min \u2211_{seg \u2208 \u0393} c_seg[seg] \u00b7 x[seg]\n\
\u2003\u2003\u2003 + \u2211_{act \u2208 \u0391} c_act[act] \u00b7 b[switch(act)]\n\
\u2003\u2003\u2003 + \u2211_{n \u2208 \u039d} c_node[n] \u00b7 b[n]\n\
\u2003\u2003\u2003 + \u2211_{fb \u2208 \u03a6} c_fb[fb] \u00b7 f[fb]

---

## Constraints

### 1) Segment activation thresholds

For each segment `seg`:

- `x[seg] \u2264 U[seg] \u00b7 b[switch(seg)]`
- `x[seg] \u2265 L[seg] \u00b7 b[switch(seg)]`

If the switch node is 0, these force `x[seg] = 0`. If it is 1, they force `x[seg] \u2208 [L[seg], U[seg]]`.

---

### 2) Slot coverage exact balance

For each slot `s`:

\u2003\u2211_{seg: slot(seg)=s} x[seg]\n\
\u2003+ \u2211_{act \u2208 \u0391} a[act,s] \u00b7 b[switch(act)]\n\
\u2003+ \u2211_{fb: slot(fb)=s} f[fb]\n\
\u2003= req[s]

---

### 2b) Fallback option bounds (only for a subset)

For each `fb \u2208 \u03a6_b`:

- `f[fb] \u2265 fb_min[fb]`
- `f[fb] \u2264 fb_max[fb]`

Fallback options not listed in `fallback_bounds.csv` have no additional bounds beyond `f[fb] \u2265 0`.

---

### 3) Internal policy identities (signed balance)

For each policy equation `e`:

\u2003\u2211_{n \u2208 \u039d} sign[e,n] \u00b7 b[n] = rhs[e]

where `sign[e,n]` is defined by `equation_terms.csv` (and 0 otherwise).

---

## Notes on reconstruction

- All identifiers are opaque; correctness depends on joining tables by keys (`*_id`).
- `nodes.csv` uses an empty string in `ref_id` for `aux` nodes; when reading CSV, avoid converting empty strings to NaN.
