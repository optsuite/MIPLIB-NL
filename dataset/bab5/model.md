# Mathematical Model (Structured): Vehicle Routing with Profits + Integrated Crew Scheduling

This instance represents a planning problem where a company chooses:

- Which **vehicle-side movements / service transitions** to operate (to earn revenue or incur cost),
- Which **crew-side transitions** to operate (to staff and legally cover the vehicle operations),

so that a set of linked “vehicle paths” and “crew paths” can be formed in multiple disconnected time-space sub-networks. The formulation can be viewed as **two coupled multi-commodity flow models**: one for vehicles and one for crews, coupled by activation-and-endpoint rules and additional operational policies.

The data files in `data/` provide a compact, reusable representation that lets you rebuild the original MPS model without relying on the MPS naming.

## Sets

- **Decisions** `D`: binary decisions (each represents selecting a transition, a block, or an auxiliary choice).
- **Start slots** `S`: each slot requires exactly one start option to be chosen.
- **Balance nodes** `N`: nodes of time-space flow balance equations (mostly zero net flow).
- **Packages** `P`: activation entities that require exactly two associated candidate decisions when activated.
- **Windows** `W`: operational windows that bound how many selected vehicle transitions can be scheduled in that window.
- **Mix dimensions** `K`: policy dimensions limiting the share of selected vehicle transitions with a given attribute.
- **Coverage groups** `G`: groups requiring at least a minimum number of selected decisions.
- **Conflict groups** `C`: small groups where at most one decision may be selected.
- **Dependency rules** `R`: logical prerequisites (“if you pick this, you must pick at least one of those”).
- **Exact-choice groups** `X`: groups where an exact number of decisions must be selected.
- **Cardinality caps** `K`: groups that cap how many member decisions may be selected.
- **Redundant bounds** `B`: optional traceability bounds that are implied by binary decisions.

## Decision variables

For each `d ∈ D`:

- `x_d ∈ {0,1}`: whether the decision is selected.

## Parameters (from data files)

- `cost_d`: objective coefficient for each decision.
- Start-slot membership: which decisions are valid options for each slot.
- Flow balance graph:
  - `from_node(d), to_node(d)` for many decisions (directed arc representation),
  - additional node coefficients for exceptional decisions.
- Package membership: which candidates belong to each package.
- Window membership and window bounds.
- Mix targets and per-decision attribute flags.
- Coverage minimums and membership.
- Conflict membership.
- Dependency edges.
- Exact-choice membership and required counts.
- Cardinality-cap membership and limits.
- Optional redundant bounds (traceability only).

## Objective

Minimize total net cost:

\\[
\\min \\sum_{d \\in D} cost_d\\, x_d
\\]

Negative costs represent “profit” (a benefit) in a minimization form.

## Constraints

### 1) Start choice (one start per slot)

For each start slot `s ∈ S`:

\\[
\\sum_{d \\in Options(s)} x_d = 1
\\]

### 2) Flow balance (time-space conservation)

For each balance node `n ∈ N`:

\\[
\\sum_{d \\in D} a_{n,d} x_d = rhs_n
\\]

Build coefficients `a_{n,d}` as follows:

- For decisions listed in `flow_arcs.csv`:
  - `a_{from(d),d} = +1`
  - `a_{to(d),d} = -1`
- For decisions listed in `flow_exceptions.csv`:
  - add the provided coefficient to the specified node equation.

This encodes multiple disconnected flow components (commodities), consistent with multi-commodity routing/scheduling.

### 3) Package activation (two endpoints when activated)

For each package `p ∈ P`:

\\[
\\sum_{d \\in Cand(p)} x_d = 2\\, x_{pkg(p)}
\\]

Interpretation: activating a block requires selecting exactly two associated boundary/endpoint decisions.

### 4) Window capacity bands (operational pacing)

For each window `w ∈ W` over its member decisions `Members(w)`:

\\[
min_w \\le \\sum_{d \\in Members(w)} x_d \\le max_w
\\]

and a hard cap:

\\[
\\sum_{d \\in Members(w)} x_d \\le cap_w
\\]

### 5) Mix / share limits (policy constraints)

For each mix dimension `k ∈ K` with target `p_k`:

\\[
\\sum_{d \\in V} (flag_{d,k} - p_k)\\, x_d \\le 0
\\]

where `V` is the set of vehicle-side decisions that appear in `mix_flags.csv`.

### 6) Coverage minimums

For each coverage group `g ∈ G`:

\\[
\\sum_{d \\in Members(g)} x_d \\ge minSelected_g
\\]

### 7) Conflicts (choose at most one)

For each conflict group `c ∈ C`:

\\[
\\sum_{d \\in Members(c)} x_d \\le 1
\\]

### 8) Dependencies (prerequisites)

For each parent decision `u` with prerequisite set `Children(u)`:

\\[
x_u \\le \\sum_{v \\in Children(u)} x_v
\\]

### 9) Exact-choice groups

For each exact-choice group `x ∈ X`:

\\[
\\sum_{d \\in Members(x)} x_d = required_x
\\]

These encode small “choose exactly k” decisions (e.g., selecting exactly one of several mutually exclusive alternatives, or selecting exactly two staffing endpoints for a small block).

### 10) Cardinality caps

For each cap group `k ∈ K`:

\\[
\\sum_{d \\in Members(k)} x_d \\le maxSelected_k
\\]

These are operational limits that restrict how many items of a certain type may be simultaneously selected (e.g., limiting the number of special crew transitions, or limiting the number of high-impact vehicle options in a protected subset).

### 11) Redundant bounds (traceability only)

Some source constraints are implied by the binary nature of the decisions and do not affect feasibility. They are listed separately for traceability and can be ignored when rebuilding the optimization model.

## Notes

- All decisions are binary in this instance.
- The file `data/source_mapping.csv` is only for traceability; it is not required to rebuild the model.
