# Currency Exchange Problem Model

## Problem Description
In an online game, there are three types of ancient currencies: Gold Coin, Platinum Coin, and Obsidian Coin. A player wants to convert a batch of Gold Coins into a combination of Platinum and Obsidian Coins such that the total value is exactly preserved. We want to find the minimum number of Gold Coins (at least 1) required for this exchange.

## Variables
- $x$: The number of Gold Coins (Integer).
- $y$: The number of Platinum Coins (Integer).
- $z$: The number of Obsidian Coins (Integer).

## Parameters
- $V_a$: The value of a Gold Coin.
- $V_b$: The value of a Platinum Coin.
- $V_c$: The value of an Obsidian Coin.

## Objective Function
Minimize the number of Gold Coins:
$$
\min x
$$

## Constraints
1.  **Value Conservation**: The total value of Gold Coins must equal the sum of the values of Platinum and Obsidian Coins.
    $$
    x \cdot V_a = y \cdot V_b + z \cdot V_c
    $$
2.  **Minimum Quantity**: The number of Gold Coins must be at least 1.
    $$
    x \ge 1
    $$
3.  **Non-negativity and Integrality**:
    $$
    x, y, z \in \mathbb{Z}_{\ge 0}
    $$
