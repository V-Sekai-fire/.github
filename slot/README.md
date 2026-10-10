# One CI slot per repo

Every V-Sekai-fire repo runs its CI as one workflow, `pipeline.yml`, whose jobs run one after another and
which sits in the concurrency group `slot-<owner/repo>`. So a repo takes one runner at a time from the
org's shared pool.

A concurrency group keeps one waiting run and drops the rest. `slot-keeper` brings dropped runs back, one
at a time, when the slot is free:

1. Tags, never lost, oldest version first: dev, alpha, beta, rc, then the release (`v0.1.0-dev.7`
   before `v0.1.0-beta.1` before `v0.1.0`).
2. The newest run of the default branch.
3. The newest run of each open PR, oldest PR first.

Older runs of a branch are not brought back (newest wins), nor are runs a person cancelled (they had
started), nor a run already tried five times.

## Adding a repo

- `pipeline.yml`: triggers on push to the default branch, tags and pull requests, with

  ```yaml
  concurrency:
    group: slot-${{ github.repository }}
    cancel-in-progress: false
  ```

  and jobs chained with `needs:` and `if: ${{ !cancelled() }}`, so each runs after the last even when
  it failed, and matrices with `max-parallel: 1`. Other CI workflows become `workflow_call` workflows the
  pipeline calls in turn.
- `slot-keeper.yml`:

  ```yaml
  name: slot-keeper
  on:
    workflow_run:
      workflows: [pipeline]
      types: [completed]
  permissions:
    actions: write
    contents: read
    pull-requests: read
  jobs:
    keep:
      uses: V-Sekai-fire/.github/.github/workflows/slot-keeper.yml@main
  ```

## Tests

`slot/test.sh` checks which run the keeper picks.
