# Contributing

## Core rule

Never change Evidence Truth merely to make a reconstruction cleaner.

## Git workflow

Iterate and commit directly on `main`. Do not create other local or remote branches unless the user explicitly requests a change to this workflow. See `AGENTS.md` for agent instructions.

## Change checklist

- Which truth layer changes?
- Does any OPEN-LOCK become more specific? If so, what new upstream evidence permits that?
- Does a candidate change downstream object, timeline, or character-knowledge state?
- Are regression tests included?
- If cultural material is added, what dramatic or character function does it perform?
- If prose is changed, has blind reading been separated from evidence review?

## Data edits

Prefer structured YAML/JSON as canonical state. Markdown is explanatory output.

## Documentation

Update existing architecture contracts and runbooks when behavior changes. Keep current progress in the selected project owners and live acceptance checks. Use Git history for implementation narratives and past test counts; add a separate review document only when it contains original findings needed to interpret sources or decisions. Registered source bytes and original review submissions remain immutable audit records.
