---
name: Assignment and scheduling
description: Pattern module for matching, timetabling, rostering, and resource allocation encodings with cardinality, capacity, and conflict constraints.
---

# Assignment and scheduling

Use this pattern for matching, timetabling, rostering, and resource allocation.

## Canonical skeleton

```asp
1 { assign(J,R) : resource(R) } 1 :- job(J).

:- assign(J,R1), assign(J,R2), R1 != R2.
:- assign(J1,R), assign(J2,R), J1 != J2, clash(J1,J2).
```

Adapt the second constraint depending on whether a resource may host one or many jobs.

## Typical extensions

- Capacity:

```asp
:- resource(R), C < #count { J : assign(J,R) }, capacity(R,C).
```

- Time conflicts:

```asp
:- assign(J1,R), assign(J2,R), J1 < J2, overlaps(J1,J2).
```

- Exactly one job per slot:

```asp
1 { assign(T,J) : job(J) } 1 :- slot(T).
```

## Modeling advice

- Separate assignment choice from conflict detection.
- If time is involved, create explicit predicates such as `slot/1`, `day/1`, `overlaps/2`.
- Prefer precomputed conflict predicates over repeating long conjunctions inside many constraints.
