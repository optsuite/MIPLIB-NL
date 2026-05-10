# Mathematical Model (Reference): Tight Scheduling With Parity Balance and Paired-Period Reciprocity

This model matches the integrality and linear structure encoded in `acc-tight4.mps`. It extends the `acc-tight2`-style schedule with (i) parity restrictions on even periods and (ii) paired-period coordination rules.

## Indices

- Periods: \(t \in \mathcal{T}\)
- Channels: \(j \in \mathcal{J}\)
- Directed promotion pairs: \((j,u)\) with \(j,u \in \mathcal{J}\), \(j \ne u\), and allowed pairs given by the promotion-requirement data.
- Paired periods: \((t_s, t_d) \in \mathcal{L}\), read from `time_link_pairs.csv` with \(t_s < t_d\).
- Even periods: \(\mathcal{T}_{even} = \{t \in \mathcal{T} \mid t \text{ is even}\}\).

## Decision variables (0–1)

- \(A_{t,j}\): channel \(j\) is the headline in period \(t\)
- \(B_{t,j}\): channel \(j\) is a support host in period \(t\)
- \(P_{t,j,u}\): in period \(t\), channel \(j\) sends a directed promotion into channel \(u\)

## Objective

Minimize discouraged headline placements:
\[
\min \sum_{t \in \mathcal{T}} \sum_{j \in \mathcal{J}} w_{t,j}\, A_{t,j}
\]

## Baseline constraints (shared with acc-tight2)

1) One headline per period:
\[
\sum_{j \in \mathcal{J}} A_{t,j} = 1 \quad \forall t
\]

2) Headline quota per channel:
\[
\sum_{t \in \mathcal{T}} A_{t,j} = q^A_j \quad \forall j
\]

3) Support-host quota per period:
\[
\sum_{j \in \mathcal{J}} B_{t,j} = q^B_t \quad \forall t
\]

4) Exactly one action per \((t,j)\):
\[
A_{t,j} + B_{t,j} + \sum_{u \in \mathcal{J}\setminus\{j\}} P_{t,j,u} = 1 \quad \forall t,j
\]

5) Promotions require the destination to host support:
\[
P_{t,j,u} \le B_{t,u} \quad \forall t,\; \forall j \ne u
\]

6) Promotion counts across the horizon:
\[
\sum_{t \in \mathcal{T}} P_{t,j,u} = r_{j,u} \quad \forall j \ne u
\]

7) At most one incoming promotion per channel per period:
\[
\sum_{j \in \mathcal{J}\setminus\{u\}} P_{t,j,u} \le 1 \quad \forall t,u
\]

8) Cadence rules (window bounds) from `cadence_rules.csv`:
window sums of \(B\), \(A+B\), and \(\sum_u P\) are constrained by either \(\le\) or \(\ge\) bounds.

## Additional constraints (acc-tight4-specific)

9) Even-period parity quotas from `parity_quota.csv`:
\[
\sum_{t \in \mathcal{T}_{even}} A_{t,j} = q^{A,even}_j,\quad
\sum_{t \in \mathcal{T}_{even}} B_{t,j} = q^{B,even}_j
\quad \forall j
\]

10) Paired-period headline linking:
\[
A_{t_s,j} \le A_{t_d,j} \quad \forall (t_s,t_d)\in\mathcal{L},\; \forall j
\]

11) Paired-period promotion reciprocity:
\[
P_{t_s,j,u} \le P_{t_d,u,j} \quad \forall (t_s,t_d)\in\mathcal{L},\; \forall j \ne u
\]

