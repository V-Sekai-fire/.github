#!/usr/bin/env bash
# Tests slot/pick.jq: which dropped pipeline run the keeper re-runs. Run: slot/test.sh
set -u
cd "$(dirname "$0")"
fail=0
run() { # name expected json
  local got
  got=$(jq -r -f pick.jq <<<"$3" | tr '\n' ' ' | sed 's/ $//')
  if [ "$got" = "$2" ]; then echo "ok   $1"; else echo "FAIL $1: want '$2' got '$got'"; fail=1; fi
}
# r id status conclusion branch event created attempt
r() { printf '{"id":%s,"status":"%s","conclusion":"%s","branch":"%s","event":"%s","created":"%s","attempt":%s}' "$@"; }
T='"tags":["v0.1.0-dev.6","v0.1.0-dev.7","v0.1.0-dev.10","v0.1.0-beta.1","v0.1.0-rc.1","v0.1.0","v0.2.0"]'
P='"prs":["fix/a","fix/b"],"default":"main"'

run "busy slot: nothing" "" "{\"runs\":[$(r 1 completed cancelled v0.1.0-dev.7 push 2026-10-10T01:00:00Z 1),$(r 2 in_progress '' main push 2026-10-10T02:00:00Z 1)],$T,$P}"
run "queued counts as busy" "" "{\"runs\":[$(r 1 completed cancelled v0.1.0-dev.7 push 2026-10-10T01:00:00Z 1),$(r 2 queued '' fix/a pull_request 2026-10-10T02:00:00Z 1)],$T,$P}"
run "dropped tags: oldest version first, not oldest run" "11 12 13" "{\"runs\":[$(r 13 completed cancelled v0.1.0-dev.10 push 2026-10-10T01:00:00Z 1),$(r 12 completed cancelled v0.1.0-dev.7 push 2026-10-10T02:00:00Z 1),$(r 11 completed cancelled v0.1.0-dev.6 push 2026-10-10T03:00:00Z 1)],$T,$P}"
run "dev before beta before rc before release, and minor bumps last" "4 3 2 1 5" "{\"runs\":[$(r 1 completed cancelled v0.1.0 push 2026-10-10T01:00:00Z 1),$(r 2 completed cancelled v0.1.0-rc.1 push 2026-10-10T01:00:00Z 1),$(r 3 completed cancelled v0.1.0-beta.1 push 2026-10-10T01:00:00Z 1),$(r 4 completed cancelled v0.1.0-dev.10 push 2026-10-10T01:00:00Z 1),$(r 5 completed cancelled v0.2.0 push 2026-10-10T01:00:00Z 1)],$T,$P}"
run "a tag built since is not re-run" "" "{\"runs\":[$(r 1 completed cancelled v0.1.0-dev.7 push 2026-10-10T01:00:00Z 1),$(r 2 completed success v0.1.0-dev.7 push 2026-10-10T02:00:00Z 1)],$T,$P}"
run "tags before branches" "1 3" "{\"runs\":[$(r 3 completed cancelled main push 2026-10-10T01:00:00Z 1),$(r 1 completed cancelled v0.1.0-dev.7 push 2026-10-10T02:00:00Z 1)],$T,$P}"
run "branches: newest wins, main then open PRs oldest first" "5 7 6" "{\"runs\":[$(r 4 completed cancelled main push 2026-10-10T01:00:00Z 1),$(r 5 completed cancelled main push 2026-10-10T02:00:00Z 1),$(r 6 completed cancelled fix/b pull_request 2026-10-10T03:00:00Z 1),$(r 7 completed cancelled fix/a pull_request 2026-10-10T02:30:00Z 1)],$T,$P}"
run "a branch whose newest run finished is done" "" "{\"runs\":[$(r 4 completed cancelled main push 2026-10-10T01:00:00Z 1),$(r 5 completed failure main push 2026-10-10T02:00:00Z 1)],$T,$P}"
run "closed PRs and other branches are left" "" "{\"runs\":[$(r 8 completed cancelled fix/gone pull_request 2026-10-10T01:00:00Z 1),$(r 9 completed cancelled feature push 2026-10-10T01:00:00Z 1)],$T,$P}"
run "a run re-run 5 times is left (no loop)" "" "{\"runs\":[$(r 1 completed cancelled v0.1.0-dev.7 push 2026-10-10T01:00:00Z 5)],$T,$P}"
run "manual and scheduled runs are left" "" "{\"runs\":[$(r 1 completed cancelled main workflow_dispatch 2026-10-10T01:00:00Z 1),$(r 2 completed cancelled main schedule 2026-10-10T01:00:00Z 1)],$T,$P}"
exit $fail
