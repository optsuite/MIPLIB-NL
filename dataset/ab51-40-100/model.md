# Mathematical Model (Reference): Package-Gated Opportunity Selection with Resource Conflicts

This instance can be interpreted as selecting a set of revenue-generating opportunities under two layers of business rules:

1. Each client may sign at most one package (a package represents a commercial agreement or configuration).
2. Opportunities belong to packages and can only be executed if their package is signed.
3. Each opportunity consumes one unit of capacity from every resource it touches, and each resource has capacity one (mutual exclusivity).

## Sets

- Clients: \( \mathcal{G} \)
- Packages: \( \mathcal{P} \)
- Opportunities: \( \mathcal{O} \)
- Resources: \( \mathcal{R} \)

## Parameters

- \( \text{client}(p) \in \mathcal{G} \): the client that owns package \(p\)
- \( \text{package}(o) \in \mathcal{P} \): the package that unlocks opportunity \(o\)
- \( \text{profit}_o > 0 \): profit gained if opportunity \(o\) is executed
- \( A_{r,o} \in \{0,1\} \): 1 if opportunity \(o\) consumes resource \(r\), else 0
- Resource capacity is 1 for every \(r\)

## Decision Variables

- \( y_p \in [0,1] \): whether to sign package \(p\)
- \( x_o \in [0,1] \): whether to execute opportunity \(o\)

## Objective

Maximize total profit from executed opportunities:
\[
\max \sum_{o \in \mathcal{O}} \text{profit}_o \, x_o
\]

## Constraints

### 1) At most one package per client
\[
\sum_{p \in \mathcal{P}: \text{client}(p)=g} y_p \le 1 \quad \forall g \in \mathcal{G}
\]

### 2) Resource mutual exclusivity (capacity 1)
\[
\sum_{o \in \mathcal{O}} A_{r,o} \, x_o \le 1 \quad \forall r \in \mathcal{R}
\]

### 3) Package gating (opportunity requires its package)
\[
 x_o \le y_{\text{package}(o)} \quad \forall o \in \mathcal{O}
\]

## Notes

- The provided MPS uses continuous variables with bounds \([0,1]\). This reference model keeps the same relaxation; if a 0/1 interpretation is desired, \(x\) and \(y\) can be declared binary.
