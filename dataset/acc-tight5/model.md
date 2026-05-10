# Mathematical Model (Reference): Choice Groups With Implications and Group Caps

This reference model matches the integrality and linear structure encoded in `acc-tight5.mps`, expressed using a generic “option selection” view.

## Indices

- Options: \(i \in \mathcal{O}\)
- Choice groups (decision slots): \(g \in \mathcal{G}\)
- Implication edges: \((p \to q) \in \mathcal{E}\)
- Cap groups: \(h \in \mathcal{H}\)

Let \(\mathcal{O}(g)\) be the set of options in choice group \(g\), and \(\mathcal{O}(h)\) be the set of options in cap group \(h\).

## Decision variables

- \(x_i \in \{0,1\}\): option \(i\) is selected

## Objective

Minimize the total penalty of selected options:
\[
\min \sum_{i \in \mathcal{O}} c_i x_i
\]

## Constraints

### 1) Exactly one option per choice group
\[
\sum_{i \in \mathcal{O}(g)} x_i = 1 \quad \forall g \in \mathcal{G}
\]

### 2) Implications (prerequisites)
\[
x_q \ge x_p \quad \forall (p \to q) \in \mathcal{E}
\]

### 3) Cap groups (uniform-sum bounds)
For each cap group \(h\), a bound of one of the following types is enforced:
- upper bound: \(\sum_{i \in \mathcal{O}(h)} x_i \le b_h\)
- lower bound: \(\sum_{i \in \mathcal{O}(h)} x_i \ge b_h\)
- equality: \(\sum_{i \in \mathcal{O}(h)} x_i = b_h\)

