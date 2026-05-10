# Reference Model Description (swath1)

This instance describes a radar-surveillance planning problem built from a large catalog of candidate actions. Each action is assigned an activity level. Some actions are commitments (binary), some are bounded shares (0..1), and some are nonnegative quantities without a preset upper limit. Some actions are unavailable and fixed to the minimum level.

## Scoring

The plan is evaluated by an overall mission score computed as a weighted sum of action activity levels. The weights are provided in `data/objective_terms.csv`.

## Operational Rules

All feasibility requirements are expressed as rule families:

- Coverage packages: choose exactly one coverage option per package.
- Configuration packages: choose exactly one configuration option per package.
- Route continuity checkpoints: total entering activity equals total leaving activity per checkpoint.
- Time-window budgets: for each time-window policy, a weighted budget combines (i) the plus time block, (ii) the minus time block, and (iii) a policy-specific coarse-weight companion set.

Coverage and configuration memberships are provided explicitly in CSV. Checkpoint memberships, time blocks, time-window policy pairs, and policy-specific coarse companion sets are generated deterministically from parameters in `instance.json`.

## Data Files

- `data/objective_terms.csv`: Mission score weights for actions.
- `data/coverage_package_options.csv`: Coverage package options.
- `data/configuration_package_options.csv`: Configuration package options.
