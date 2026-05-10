# Congestion-Minimizing Lane Commitment and Routing

## Business interpretation

Consider a company that needs to prepare an operations plan for a fixed planning window (e.g., the next week). It must decide how to allocate limited linehaul capacity between regional sites by activating a set of candidate directed service lanes (think “scheduled shuttles” from one site to another).

Each lane has an activation amount that represents how much standardized capacity is committed to that lane for the window:

- Activation = 1 means one full standard capacity block is reserved for that lane (for example, one contracted shuttle, one full truck-equivalent, or one full container-equivalent allocation).
- A fractional activation represents reserving only that fraction of the standard block (for example, shared equipment, partial booking, or fewer departures).

Some activation decisions are modeled as discrete (integer) commitments and others may be fractional, which matches the fact that the source dataset labels this instance as a relaxation.

The company moves multiple independent product streams. A product stream is a group of shipments that must be planned separately (for example because they belong to different customers, product lines, or handling classes). Each stream is injected at a designated origin site and has net receipt requirements at the other sites. A net receipt requirement is defined as:

> (total units received into the site) − (total units forwarded out of the site) over the planning window.

This definition allows transshipment: a site may receive some units and forward some units onward, as long as the net difference matches the requirement.

Operationally, the company wants:

1. Simplicity and resilience: each site commits to a fixed number of outgoing lanes and a fixed number of incoming lanes.
2. Low congestion: avoid any single lane becoming a bottleneck. Congestion is measured as the maximum, over all lanes, of the total shipped volume on that lane when summing across all product streams.

The optimization chooses lane activations and stream routing to satisfy all net receipts while minimizing the congestion indicator.

## Data mapping

This instance is described by `instance.json` and the CSV files in `data/`:

- `nodes.csv`: sites
- `commodities.csv`: product streams and their origin sites
- `arcs.csv`: candidate directed lanes and their activation types/bounds
- `degree_requirements.csv`: required incoming/outgoing lane counts per site
- `demands.csv`: net receipt requirements (net inflow) per (stream, site)
- `capacity_multipliers.csv`: per-unit-activation carrying capability per (stream, lane)

## Reference optimization model

### Sets

- Sites: \(n \in \mathcal{N}\)
- Directed lanes: \(a \in \mathcal{A}\), each with endpoints \(\mathrm{from}(a)\), \(\mathrm{to}(a)\)
- Product streams: \(k \in \mathcal{K}\), each with an origin site \(\mathrm{src}(k)\)
- Eligible lane usage pairs: \((k,a) \in \mathcal{E}\) (rows present in `capacity_multipliers.csv`)

### Parameters

- Required lane counts: \(d^{out}_n\), \(d^{in}_n\) from `degree_requirements.csv`
- Lane activation bounds: \(\underline{x}_a, \overline{x}_a\) from `arcs.csv`
- Per-unit-activation carrying capability: \(u_{k,a} \ge 0\) from `capacity_multipliers.csv`
- Net receipt requirements (net inflow): \(b_{k,n}\) from `demands.csv` (origin sites are typically omitted)

### Decision variables

- Lane activation: \(x_a\) (integer or continuous as specified in `arcs.csv`)
- Routed volume: \(f_{k,a} \ge 0\) for \((k,a)\in\mathcal{E}\)
- Total lane volume: \(F_a \ge 0\) for \(a\in\mathcal{A}\)
- Congestion indicator: \(z \ge 0\)

### Core relationships

Lane-count requirements at each site:

\[
\sum_{a\in\mathcal{A}:\,\mathrm{from}(a)=n} x_a = d^{out}_n \quad \forall n\in\mathcal{N}
\]
\[
\sum_{a\in\mathcal{A}:\,\mathrm{to}(a)=n} x_a = d^{in}_n \quad \forall n\in\mathcal{N}
\]

Total lane volume as the sum over streams:

\[
F_a = \sum_{k:\,(k,a)\in\mathcal{E}} f_{k,a} \quad \forall a\in\mathcal{A}
\]

Congestion indicator upper-bounds every lane:

\[
F_a \le z \quad \forall a\in\mathcal{A}
\]

Per-stream carrying capability tied to activation:

\[
f_{k,a} \le u_{k,a}\,x_a \quad \forall (k,a)\in\mathcal{E}
\]

Net receipts at sites (flow conservation with signed right-hand side):

For each stream \(k\) and each non-origin site \(n \ne \mathrm{src}(k)\):

\[
\sum_{a:\,\mathrm{to}(a)=n,\,(k,a)\in\mathcal{E}} f_{k,a}
- \sum_{a:\,\mathrm{from}(a)=n,\,(k,a)\in\mathcal{E}} f_{k,a}
= b_{k,n}
\]

The origin site is omitted, meaning its net export is whatever is needed to satisfy the net receipts elsewhere.

### Objective

\[
\min z
\]

## Notes

- `solver.py` implements this model from the CSV files and optionally checks the objective value against `bienst2.mps`.
- The source dataset labels this instance as a relaxation, which is why some lane activations are continuous rather than discrete.

