# Mathematical Model: Cost-Minimal Action Selection with Menu Limits and Target Requirements

## Overview

This instance models how to choose a low-cost bundle from many candidate actions. Each action has a cost and can be either adopted or not. The chosen bundle must satisfy:

- **Menu limits**: actions are partitioned into menus (groups); each menu allows selecting at most a fixed number of actions (given at the instance level).
- **Target requirements**: each adopted action contributes to one or more organization-wide targets; for every target, the total contribution from selected actions must meet or exceed the required level.

All data needed to rebuild the model is provided in the CSV files under `data/`.

## Sets

- Actions: \(j \in \mathcal{A}\)
- Menus (groups): \(g \in \mathcal{G}\)
- Targets: \(t \in \mathcal{T}\)

## Decision variables

- \(y_j \in \{0,1\}\): whether action \(j\) is adopted

## Parameters

- \(c_j\): cost of action \(j\) (from `options.csv`)
- \(\text{req}_t\): required level for target \(t\) (from `resources.csv`)
- \(a_{tj}\): contribution of action \(j\) to target \(t\) (from `resource_usage.csv`; omitted pairs are zero)
- \(g(j)\): menu assigned to action \(j\) (from `option_requirement.csv`)
- \(K\): maximum number of actions selectable per menu (from `instance.json` parameters)

## Objective

Minimize total cost:
\[
\min \sum_{j \in \mathcal{A}} c_j y_j
\]

## Constraints

### 1) Menu limits (one constraint per menu)
\[
\sum_{j \in \mathcal{A}: g(j)=g} y_j \;\le\; K \qquad \forall g \in \mathcal{G}
\]

### 2) Target requirements (one constraint per target)
\[
\sum_{j \in \mathcal{A}} a_{tj} y_j \;\ge\; \text{req}_t \qquad \forall t \in \mathcal{T}
\]

## Data mapping

- `data/options.csv`: provides action IDs and costs \(c_j\)
- `data/requirements.csv`: provides menu IDs \(g\)
- `data/option_requirement.csv`: maps each action to exactly one menu \(g(j)\)
- `data/resources.csv`: provides target IDs and required levels \(\text{req}_t\)
- `data/resource_usage.csv`: provides nonzero contributions \(a_{tj}\)
