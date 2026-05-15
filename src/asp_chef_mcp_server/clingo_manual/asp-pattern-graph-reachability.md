---
name: Graph and reachability
description: Pattern module for paths, connectivity, recursive reachability, graph coloring, and acyclicity constraints in ASP.
---

# Graph and reachability

Use this pattern for paths, connectivity, graph coloring, dependency closure, and acyclicity.

## Reachability closure

```asp
reach(Y) :- start(X), edge(X,Y).
reach(Y) :- reach(X), edge(X,Y).
```

Usually add domain facts such as `node/1` and seed predicates such as `start/1`.

## Path or tree selection

```asp
{ use(X,Y) : edge(X,Y) }.
:- use(X,Y), not edge(X,Y).
```

Then constrain selected edges using reachability, indegree, or acyclicity predicates.

## Coloring

```asp
1 { color(N,C) : palette(C) } 1 :- node(N).
:- edge(N1,N2), color(N1,C), color(N2,C).
```

## Acyclicity idea

Derive a closure relation over selected edges and forbid self-reachability:

```asp
path(X,Y) :- use(X,Y).
path(X,Z) :- path(X,Y), use(Y,Z).
:- path(X,X).
```

## Modeling advice

- Introduce helper predicates like `reach/1`, `path/2`, `indegree/2`.
- For undirected graphs, normalize edge handling early instead of duplicating logic inconsistently.
- Recursive definitions are often the cleanest part of the encoding; keep them small and domain-grounded.
