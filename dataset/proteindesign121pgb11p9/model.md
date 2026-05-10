# Mathematical Model: Protein Design (Rotamer Selection with Pairwise Interactions)

## Problem Overview

This instance selects discrete local configurations ("rotamers") for a set of interacting protein sites.

- At each **site**, exactly one rotamer must be selected.
- For each **interacting pair** of sites, exactly one rotamer-pair must be selected.
- Site selections and pair selections must be **consistent**: the rotamer chosen for a pair must match the rotamer chosen at each endpoint site.
- Each site option and pair option has an associated **energy** (cost). The objective is to minimize total energy.

## Sets

- Sites: \(i \in \mathcal{S}\)
- Interacting pairs: \(p \in \mathcal{P}\), with endpoints \((i(p), j(p))\)
- Rotamers: \(r \in \{0,\dots,R-1\}\)

## Parameters

- \(c^{site}_{i,r}\): energy for selecting rotamer \(r\) at site \(i\)
- \(c^{pair}_{p,r,s}\): energy for selecting rotamer-pair \((r,s)\) for pair \(p\)

All parameter values are provided in the CSV data files.

## Decision Variables

- \(x_{i,r} \in \{0,1\}\): 1 if site \(i\) selects rotamer \(r\)
- \(y_{p,r,s} \in \{0,1\}\): 1 if pair \(p\) selects rotamer-pair \((r,s)\)

## Objective

\[
\min \sum_{i \in \mathcal{S}}\sum_{r} c^{site}_{i,r}\,x_{i,r} \;+\;
\sum_{p \in \mathcal{P}}\sum_{r}\sum_{s} c^{pair}_{p,r,s}\,y_{p,r,s}.
\]

## Constraints

### 1) One rotamer per site
\[
\sum_{r} x_{i,r} = 1,\quad \forall i \in \mathcal{S}.
\]

### 2) One rotamer-pair per interacting pair
\[
\sum_{r}\sum_{s} y_{p,r,s} = 1,\quad \forall p \in \mathcal{P}.
\]

### 3) Consistency between site and pair selections
For every pair \(p\) with endpoints \(i=i(p)\) and \(j=j(p)\):
\[
\sum_{s} y_{p,r,s} = x_{i,r},\quad \forall r
\]
\[
\sum_{r} y_{p,r,s} = x_{j,s},\quad \forall s
\]

## Data Mapping

- `data/sites.csv`: defines sites \(\mathcal{S}\)
- `data/pairs.csv`: defines interacting pairs \(\mathcal{P}\) and endpoints
- `data/site_options.csv`: provides \(c^{site}_{i,r}\)
- `data/pair_options.csv`: provides \(c^{pair}_{p,r,s}\)

