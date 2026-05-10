# Mathematical Model: Assembly Line Balancing for PCB Production (sct31)

This document is a reference formulation that mirrors the original MPS model. The implementation should read the CSV files described in `instances/sct31/instance.json`.

## Overview

Each production operation selects how its workload is assigned across workstation options. Some options are all-or-nothing, while others allow splitting into fractional shares. The plan must satisfy:

- Station capacity limits (some fixed, some scaling with a staffing proxy).
- A set of internal checkpoint rules evaluated across multiple variants.
- A small global budget of discretionary “priority” activations, which can neutralize the family-2 burden of certain discrete routing choices.
- A small set of additional policy checks that enforce minimum/maximum aggregated requirements over selected discrete choices.

## Sets and data

- Operations: \(i \\in \\mathcal{I}\)
- Stations: \(s \\in \\mathcal{S}\)
- Variants: \(v \\in \\mathcal{V}\)
- Checkpoints: \(k \\in \\mathcal{K}\)
- Policy checks: \(p \\in \\mathcal{P}\)

All sets and coefficients are provided via the CSV files listed in `instances/sct31/instance.json`.

## Decision quantities (conceptual)

- Routing share \(x_{i,s}\\): share of operation \(i\) assigned to station option \(s\). Discrete options are binary; splittable options are continuous in \([0,1]\).
- Staffing proxy \(u\\): a nonnegative scalar that expands capacity for certain stations.
- Checkpoint indicators \(r_{v,k}\\) and \(q_{v,k}\\): real-valued checkpoint indicators for family 1 and family 2.
- Summary indicators \(m\\), \(R_1\\), \(R_2\\): a minimum-of-family-1 indicator and two weighted aggregates.
- Priority activation \(y_{i,s}\\): a binary activation available only for eligible discrete routing choices; the total number of activations is limited.

## Core constraints

### Operation completion
\nFor each operation \(i\), the routed shares across available options sum to one:
\n\\[ \\sum_{s \\in \\mathcal{S}(i)} x_{i,s} = 1. \\]

### Station capacity

For each station \(s\), the total workload induced by assigned shares cannot exceed its usable capacity (fixed base plus an optional staffing expansion):
\n\\[ \\sum_{i} \\text{workload}_{i,s} \\, x_{i,s} \\le \\text{base}_s + \\text{crew}_s \\, u. \\]

### Priority budget and activation

Eligible discrete routing choices may have a binary priority activation \(y_{i,s}\\). Activations are optional but limited:
\n\\[ y_{i,s} \\le x_{i,s}, \\qquad \\sum_{(i,s)} y_{i,s} \\le \\text{priority\\_budget}. \\]

### Policy checks

Each policy check \(p\\) defines an aggregate linear expression over selected discrete routing choices and compares it to a right-hand side using a per-policy inequality direction:
\n\\[ \\sum_{(i,s)} \\alpha_{p,i,s} \\, x_{i,s} \\;\\le/\\ge\\; \\text{rhs}_p. \\]

## Checkpoint families

Both checkpoint families define one rule per \((v,k)\). The rule direction is given by `sense_id` (0 for “<=”, 1 for “>=”).

### Family 1 (rate-style)
\n\\[ \\sum_{(i,s)} a_{v,k,i,s} \\, x_{i,s} - d_{v,k} \\, r_{v,k} \\;\\le/\\ge\\; \\text{rhs}^{(1)}_{v,k}. \\]

### Family 2 (budget-style with priority relief)
\n\\[ b_{v,k} \\, q_{v,k} + \\sum_{(i,s)} c_{v,k,i,s} \\, x_{i,s} - \\sum_{(i,s) \\in \\text{eligible}} c_{v,k,i,s} \\, y_{i,s} \\;\\le/\\ge\\; \\text{rhs}^{(2)}_{v,k}. \\]

## Summary indicators and objective

- \(m\\) is bounded by every \(r_{v,k}\\) and is incentivized upward.
- \(R_1\\) and \(R_2\\) are bounded by weighted sums of the checkpoint indicators and are incentivized upward.

The objective is a weighted balance of staffing penalty, checkpoint summaries, and a discrete-routing score computed from eligible discrete routing choices.
