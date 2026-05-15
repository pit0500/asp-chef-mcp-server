---
name: Optimization and symmetry
description: Pattern module for weak constraints, #minimize, multi-criteria objectives, and safe symmetry breaking in ASP encodings.
---

# Optimization and symmetry

Use this reference after the base encoding already generates valid models.

## Objective pattern

```asp
#minimize { W,I : chosen(I), weight(I,W) }.
```

Or with weak constraints:

```asp
:~ chosen(I), weight(I,W). [W@1,I]
```

## Multi-criteria optimization

```asp
#minimize {
    W@1,I : chosen(I), cost(I,W);
    P@2,J : late(J), penalty(J,P)
}.
```

Lower levels have higher priority in clingo's lexicographic optimization scheme.

## Symmetry breaking examples

- Order interchangeable objects by index
- Force one canonical representative among equivalent permutations
- Use comparisons like `J1 < J2` to avoid duplicate pair constraints

Example:

```asp
:- assign(J1,R), assign(J2,R), J1 < J2, same_type(J1,J2), preferred(J2,J1).
```

The exact rule depends on the domain; the point is to cut equivalent solutions, not valid distinct ones.

## Modeling advice

- Add optimization only after feasibility works.
- Add symmetry breaking only when you can justify why two solutions are truly equivalent.
- If a "symmetry breaking" rule changes which real-world solutions are admissible, it is not symmetry breaking.
