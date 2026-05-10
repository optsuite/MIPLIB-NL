# Reference Model Answer: Orientation Harmonization with Pairwise Evidence

## Business Interpretation

Each entity has an unknown binary reference orientation relative to a shared convention. Evidence statements describe how pairs of entities should relate *after* harmonization:

- **co-move**: the pair is expected to have the same orientation
- **counter-move**: the pair is expected to have opposite orientations

If the chosen orientations make an evidence statement incompatible, a penalty equal to its weight is incurred.

## Sets and Indices

- Let \(V\) be the set of entities (`entities.csv`), indexed by \(v\).
- Let \(E\) be the set of evidence records (`evidence.csv`), indexed by \(e\).

For each evidence record \(e\), denote:

- endpoints \((u_e, v_e)\)
- expected parity \(r_e \in \{\text{same}, \text{opposite}\}\)
- weight \(w_e \ge 0\)

The expected parity \(r_e\) is not stored directly in `evidence.csv`. It must be derived by looking up the pair (`effect_type`, `agreement_domain`) in `evidence_semantics.csv`.

## Decision Variables

- \(s_v \in \{0,1\}\) for each entity \(v \in V\)  
  (the chosen reference orientation)
- \(z_e \in \{0,1\}\) for each evidence \(e \in E\)  
  (\(z_e = 1\) if evidence \(e\) is incompatible with the chosen orientations, else \(0\))

## Objective

Minimize the total incompatibility penalty:
\[
\min \sum_{e \in E} w_e \, z_e.
\]

(If you want to apply a global unit scaling factor `violation_unit_cost`, multiply the objective by it.)

## Constraints (Linearization)

### 1) Evidence with expected parity `same` (same-orientation expected)

For every evidence \(e\) with \(r_e = \text{same}\), enforce:
\[
z_e \ge s_{u_e} - s_{v_e},
\]
\[
z_e \ge s_{v_e} - s_{u_e}.
\]

These constraints ensure \(z_e \ge |s_{u_e} - s_{v_e}|\). Therefore:
- if the two orientations differ, \(z_e\) must be 1 (evidence violated)
- if they are the same, \(z_e\) may be 0 (evidence satisfied)

### 2) Evidence with expected parity `opposite` (opposite-orientation expected)

For every evidence \(e\) with \(r_e = \text{opposite}\), enforce:
\[
z_e \ge s_{u_e} + s_{v_e} - 1,
\]
\[
z_e \ge 1 - s_{u_e} - s_{v_e}.
\]

These constraints ensure \(z_e \ge 1 - |s_{u_e} - s_{v_e}|\). Therefore:
- if the two orientations are the same, \(z_e\) must be 1 (evidence violated)
- if they differ, \(z_e\) may be 0 (evidence satisfied)

## Notes for Implementers

- `source_id` in `evidence.csv` is metadata and should not affect the model.
- The formulation is equivalent to a signed-graph disagreement minimization / balanced-subgraph variant. If multiple evidence statements share the same endpoints and relation, they can be aggregated by summing weights; this does not change optimal solutions.
