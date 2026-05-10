# Reference Model Description (swath2)

This instance describes a radar-surveillance planning problem built from a large catalog of candidate actions. Each action is assigned an activity level (how strongly the action is used). Some actions are binary commitments (used or not used), some are bounded effort shares, and a small set are nonnegative quantities without a preset upper limit. A subset of actions is unavailable in this specific instance and is fixed to its minimum level.

## Scoring

The plan is evaluated by an overall mission score computed as a weighted sum of action levels. The weights are provided in `data/objective_terms.csv`.

## Operational Rules

All feasibility requirements are expressed as rule families:

- Coverage packages: choose exactly one coverage option per package.
- Configuration packages: choose exactly one configuration option per package.
- Route continuity checkpoints: total entering activity equals total leaving activity per checkpoint.
- Time-window budgets: for each time-window policy, a weighted budget combines (i) the plus time block, (ii) the minus time block, and (iii) a policy-specific coarse-weight companion set.

Coverage and configuration memberships are provided explicitly in CSV. Checkpoint memberships, time blocks, time-window policy pairs, and policy-specific coarse companion sets are generated deterministically from parameters in `instance.json`.

## Data Files

- `data/objective_terms.csv`: Defines the mission score weights for actions.
- `data/coverage_package_options.csv`: Coverage package options.
- `data/configuration_package_options.csv`: Configuration package options.

## Generator Parameters

All other model structure is specified in `instances/swath2/instance.json` under `parameters` (action domains, availability structure, and generator parameters for coverage, configuration, route continuity, and time-window budgets).
