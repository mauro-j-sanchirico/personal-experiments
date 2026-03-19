# AGENTS.md

These rules are mandatory and override default behavior.

## 0. Human Interaction

- Perform only the steps requested.
- Do not perform extra steps.

## 1. Core Philosophy

- Simplicity is the top priority.
- Prefer the smallest working solution.
- Readability is more important than cleverness.
- Avoid over-engineering.
- Choose the simplest approach and justify added complexity.
- Do not optimize prematurely.
- Make the code **instructive**. The reader of the code should be able to learn from it.

## 2. Architecture Rules

- Prefer functions over classes.
- Avoid OOP unless it is clearly justified.
- No unnecessary layers, abstractions, or patterns.
- No dependency injection, factories, or frameworks unless required.
- Keep structure flat and direct.

## 3. Code Style

- Use idiomatic Python.
- Follow the Google style guide.
- Ensure code will pass mypy and ruff checks.
- Prefer the standard library.
- Minimize dependencies.
- Use clear, descriptive names in snake case (no clever abbreviations).
- Keep functions small (target: <30 lines).
- Limit nesting (max ~2 levels where possible).

## 3. Modification Rules (VERY IMPORTANT)

When editing existing code:

- Make the smallest possible change.
- Do not refactor unrelated parts.
- Do not rewrite working code without clear benefit.
- Preserve existing structure unless there is a strong reason.

## 4. Comments & Documentation

- Comment only when intent is not obvious.
- Do not restate what the code already shows.
- Prefer clear code over explanatory comments.
