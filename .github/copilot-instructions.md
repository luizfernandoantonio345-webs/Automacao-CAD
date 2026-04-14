# Automacao CAD workspace instructions

- This repository is a mixed workspace with a Python backend at the root and a frontend app in the frontend folder.
- Prefer small, focused changes and fix the root cause instead of adding broad workarounds.
- On Python work, prefer the existing local virtual environment in .venv and keep compatibility with the current project structure.
- On frontend work, keep changes scoped to the frontend folder and preserve the existing stack and conventions already present there.
- On Windows automation tasks, prefer PowerShell-friendly commands and avoid Linux-only command examples.
- Before changing behavior, inspect the relevant module and nearby routes, services, or tests so decisions are based on the current code.
- Do not rewrite unrelated files, do not revert user changes, and do not introduce new dependencies unless they are necessary for the requested task.
- When making changes, validate with the most local checks possible, such as file errors, targeted tests, or the relevant app command.
