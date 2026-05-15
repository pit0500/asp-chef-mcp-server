---
name: ASP pattern index
description: Routing module for common ASP modeling families. Use first to decide whether a task is about scheduling, graph reachability, selection and covering, or optimization and symmetry.
---

# ASP pattern index

Use this file to map a request to a modeling family.

## Assignment and scheduling

Signals:

- assign each task, job, person, room, or resource
- one-per-slot, one-per-job, capacity per resource
- timetabling, matching, allocation, roster

Go to `asp-pattern-assignment-scheduling.md`.

## Graph and reachability

Signals:

- path, connectivity, reachability, ancestor, dependency closure
- graph coloring
- acyclicity, transitive closure, connected subgraph

Go to `asp-pattern-graph-reachability.md`.

## Selection, covering, packing

Signals:

- choose a subset of items
- satisfy coverage requirements
- stay under budget or capacity
- set cover, knapsack-like selection, facility choice

Go to `asp-pattern-selection-covering-packing.md`.

## Optimization and symmetry

Signals:

- minimize cost, lateness, or penalty
- maximize score or covered demand
- remove equivalent solutions that differ only by renaming or order

Go to `asp-pattern-optimization-symmetry.md`.

## Baseline decomposition

For most ASP encodings, use this order:

1. Facts describing the instance
2. Choice rules generating candidate solutions
3. Constraints rejecting invalid candidates
4. Helper predicates for counts, reachability, or conflict detection
5. Optimization
6. `#show`
