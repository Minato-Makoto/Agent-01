---
name: Math
description: Evaluate arithmetic and math-function expressions in a restricted environment.
module: builtin_tools.calculator
tools:
  - calculate
---

# Math Skill

Performs deterministic math evaluation.

## `calculate`

- Required: `expression` (string)
- Example: `2 + 3 * 4`, `sqrt(144)`, `sin(pi/2)`

Supported functions/constants are restricted by implementation.
If expression parsing fails, tool returns a structured math error.
