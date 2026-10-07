# Full Migration Branch Governance

Effective during M0→M8.

## Active branches

### `main`

Formal release branch. Keep frozen during Full Migration. Do not merge partial migration milestones into main.

### `migration/full-v3`

Single active Full Migration integration line. M6→M8 work lands here.

## Historical feature branches

The following branches are ancestors/history, not active authorities:

- `feature/provenance-kernel-v0.2` — PR #7 already merged;
- `feature/r4-evidence-core-v0.2-beta` — PR #8 already merged;
- `feature/literary-plock-v0.3-alpha` — fully incorporated into the migration line.

PR #9 was closed without merge after its effective history was incorporated into `migration/full-v3`. Its old “next gate” instructions are superseded by the Full Migration freeze.

Do not add new commits to these feature branches during M0→M8.

## Export branches

- `export/full-migration-snapshot-20261006`
- `export/self-contained-20261006`

These are immutable handover/export snapshots. Do not merge, rebase or cherry-pick the snapshot commits into the runtime migration branch as a whole.

If an exporter utility is ever needed later, migrate the utility intentionally as code rather than merging the snapshot branch.

## Cleanup timing

Do not delete historical/export branches before M8 Completion Gate and the final migration merge.

After M8:

1. create archival tags for meaningful frozen states;
2. merge the completed Full Migration into main through one reviewed release PR;
3. verify stable ACTIVE and all Completion Gate regressions;
4. only then delete obsolete feature branches;
5. retain export history as tags or documented immutable refs.

This keeps one runtime authority while preserving audit provenance.
