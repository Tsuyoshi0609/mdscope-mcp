# Repository Instructions

## Viewing structures, trajectories and maps

If the request is only to show a structure, trajectory or density map with the mdscope MCP tools,
do not read any files and do not run shell commands. Call `view_structure` (one frame),
`view_trajectory` (playback) or `view_density` (map over a structure) right away, passing the paths
the user gave as `topology` / `trajectory` / `map`.
Skip `mdscope_info` and `list_files` unless a call reports a missing file.
The `.claude/` rules below are for editing, documenting and committing, not for viewing.

## Shared Claude/Codex Rules

Before editing code or docs, or running git, read all instruction files under `.claude/` recursively and follow them as repository instructions.

- Treat `.claude/**/*.md` as instructions for the entire repository unless a file explicitly limits its scope.
- Apply the same precedence and intent that Claude uses for those rules.
- If multiple `.claude/` rules conflict, prefer the rule with the more specific scope. If scope is equal, prefer the rule in the deeper directory, then the more explicit task-specific rule.
- Direct system, developer, and user instructions take precedence over this file and `.claude/` rules.
- Re-read the applicable `.claude/` rules when they change during a task.

This file intentionally delegates shared project guidance to `.claude/` so Claude and Codex use one source of truth.
