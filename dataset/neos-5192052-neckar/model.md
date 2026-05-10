### Problem Description
Assume you are the Operations Director of a chemical processing company. You manage a network that sources raw materials from $N_1$ supply regions, processes them through $N_2$ specific production lines, and fulfills contracts for $N_3$ potential strategic partners. 

Your goal is to maximize total net profit (which is mathematically equivalent to minimizing the negative of profit).

Key operations involve:
1. **Sourcing**: Obtaining raw materials from different supply groups, each with a total capacity limit.
2. **Processing & Splitting**: Raw materials are processed. Some lines transfer 100% of the volume, while others chemically separate the input into 80% Main Product and 20% By-Product.
3. **Production Line Decisions**: You have specific production lines that can be activated. Activating a line incurs a fixed setup cost/benefit and allows flow up to a specific capacity (Big-M constraint).
4. **Strategic Contracts**: There are major strategic contracts available. Accepting a contract brings a large fixed bonus but requires allocating significant production capacity. You are limited to selecting at most 4 out of these strategic contracts.
5. **Distribution**: Processed goods are sent to distribution zones, which also have capacity limits.

### Parameter Description
- $G$: Set of Supply Groups ($g = 1, \dots, N_1$)
- $I$: Set of Raw Material Item Types ($i = 1, \dots, 17$)
- $L$: Set of Production Lines ($l = 1, \dots, N_2$)
- $K$: Set of Strategic Contracts ($k = 1, \dots, N_3$)
- $Z$: Set of Distribution Zones ($z = 1, \dots, 9$)
- $S_g$: Maximum capacity for Supply Group $g$
- $D_z$: Maximum capacity for Distribution Zone $z$
- $M_l$: Capacity limit ("Big-M") for Production Line $l$
- $Q_k$: Capacity requirement/limit for Strategic Contract $k$
- $C_{var}$: Unit operational cost (or revenue if negative) for continuous flow variable $var$
- $F_l$: Fixed cost (or bonus if negative) for activating Production Line $l$
- $B_k$: Fixed bonus (negative value) for accepting Strategic Contract $k$
- $\alpha_{i,out}$: Yield ratio converting input item $i$ to output product $out$ (e.g., 1.0, 0.8, 0.2)

### Decision Variables
- $x_{g,i}$: Continuous variable, quantity of raw material $i$ sourced from group $g$ ($\ge 0$)
- $y_{out}$: Continuous variable, quantity of processed/distributed product ($\ge 0$)
- $\delta_l$: Binary variable, equals 1 if production line $l$ is active, 0 otherwise
- $\gamma_k$: Binary variable, equals 1 if strategic contract $k$ is accepted, 0 otherwise

### Objective Function

$$ 
\minimize \quad \sum_{g,i} C_{x_{g,i}} x_{g,i} + \sum_{out} C_{y_{out}} y_{out} + \sum_{l} F_l \delta_l + \sum_{k} B_k \gamma_k 
$$ 
*(Note: Since revenue is represented as negative cost, minimizing the total sum maximizes the net profit)*

### Constraints

1. **Supply Group Capacity**: Total raw material sourced from each group must not exceed its capacity.
$$\sum_{i \in I} x_{g,i} \le S_g \quad \forall g \in G$$

2. **Distribution Zone Capacity**: Total processed goods sent to each zone must not exceed its capacity.
$$\sum_{out \in Zone_z} y_{out} \le D_z \quad \forall z \in Z$$

3. **Production Line Logic (Big-M)**: Flow of a specific item type is allowed only if the corresponding line is active.
$$\sum_{g \in G} x_{g,l} \le M_l \cdot \delta_l \quad \forall l \in L$$
*(where line $l$ processes item type $l$)*

4. **Strategic Contract Logic**: Flow for contract-specific item groups is constrained by the contract selection.
$$\sum_{i \in Group_k} \sum_{g \in G} x_{g,i} \le Q_k \cdot \gamma_k \quad \forall k \in K$$

5. **Global Contract Limit**: At most 4 strategic contracts can be selected.
$$\sum_{k \in K} \gamma_k \le 4$$

6. **Material Conversion (Flow Balance)**: The output flow is strictly determined by the input flow and yield ratios.
$$\sum_{g \in G} x_{g,i} \cdot \alpha_{i,out} = \sum_{out} y_{out} \quad \forall i \in I$$
*(This represents the chemical splitting process, e.g., $1.0 \cdot Input = Output$ or $0.8 \cdot Input = MainProduct$)*