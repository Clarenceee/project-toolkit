# Coding practices

Write code that is easy to understand, verify, and change. Choose the smallest design that makes responsibilities and behavior clear.

## Design

- Give each module and function a clear responsibility. Put behavior with the module that owns the data and knowledge it uses.
- When designing or changing an interface, consult the `codebase-design` skill. Aim for deep modules: keep the interface small and clear while hiding implementation complexity behind it.
- Use typed schemas for inputs and outputs when data crosses a meaningful boundary. Keep validation with the schema or boundary that owns the data; reject invalid data clearly before it spreads through the system. Use Pydantic models where runtime validation and structured parsing are useful.
- Keep integration logic in focused classes with methods relevant to that integration. Give each class a clear responsibility and avoid catch-all utility classes.
- Keep dependencies and side effects visible. Pass dependencies explicitly, avoid global state, and keep I/O at clear seams.
- Avoid pass-through wrappers and speculative abstractions. Add a layer when it owns meaningful behavior, hides complexity, or provides a stable interface.
- Remove duplication when it represents the same rule or knowledge. Similar-looking code with different meaning should remain separate.
- Keep comments out of source-file headers and do not add module docstrings. Put module-level explanations in Markdown documentation. Use simple function and class docstrings when they clarify a public interface. Use inline comments sparingly to explain non-obvious reasons or constraints, not to narrate the code.

## Refactoring

- Name the design problem or code smell before changing structure. Choose the smallest refactoring that addresses it.
- Preserve observable behavior while refactoring. Make one structural change at a time and run relevant checks between changes.
- Extract a function when a meaningful name clarifies behavior or gives it a clear owner. Inline a function when it only adds indirection.
- Keep related decisions together so one change does not require edits across unrelated modules.
- Prefer clear control flow. Use guard clauses for early exits and simplify complex conditions when that makes the main path easier to follow.
- Improve clarity before optimizing. Measure performance before making performance-driven changes.

## Code review

- Before starting a requested code review, tell the user that three subagents will review the changes and name the skills they will use. Wait for the user's approval before launching them.
- After approval, run separate subagents using the `pragmatic-programmer`, `software-design-philosophy`, and `refactoring-patterns` skills. Have each report concrete findings tied to the changed code.
- Summarize the findings together, remove duplicates, and make disagreements or distinct perspectives clear.

## Review questions

- Is each module's responsibility clear, and does its interface keep complexity with its owner?
- Are inputs and outputs typed and validated where data enters or changes ownership?
- Does each class own related behavior, dependencies, and decisions?
- Does each abstraction or wrapper provide behavior or clarity that callers need?
- Is repeated code the same rule, or only superficially similar?
- Does the refactoring preserve behavior, with relevant checks passing after each step?
