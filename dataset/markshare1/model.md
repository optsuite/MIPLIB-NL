# Mathematical Model: Market Sharing via Bundle Selection

## Problem Overview

A company operates across multiple regional markets and can acquire a set of pre-defined “bundles” (e.g., contracted package deals). Each bundle, if selected, contributes a fixed number of standardized units to every market (units vary by bundle and market). Each market has a target level that must **not be exceeded**. If the selected bundles do not reach the target in a market, the remaining shortfall is allowed but incurs a per-unit penalty. The goal is to select bundles to minimize total shortfall across markets.

## Sets and Indices

- $\mathcal{M}$: markets, indexed by $m$
- $\mathcal{B}$: bundles, indexed by $b$

## Parameters

- $T_m \ge 0$: target units for market $m$
- $S_{b,m} \ge 0$: units delivered to market $m$ if bundle $b$ is selected
- $w \ge 0$: penalty per unit of unmet target (shortfall)

## Decision Variables

- $x_b \in \{0,1\}$: 1 if bundle $b$ is selected, 0 otherwise
- $u_m \ge 0$: unmet target (shortfall) in market $m$

## Objective Function

Minimize total shortfall penalty:
$$
\min \sum_{m \in \mathcal{M}} w \, u_m.
$$

## Constraints

1. **Target balance with no oversupply**

For each market, the delivered units plus shortfall must equal the target:
$$
\sum_{b \in \mathcal{B}} S_{b,m} x_b + u_m = T_m, \quad \forall m \in \mathcal{M}.
$$

This enforces $\sum_b S_{b,m} x_b \le T_m$ automatically because $u_m \ge 0$.

2. **Variable domains**
$$
x_b \in \{0,1\}, \quad \forall b \in \mathcal{B},
$$
$$
u_m \ge 0, \quad \forall m \in \mathcal{M}.
$$

## Notes on Data Mapping

- $\mathcal{M}$ and $T_m$ come from `data/markets.csv` (`market_id`, `target_units`).
- $\mathcal{B}$ and $S_{b,m}$ come from `data/packages.csv` (`package_id`, and the `market_*` columns).
- $w$ is given in `instance.json` as `penalty_per_unit`.

