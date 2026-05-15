---
name: asp-modeling-patterns
description: Solve common Answer Set Programming modeling tasks by mapping requests to reusable encoding patterns. Use when the task looks like assignment, scheduling, graph reachability, subset selection, covering, packing, symmetry breaking, or optimization over candidate solutions.
---

# ASP modeling patterns

Use this file when the main challenge is choosing the right encoding pattern rather than remembering surface syntax.

This file complements `asp-clingo-syntax.md`.

## Workflow

1. Classify the request using `asp-pattern-index.md`.
2. Start from the smallest matching pattern file instead of writing the encoding from scratch.
3. Keep the encoding layered:
   - instance facts
   - candidate generation
   - hard constraints
   - helper predicates
   - optimization
   - `#show`
4. Use `asp-clingo-syntax.md` to validate the final syntax.

## Global heuristics

- Prefer explicit domain predicates such as `job/1`, `slot/1`, `edge/2`, `item/1`.
- Separate "what can be chosen" from "what is forbidden".
- Add helper predicates when they make constraints shorter or safer.
- Add symmetry breaking only after the base encoding is correct.
- Add optimization only after satisfiable models exist.

## Pattern files

- `asp-pattern-index.md`
- `asp-pattern-assignment-scheduling.md`
- `asp-pattern-graph-reachability.md`
- `asp-pattern-selection-covering-packing.md`
- `asp-pattern-optimization-symmetry.md`
