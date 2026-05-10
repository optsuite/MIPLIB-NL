# 3D Container Loading (Axis-Aligned Packing)

## Business interpretation

A freight forwarder is preparing a single loading unit for a fixed departure (e.g., a narrow truck bay, a long shipping crate, or an aircraft ULD). A staging area contains a set of candidate shipment boxes. Each box comes with a known business value called profit: an additive score earned only if that box is actually loaded. It can represent expected revenue, customer priority points, avoided delay penalties, or an internal service score. Boxes that are not loaded contribute zero. The planner may reject some boxes if space is tight.

Every loaded box must be placed fully inside the container and cannot overlap any other loaded box. Some boxes have handling constraints that restrict how they can be turned (for instance, a fragile item must stay upright, labels must remain readable, or a product must not be laid on its side). These restrictions are modeled by listing the allowed axis-aligned orientations for each item, and the planner may choose at most one allowed orientation for a loaded item.

The objective is to maximize the total business value (sum of profits of the loaded boxes) while keeping the load physically feasible.

## Data mapping

This instance is described by `instance.json` and the CSV files in `data/`:

- `container.csv` gives the container inner dimensions.
- `items.csv` lists candidate boxes and their profits.
- `orientations.csv` enumerates the allowed oriented dimensions for each box.

## Reference optimization model

### Sets

- Items: $i \\in \\mathcal{I}$.
- Orientations for item $i$: $o \\in \\mathcal{O}_i$.
- Axes: $a \\in \\{x,y,z\\}$.
- Ordered item pairs: $(i,j) \\in \\mathcal{I}^2, i \\ne j$.

### Parameters

- Container dimensions: $(L_x,L_y,L_z)$.
- Oriented box sizes: $(\\ell_{i,o,x}, \\ell_{i,o,y}, \\ell_{i,o,z})$ for each $(i,o)$.
- Profit: $p_i$ for each item $i$.

### Decision variables

- $u_i \\in \\{0,1\\}$: 1 if item $i$ is loaded.
- $s_{i,o} \\in \\{0,1\\}$: 1 if item $i$ is loaded using orientation $o$.
- $(X_{i,x},X_{i,y},X_{i,z}) \\ge 0$: lower-corner placement coordinates for item $i$.
- $b_{i,j,a} \\in \\{0,1\\}$ for $i\\ne j$: 1 if item $i$ is placed before item $j$ along axis $a$.

### Core constraints

\\[
\\sum_{o\\in \\mathcal{O}_i} s_{i,o} = u_i \\quad \\forall i \\in \\mathcal{I}.
\\]

\\[
\\ell_{i,a} = \\sum_{o\\in \\mathcal{O}_i} \\ell_{i,o,a} \\; s_{i,o} \\quad \\forall i,\\; a\\in\\{x,y,z\\}.
\\]

\\[
X_{i,a} + \\ell_{i,a} \\le L_a + L_a (1-u_i) \\quad \\forall i,\\; a\\in\\{x,y,z\\}.
\\]

\\[
\\sum_{a\\in\\{x,y,z\\}} (b_{i,j,a} + b_{j,i,a}) \\ge u_i + u_j - 1 \\quad \\forall i<j.
\\]

\\[
X_{i,a} + \\ell_{i,a} \\le X_{j,a} + L_a (1-b_{i,j,a}) + L_a (2-u_i-u_j) \\quad \\forall i\\ne j,\\; a\\in\\{x,y,z\\}.
\\]

### Objective

\\[
\\max \\sum_{i\\in\\mathcal{I}} p_i\\, u_i.
\\]

## Notes

- The reference `solver.py` in this folder implements this formulation and reads the CSV files directly.
