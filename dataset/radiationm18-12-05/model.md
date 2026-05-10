# Mathematical Model: Intensity-Modulated Radiation Therapy Field Decomposition

## Problem Overview

This model describes the IMRT (intensity-modulated radiation therapy) field decomposition problem used in the MiniZinc
Challenges and linearized for MIPLIB. A rectangular treatment field is discretized into an $M \times N$ grid of cells.
For each cell $(i,j)$, an integer value $\text{Intensity}_{i,j}$ specifies the total amount of radiation exposure that
cell should receive. A treatment plan consists of a multiset of beam segments (also called shape matrices). Each segment
is delivered for a certain beam-on time $b$ and corresponds to a binary $M \times N$ pattern with the consecutive-ones
property: in each row, all exposed cells (1s) form a single contiguous interval, while 0s represent cells blocked by
the multi-leaf collimator.

When a segment with beam-on time $b$ is used once, every exposed cell in that segment receives $b$ units of exposure.
By repeatedly using segments with possibly different beam-on times, the accumulated exposure at each cell must equal
its prescribed intensity. The optimization objective is lexicographic: first minimize the total beam-on time, and then
the total number of used segments.

The instances `radiationm18-12-05` and `radiationm40-10-02` differ only in the size and numerical values of the
intensity matrix.

## Sets and Indices

- $\mathcal{R} = \{1,\dots,M\}$: set of rows (indexed by $i$)
- $\mathcal{C} = \{1,\dots,N\}$: set of columns (indexed by $j$)
- $\mathcal{B} = \{1,\dots,B_{\max}\}$: set of possible beam-on times (indexed by $b$)

In the original MiniZinc model, $B_{\max}$ can be chosen as the maximum intensity value in the matrix.

## Parameters

- $\text{Intensity}_{i,j} \in \mathbb{Z}_{\ge 0}$: required total exposure for cell $(i,j)$.
- $B_{\max} \in \mathbb{Z}_{\ge 1}$: maximum beam-on time considered.

## Decision Variables

- $\text{Beamtime} \in \mathbb{Z}_{\ge 0}$: total beam-on time in the treatment plan.
- $K \in \mathbb{Z}_{\ge 0}$: total number of segments (shape matrices) used.
- $N_b \in \mathbb{Z}_{\ge 0}$ for all $b \in \mathcal{B}$: number of segments with beam-on time $b$.
- $Q_{i,j,b} \in \mathbb{Z}_{\ge 0}$ for all $i \in \mathcal{R}$, $j \in \mathcal{C}$, $b \in \mathcal{B}$:
  number of segments with beam-on time $b$ that expose cell $(i,j)$.

In the MiniZinc model, the consecutive-ones property for each row and beam-on time is enforced using a dedicated
predicate over the array $Q_{i,*,b}$. The MIPLIB MPS instances correspond to a linearization of this model and
introduce additional auxiliary variables and constraints. For the purpose of understanding the underlying application,
$Q_{i,j,b}$ can be interpreted as above.

## Objective Function

The intended objective is lexicographic: minimize total beam-on time first, then the total number of segments.
This can be modeled as a single linear objective with a sufficiently large weight:

\[
  \min \; (M \cdot N + 1) \cdot \text{Beamtime} + K.
\]

Because $K \le M \cdot N$ in any feasible solution, the coefficient $(M \cdot N + 1)$ ensures that any reduction in
Beamtime dominates any change in $K$.

## Constraints

### 1. Definition of total beam-on time

The total beam-on time is the sum of the beam-on times of all segments:

\[
  \text{Beamtime} = \sum_{b \in \mathcal{B}} b \cdot N_b.
\]

### 2. Definition of number of segments

The total number of segments $K$ is the sum over all beam-on times:

\[
  K = \sum_{b \in \mathcal{B}} N_b.
\]

### 3. Intensity matching for each cell

For every cell $(i,j)$, the sum of exposures delivered by all segments that expose it must equal the prescribed
intensity:

\[
  \forall i \in \mathcal{R}, \forall j \in \mathcal{C}:
  \quad \text{Intensity}_{i,j}
  = \sum_{b \in \mathcal{B}} b \cdot Q_{i,j,b}.
\]

Here, $Q_{i,j,b}$ plays the role of "how many times" a segment with beam-on time $b$ and exposing $(i,j)$ is used.

### 4. Consecutive-ones property (row-wise shape constraints)

For each row $i$ and beam-on time $b$, the set of columns $j$ such that cell $(i,j)$ is exposed by at least one
segment with beam-on time $b$ must form a single contiguous interval. In the MiniZinc model, this is enforced by the
predicate `upper_bound_on_increments` applied to the sequence $(Q_{i,1,b}, \dots, Q_{i,N,b})$:

\[
  \forall i \in \mathcal{R}, \forall b \in \mathcal{B}:
  \quad N_b \ge Q_{i,1,b} + \sum_{j=2}^N \max\bigl(0, Q_{i,j,b} - Q_{i,j-1,b}\bigr).
\]

Intuitively, the right-hand side counts the number of times the exposure level increases along the row, and bounding
this by $N_b$ ensures that, across all segments with beam-on time $b$, each row can be represented as a union of at
most $N_b$ contiguous blocks.

In the MIPLIB instances this predicate is fully linearized using additional binary and integer variables; however, the
logical effect is to restrict segments to patterns with the consecutive-ones property.

## Summary

- Data files `data/intensity.csv` and `data/parameters.csv` specify the grid size and required intensity pattern.
- The decision variables describe how many segments of each beam-on time are used and how they expose each cell.
- Constraints ensure that total beam-on time and number of segments match $N_b$, that each cell's required intensity
  is satisfied exactly, and that each segment pattern respects the consecutive-ones property in every row.
- The objective corresponds to minimizing total beam-on time first and then the number of segments, matching the
  intent of the original MiniZinc radiation model whose linearization produced the MIPLIB instances.
