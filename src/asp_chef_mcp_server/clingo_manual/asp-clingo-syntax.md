---
name: asp-clingo-syntax
description: Write and review correct ASP/clingo code. Use when a task is syntax-sensitive, when the request involves rules, constraints, negation, choice rules, aggregates, optimization, #show, #program, or when an encoding may be unsafe for grounding.
---

# ASP clingo syntax

Use this file as the entry point when the main risk is incorrect clingo syntax or unsafe ASP rules.

## Workflow

1. Read this file first.
2. If the request is about a common modeling family, also read `asp-modeling-patterns.md`.
3. Prefer the exact syntax forms already present here instead of reconstructing them from memory.
4. If coverage is incomplete, say so instead of inventing syntax.

## What to enforce

- Every rule ends with `.`.
- Variables must be grounded safely, usually through positive domain literals.
- Keep `not p(X)` distinct from `-p(X)`.
- Keep disjunction `a ; b` distinct from choice `{ a; b }`.
- Use `#show` intentionally when visible output matters.
- Add `#minimize` or `:~` only when optimization is actually required.
