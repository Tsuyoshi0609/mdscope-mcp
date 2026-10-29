# Repository Instructions

## Shared Claude/Codex Rules

Before starting any task in this repository, read all instruction files under `.claude/` recursively and follow them as repository instructions.

- Treat `.claude/**/*.md` as instructions for the entire repository unless a file explicitly limits its scope.
- Apply the same precedence and intent that Claude uses for those rules.
- If multiple `.claude/` rules conflict, prefer the rule with the more specific scope. If scope is equal, prefer the rule in the deeper directory, then the more explicit task-specific rule.
- Direct system, developer, and user instructions take precedence over this file and `.claude/` rules.
- Re-read the applicable `.claude/` rules when they change during a task.

This file intentionally delegates shared project guidance to `.claude/` so Claude and Codex use one source of truth.
