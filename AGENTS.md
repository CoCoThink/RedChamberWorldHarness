# Repository workflow

- Work and commit directly on `main` in `/mnt/d/code/redchamberworldharness`.
- Do not create local or remote branches, including temporary, backup, research, review, or agent branches, unless the user explicitly changes this instruction.
- Use the existing `main` working directory for future iterations. Do not create additional worktrees for routine work. Existing detached worktrees retain historical files and are not active development checkouts.
- Preserve review evidence and historical commits when consolidating work. Follow the evidence and data rules in `CONTRIBUTING.md`.
- Sub-agents must use the parent session's model; when the launch interface requires a model, specify the same model as the parent session.

- If a delegated task name begins `rcwh_ticket_`, read and execute `.codex-dispatch/<task-name>.md` in the repository root; the name is supplied in the NEW_TASK header. This is a fallback when task message bodies are unavailable. The dispatcher must create the task file before launching the agent, and retain required review evidence and context declarations.
