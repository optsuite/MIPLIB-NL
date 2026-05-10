# Mathematical Model (Structured): Vehicle Routing with Profits + Integrated Crew Scheduling

This instance follows the same structured representation as `bab5`: a binary optimization model that can be viewed as **two coupled multi-commodity flow problems** (vehicle-side routing with profits + crew-side scheduling), with additional operational policies.

The model is rebuilt from `data/*.csv` and does not rely on the original MPS naming.

## Sets

- `D`: binary decisions (selecting a transition, a block-opening choice, or an auxiliary linkage).
- `S`: start slots (each must select exactly one option).
- `N`: flow balance nodes (time-space equations for vehicle and crew streams).
- `P`: packages (when opened, require selecting exactly two associated boundary choices).
- `W`: pacing windows (each bounds how many vehicle-side choices are activated in that window).
- `K`: mix dimensions (share-limit policy constraints).
- `G`: coverage groups (minimum selected in a group).
- `C`: conflict groups (at most one selected in a group).
- `R`: prerequisite rules (a selected choice must be supported by at least one continuation).
- `Kcap`: cardinality-cap groups (upper bounds on how many members may be selected).
- `X`: exact-choice groups (may be empty for some instances).

## Variables

- For each `d ∈ D`, `x_d ∈ {0,1}` indicates whether the decision is selected.

## Objective

Minimize net cost (negative costs represent profit credits):

\\[
\\min \\sum_{d \\in D} cost_d\\, x_d
\\]

## Constraints

### 1) Start choices

For each start slot `s ∈ S`:
\\[
\\sum_{d \\in Options(s)} x_d = 1
\\]

### 2) Flow balance (time-space conservation)

For each node `n ∈ N`:
\\[
\\sum_{d \\in D} a_{n,d} x_d = rhs_n
\\]

Coefficients are built from:
- `flow_arcs.csv`: standard directed-transition pattern (`+1` at origin node, `-1` at destination node).
- `flow_exceptions.csv`: explicit coefficients for non-standard transitions.

### 3) Package anchoring (two boundary choices)

For each package `p ∈ P`:
\\[
\\sum_{d \\in Cand(p)} x_d = 2\\, x_{open(p)}
\\]

### 4) Window pacing

For each window `w ∈ W`:
\\[
min_w \\le \\sum_{d \\in Members(w)} x_d \\le max_w
\\]
and
\\[
\\sum_{d \\in Members(w)} x_d \\le hardCap_w
\\]

### 5) Mix / share limits

For each dimension `k ∈ K` with target `p_k`:
\\[
\\sum_{d \\in V} (flag_{d,k} - p_k)\\, x_d \\le 0
\\]

where `V` is the set of decisions listed in `mix_flags.csv`.

### 6) Coverage minimums

For each coverage group `g ∈ G`:
\\[
\\sum_{d \\in Members(g)} x_d \\ge minSelected_g
\\]

### 7) Conflicts

For each conflict group `c ∈ C`:
\\[
\\sum_{d \\in Members(c)} x_d \\le 1
\\]

### 8) Prerequisites

For each prerequisite parent choice `u`:
\\[
x_u \\le \\sum_{v \\in Children(u)} x_v
\\]

### 9) Cardinality caps

For each cap group `kcap ∈ Kcap`:
\\[
\\sum_{d \\in Members(kcap)} x_d \\le maxSelected_{kcap}
\\]

### 10) Exact-choice groups (optional)

For each exact-choice group `x ∈ X`:
\\[
\\sum_{d \\in Members(x)} x_d = required_x
\\]

## Notes

- All variables are binary in this instance.
- `data/source_mapping.csv` is optional and only for traceability back to the MPS.

