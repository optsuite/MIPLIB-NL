# Mathematical Model: Assembly Line Balancing for PCB Production (sct32)

This document is a reference formulation that mirrors the original MPS model. The implementation should read the CSV files described in `instances/sct32/instance.json`.

The structure is the same as `instances/sct2/sct2.md`, with instance-specific sizes and coefficients. In particular:

- Station capacity data is in `data/stations.csv`.
- Allowed routing options and workload are in `data/routing.csv`.
- Checkpoint family 1 is defined by `data/rate_denominators.csv` and `data/rate_contributions.csv`.
- Checkpoint family 2 is defined by `data/budget_meta.csv` and `data/budget_contributions.csv`.
- Checkpoint aggregation weights are in `data/checkpoint_weights.csv`.

Additional internal policy checks are defined by:

- `data/policy_meta.csv`
- `data/policy_contributions.csv`

Both checkpoint families use per-\((variant, checkpoint)\) right-hand-sides and inequality directions (via `sense_id`). Use the convention in `instance.json`: `sense_id = 0` means \"<=\", and `sense_id = 1` means \">=\".
