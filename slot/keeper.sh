#!/usr/bin/env bash
# Re-runs at most one dropped pipeline run of $REPO when its CI slot is free (slot/pick.jq says which).
# Env: GH_TOKEN (actions: write), REPO (owner/name), WORKFLOW (the pipeline's file name); DRY_RUN=1 only
# says what it would re-run.
set -euo pipefail
here=$(dirname "$0")
api() { gh api "$@"; }

runs=$(api "repos/$REPO/actions/workflows/$WORKFLOW/runs?per_page=100" \
  --jq '[.workflow_runs[] | {id, status, conclusion, branch: .head_branch, event, created: .created_at, attempt: .run_attempt}]')
tags=$(api "repos/$REPO/tags?per_page=100" --paginate --jq '[.[].name]' | jq -s 'add // []')
prs=$(api "repos/$REPO/pulls?state=open&per_page=100" --paginate --jq '[.[].head.ref]' | jq -s 'add // []')
default=$(api "repos/$REPO" --jq .default_branch)
input=$(jq -n --argjson runs "$runs" --argjson tags "$tags" --argjson prs "$prs" --arg default "$default" \
  '{runs: $runs, tags: $tags, prs: $prs, default: $default}')

for id in $(jq -r -f "$here/pick.jq" <<<"$input"); do
  # GitHub drops a waiting run before any job starts; a run with jobs was cancelled after it began.
  jobs=$(api "repos/$REPO/actions/runs/$id/jobs?filter=all" --jq .total_count)
  if [ "$jobs" != "0" ]; then
    echo "skip $id: it had started ($jobs jobs), so the slot did not drop it"
    continue
  fi
  echo "re-running $id"
  [ "${DRY_RUN:-}" = 1 ] && exit 0
  # Another keeper may have taken it a moment ago; that is not a failure.
  api -X POST "repos/$REPO/actions/runs/$id/rerun" || echo "re-run of $id refused; another keeper likely took it"
  exit 0
done
echo "nothing to re-run"
