# Mathematical Model (Reference): Tight Multi-Channel Scheduling With Cross-Channel Promotions

This instance is a tightly constrained schedule over a grid of periods and channels. In every (period, channel) cell, exactly one action is chosen: headline, hosting support, or sending a directed cross-channel promotion to a different channel. Cross-channel promotions can only be received by channels that host support in that period, and each channel can receive at most one incoming promotion per period.

The model below is written as a 0–1 integer program, matching the integrality encoded in the MPS.

## Indices

- Periods: \(t \in \{1,\dots,T\}\)
- Channels: \(j \in \{1,\dots,J\}\)
- Directed promotion pairs: \((j,u)\) with \(j,u \in \{1,\dots,J\}\) and \(j \ne u\)

## Decision variables (0–1)

- \(A_{t,j} \in \{0,1\}\): channel \(j\) is the headline in period \(t\)
- \(B_{t,j} \in \{0,1\}\): channel \(j\) is a support host in period \(t\)
- \(P_{t,j,u} \in \{0,1\}\): in period \(t\), channel \(j\) sends a directed promotion into channel \(u\) (\(j \ne u\))

## Objective

Minimize a single discouraged headline placement:
\[
\min \; A_{t^\*, j^\*}
\]

## Core constraints

### 1) Exactly one headline channel per period
\[
\sum_{j=1}^{J} A_{t,j} = 1 \quad \forall t
\]

### 2) Headline quota per channel (over the whole horizon)
\[
\sum_{t=1}^{T} A_{t,j} = q^{A}_{j} \quad \forall j
\]

### 3) Exactly a fixed number of support hosts per period
\[
\sum_{j=1}^{J} B_{t,j} = q^{B}_{t} \quad \forall t
\]

### 4) Exactly one action per (period, channel)
\[
A_{t,j} + B_{t,j} + \sum_{\substack{u=1\\u\ne j}}^{J} P_{t,j,u} = 1 \quad \forall t,j
\]

### 5) Promotions require the destination to host support (same period)
\[
P_{t,j,u} \le B_{t,u} \quad \forall t,\; \forall j \ne u
\]

### 6) Each directed channel pair is used exactly once across periods
\[
\sum_{t=1}^{T} P_{t,j,u} = r_{j,u} \quad \forall j \ne u
\]

### 7) At most one incoming promotion per channel per period
\[
\sum_{\substack{j=1\\j\ne u}}^{J} P_{t,j,u} \le 1 \quad \forall t,u
\]

## Cadence constraints (tightness rules)

The instance includes additional time-window constraints that prevent a channel from being too dense or too sparse in its support hosting over time, and similar window rules that couple headline and hosting actions. These are provided as data rows in `data/cadence_rules.csv` and can be expressed generically as:

- target \(=\) `B`: window sums of \(B_{t,j}\)
- target \(=\) `AB`: window sums of \(A_{t,j} + B_{t,j}\)
- target \(=\) `Csum`: window sums of \(\sum_{u \ne j} P_{t,j,u}\)

with either an upper bound (\(\le\)) or a lower bound (\(\ge\)) on each window sum.

