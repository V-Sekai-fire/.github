# Which dropped pipeline runs to re-run, in order, when the repo's one CI slot is free.
#
# Input: {"runs":[{id,status,conclusion,branch,event,created,attempt}], "tags":[...], "prs":[open PR
# head branches], "default":"main"}. Output: run ids, best first; empty while any run holds or waits
# for the slot. The caller re-runs the first that GitHub dropped unstarted (no jobs), so a run a person
# cancelled is not brought back.
#
# A concurrency group keeps one waiting run and drops the rest. Tags are never lost: every tag whose
# newest run was dropped comes back, oldest version first (dev < alpha < beta < rc < release). Branches
# are newest-wins: only the newest run of the default branch, then of each open PR (oldest PR first).

# Semver order, with the pre-release ladder ranked as the org releases it rather than alphabetically.
def stage: {"dev": 0, "alpha": 1, "beta": 2, "rc": 3}[.] // .;
def ident: if test("^[0-9]+$") then tonumber else stage end;
def version:
  ltrimstr("v") | capture("^(?<core>[0-9]+(\\.[0-9]+)*)(-(?<pre>[^+]*))?") as $v
  | ($v.core | split(".") | map(tonumber)) as $core
  | ($core + [0, 0, 0])[0:3]
    + (if $v.pre == null then [1] else [0] + ($v.pre | split(".") | map(ident)) end);

def dropped: .status == "completed" and .conclusion == "cancelled" and .attempt < 5;
# The newest run of each ref, for events that build a ref.
def newest: map(select(.event == "push" or .event == "pull_request"))
  | group_by([.event, .branch]) | map(max_by(.created));

. as $in
| if any($in.runs[]; .status != "completed") then empty
  else
    ($in.runs | newest) as $heads
    | ($heads | map(select(.event == "push" and (.branch as $b | $in.tags | index($b)) and dropped))
        | sort_by(.branch | version) | .[].id),
      ($heads | map(select(.event == "push" and .branch == $in.default and dropped)) | .[].id),
      ($heads | map(select(.event == "pull_request" and (.branch as $b | $in.prs | index($b)) and dropped))
        | sort_by(.created) | .[].id)
  end
