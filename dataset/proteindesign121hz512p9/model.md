# Mathematical Model: Protein Design (Local Choices + Pairwise Choices + Consistency)

## Overview

This instance selects discrete configurations for protein design:

- For each site, choose exactly one local configuration ("rotamer").
- For each interacting site pair, choose exactly one joint configuration (a rotamer pair).
- Enforce consistency between chosen local and joint configurations at each endpoint.
- Minimize total energy (sum of local and pairwise energies).

## Sets

- Sites: \(i \in \mathcal{S}\)
- Pairs: \(p \in \mathcal{P}\) with endpoints \((u(p), v(p))\)
- Rotamers: \(r \in \{0,\dots,R-1\}\)

## Parameters

- \(c^{site}_{i,r}\): energy for site \(i\) choosing rotamer \(r\)
- \(c^{pair}_{p,r,s}\): energy for pair \(p\) choosing rotamer-pair \((r,s)\)

## Variables

- \(x_{i,r} \in \{0,1\}\): 1 if site \(i\) selects rotamer \(r\)
- \(y_{p,r,s} \in \{0,1\}\): 1 if pair \(p\) selects \((r,s)\)

## Objective

\[
\min \sum_{i,r} c^{site}_{i,r} x_{i,r} + \sum_{p,r,s} c^{pair}_{p,r,s} y_{p,r,s}.
\]

## Constraints

1. One rotamer per site:
\[
\sum_{r} x_{i,r} = 1 \quad \forall i
\]

2. One rotamer-pair per interacting pair:
\[
\sum_{r}\sum_{s} y_{p,r,s} = 1 \quad \forall p
\]

3. Consistency for each endpoint:
\[
\sum_{s} y_{p,r,s} = x_{u(p),r} \quad \forall p,\forall r
\]
\[
\sum_{r} y_{p,r,s} = x_{v(p),s} \quad \forall p,\forall s
\]

## Data Mapping

- `data/sites.csv`: site identifiers
- `data/pairs.csv`: pair identifiers and endpoints (ordered as `site_u < site_v`)
- `data/site_options.csv`: local energies \(c^{site}_{i,r}\)
- `data/pair_options.csv`: pairwise energies \(c^{pair}_{p,r,s}\) with `(rot_u, rot_v)` aligned to `(site_u, site_v)`

