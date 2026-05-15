---
name: Selection, covering, packing
description: Pattern module for subset selection, set cover, capacity and budget constraints, and knapsack-like ASP encodings.
---

# Selection, covering, packing

Use this pattern when the task is "pick a subset" under feasibility and cost constraints.

## Basic subset choice

```asp
{ chosen(I) : item(I) }.
```

## Exact or bounded cardinality

```asp
K { chosen(I) : item(I) } K.
:- K+1 { chosen(I) : item(I) }.
```

Choose the form that reads most clearly for the requested bound.

## Coverage

```asp
covered(E) :- chosen(I), covers(I,E).
:- need(E), not covered(E).
```

## Capacity or budget

```asp
:- budget(B), B < #sum { W,I : chosen(I), weight(I,W) }.
```

## Modeling advice

- Use helper predicates such as `covered/1`, `used_capacity/1`, `selected_count/1`.
- Coverage and budget constraints should usually be separate; do not hide both concerns in one large rule.
- This pattern fits set cover, team formation, menu selection, feature selection, and many knapsack-like tasks.
