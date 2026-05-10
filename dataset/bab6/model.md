# Mathematical Model (Structured): Vehicle Routing with Profits + Integrated Crew Scheduling (bab6)

This instance represents a planning problem where a company selects a consistent set of binary choices to:

- operate vehicle-side movements / service transitions (incurring costs or earning profit credits),
- operate crew-side linkages / transitions so that selected vehicle operations can be legally covered,

while maintaining internal network consistency and policy rules.

The data files in `data/` provide a compact representation that lets you rebuild the original MPS model without relying on MPS naming.

## Sets

- **Decisions** `D`: binary choices (transitions, options, or auxiliary selections).
- **Start slots** `S`: independent start requirements; each requires exactly one option.
- **Flow nodes** `N`: balance equations in a time-space network representation.
- **Windows** `W`: activity windows that bound how many selected transitions can occur in that window (min/max, plus optional hard cap).
- **Mix dimensions** `M`: policy dimensions limiting how concentrated certain attributes may be among selected decisions.
- **Coverage groups** `G`: groups requiring at least a minimum number of selected decisions.
- **Conflict groups** `C`: groups where at most one member decision may be selected.
- **Dependency rules** `R`: prerequisite links: selecting a parent requires selecting at least one child.
- **Guarded groups** `H`: group activation guards: the number of selected members is limited by a designated gate decision.
- **Cardinality caps** `K`: groups with an upper bound on how many members may be selected.

## Decision variables

For each `d ∈ D`:

- `x_d ∈ {0,1}`: whether the choice is selected.

## Parameters (from data files)

- `cost_d`: objective coefficient for each decision.
- Start-slot membership: which decisions are valid options for each slot.
- Flow balance coefficients:
  - Standard arc representation via `(from_node(d), to_node(d))`.
  - Additional node coefficients for exceptional decisions.
- Window membership and window bounds (min/max/hard cap).
- Mix targets and per-decision binary attribute flags.
- Coverage minimums and membership.
- Conflict membership.
- Dependency edges.
- Guarded-group membership and gate decision.
- Cardinality-cap membership and limits.

## Objective

Minimize total net cost:

\[
\min \sum_{d \in D} cost_d\, x_d
\]

Negative costs represent profit credits in a minimization form.

## Constraints

### 1) Start choice (one start per slot)

For each start slot `s ∈ S`:

\[
\sum_{d \in Options(s)} x_d = 1
\]

### 2) Flow balance (time-space conservation)

For each flow node `n ∈ N`:

\[
\sum_{d \in D} a_{n,d}\, x_d = rhs_n
\]

Build coefficients as follows:

- For decisions listed in `flow_arcs.csv`:
  - `a_{from(d),d} = +1`
  - `a_{to(d),d} = -1`
- For decisions listed in `flow_exceptions.csv`:
  - add the provided coefficient to the specified node equation.

### 3) Window pacing (min/max band + optional hard cap)

For each window `w ∈ W` over member decisions `Members(w)`:

\[
min_w \le \sum_{d \in Members(w)} x_d \le max_w
\]

and optionally:

\[
\sum_{d \in Members(w)} x_d \le hardCap_w
\]

### 4) Mix / share limits (policy constraints)

For each mix dimension `m ∈ M` with target `p_m`:

\[
\sum_{d \in D} (flag_{d,m} - p_m)\, x_d \le 0
\]

### 5) Coverage minimums

For each coverage group `g ∈ G`:

\[
\sum_{d \in Members(g)} x_d \ge minSelected_g
\]

### 6) Conflicts (choose at most one)

For each conflict group `c ∈ C`:

\[
\sum_{d \in Members(c)} x_d \le 1
\]

### 7) Dependencies (prerequisites)

For each parent decision `u` with prerequisite set `Children(u)`:

\[
x_u \le \sum_{v \in Children(u)} x_v
\]

### 8) Guarded groups (activation guards)

For each guarded group `h ∈ H` with gate decision `gate(h)`:

\[
\sum_{d \in Members(h)} x_d \le x_{gate(h)}
\]

### 9) Cardinality caps

For each cap group `k ∈ K`:

\[
\sum_{d \in Members(k)} x_d \le maxSelected_k
\]

## Notes

- All decisions are modeled as binary in the reconstructed model; in the source MPS they are integer with bounds \([0,1]\), which is equivalent.
- The file `data/source_mapping.csv` is only for traceability; it is not required to rebuild the model.

