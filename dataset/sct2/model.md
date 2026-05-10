# Mathematical Model: Assembly Line Balancing for PCB Production (sct2)

This document is a reference formulation that mirrors the original MPS model. The implementation should read the CSV files described in `instances/sct2/instance.json`.

## Sets and indices

- Operations: \(i \in \mathcal{I}\)
- Station options: \(s \in \mathcal{S}\)
- Variants: \(v \in \mathcal{V}\)
- Checkpoints: \(k \in \mathcal{K}\)

## Decision variables

- Routing share \(a_{i,s}\) for each allowed \((i,s)\):
  - Discrete lanes: \(a_{i,s} \in \{0,1\}\)
  - Splittable lanes: \(0 \le a_{i,s} \le 1\)
- Priority use \(p_{i,s} \in \{0,1\}\) for eligible discrete options \((i,s)\)
- Staffing proxy \(u \ge 0\) (crew units)
- Checkpoint indicators:
  - Family 1: \(r_{v,k}\)
  - Family 2: \(q_{v,k}\)
- Aggregators (as in the MPS):
  - \(m\) (minimum of family-1 indicators)
  - \(R_1\), \(R_2\) (weighted sums of \(r\) and \(q\))

All checkpoint indicators are bounded above by \(\overline{r}\) from `instance.json` (`checkpoint_upper_bound`).

## Parameters and data sources

- Station capacities and staffing responsiveness: `data/stations.csv`
  - Base capacity \(\bar{W}_s\)
  - Increment per crew unit \(\alpha_s\)
- Allowed routing options: `data/routing.csv`
  - Workload units \(w_{i,s}\)
  - Discrete score \(g_{i,s}\) (only for discrete options; empty otherwise)
  - Eligibility flag for priority tokens
- Checkpoint weights \(\omega_k\): `data/checkpoint_weights.csv`

Checkpoint family 1 (rate-style):

- Metadata by \((v,k)\): `data/rate_denominators.csv`
  - Scaling coefficient \(d_{v,k}\)
  - Right-hand-side and inequality direction (via `sense_id`)
- Sparse contributions: `data/rate_contributions.csv`
  - Coefficients \(A_{v,k,i,s}\)

Checkpoint family 2 (budget-style with priority relief):

- Metadata by \((v,k)\): `data/budget_meta.csv`
  - Checkpoint coefficient \(\beta_{v,k}\)
  - Right-hand-side and inequality direction (via `sense_id`)
- Sparse contributions: `data/budget_contributions.csv`
  - Coefficients \(C_{v,k,i,s}\)

Additional policy checks:

- Metadata by requirement id: `data/policy_meta.csv`
  - Right-hand-side and inequality direction (via `sense_id`)
- Sparse contributions: `data/policy_contributions.csv`
  - Coefficients over selected routing choices

## Objective (structure)

The original MPS objective is a linear combination of:

- Staffing penalty: \(c_u \, u\)
- Incentives for larger checkpoint indicators and aggregations:
  - \(-c_m \, m\), \(-c_1 \, R_1\), \(-c_2 \, R_2\)
- Discrete routing score incentive:
  - \(-c_a \sum g_{i,s} a_{i,s}\) over discrete options

The scalar weights are exposed in `instance.json` parameters.

## Constraints (core families)

1) Operation completion (one choice per operation):
\[
\sum_{s \in \mathcal{S}(i)} a_{i,s} = 1,\quad \forall i \in \mathcal{I}.
\]

2) Station capacity (with optional staffing expansion):
\[
\sum_{i \in \mathcal{I}} w_{i,s} a_{i,s} \le \bar{W}_s + \alpha_s u,\quad \forall s \in \mathcal{S}.
\]

3) Priority activation and global budget:
\[
p_{i,s} \le a_{i,s},\quad \forall (i,s)\ \text{eligible},
\qquad
\sum p_{i,s} \le B.
\]

4) Minimum checkpoint definition (family 1):
\[
m \le r_{v,k},\quad \forall v,k.
\]

5) Aggregation definitions:
\[
R_1 \le \sum_{v,k} \omega_k r_{v,k},
\qquad
R_2 \le \sum_{v,k} \omega_k q_{v,k}.
\]

6) Checkpoint family 1 rules:

For each \((v,k)\), take the sign and direction from `rate_denominators.csv` (`sense_id`) and use:

- The scaling coefficient on \(r_{v,k}\)
- The constant right-hand-side
- The contributions \(A_{v,k,i,s}\) from `rate_contributions.csv`

7) Checkpoint family 2 rules with priority relief:

For each \((v,k)\), take the sign and direction from `budget_meta.csv` (`sense_id`) and use:

- The checkpoint coefficient on \(q_{v,k}\)
- The constant right-hand-side
- Contributions \(C_{v,k,i,s}\) from `budget_contributions.csv`, applied to \((a_{i,s} - p_{i,s})\) for eligible discrete options

The relief structure matches the original MPS: applying priority removes the corresponding contribution from this checkpoint family.
