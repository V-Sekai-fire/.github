"""Lower compact GRAFCET JSON-LD to taskweft HTN and raise HTN back.

Compact GRAFCET is IEC 60848 SFC in a small JSON-LD profile aligned with
Project-AGRAFE. HTN is taskweft's variables / actions / methods / tasks
shape. Round-trip on the domains in scope is the identity, modulo JSON
whitespace.

Usage:
    grafcet_htn.py lower <in.grafcet.jsonld> <out.domain.jsonld>
    grafcet_htn.py raise <in.domain.jsonld>   <out.grafcet.jsonld>
    grafcet_htn.py roundtrip <file>           # prove file == raise(lower(file))
                                              # or   file == lower(raise(file))
"""

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path


# ---------- shared parsers ------------------------------------------------


ASSIGN_RE = re.compile(r"^\s*V\.(?P<var>\w+)\s*:=\s*(?P<val>[^,\s]+)\s*$")
DURATION_RE = re.compile(r"^(?P<n>\d+)h$")
ISO_DURATION_RE = re.compile(r"^PT(?P<n>\d+)H$")
RECEPTIVITY_ATOM_RE = re.compile(r"X\.(?P<step>\w+)")


def parse_receptivity(expr):
    """Parse `X.a & X.b` into ['a', 'b']. Only AND-of-activities supported;
    that is the fragment this domain uses. Anything richer raises."""
    if not expr:
        return []
    parts = [p.strip() for p in expr.split("&")]
    out = []
    for p in parts:
        m = RECEPTIVITY_ATOM_RE.fullmatch(p)
        if not m:
            raise ValueError(f"receptivity atom outside supported fragment: {p!r}")
        out.append(m.group("step"))
    return out


def parse_action(expr):
    """Parse `V.foo:=1` into ('foo', 1)."""
    m = ASSIGN_RE.fullmatch(expr)
    if not m:
        raise ValueError(f"action outside supported fragment: {expr!r}")
    raw = m.group("val")
    val = int(raw) if raw.isdigit() else (True if raw == "true" else raw)
    return m.group("var"), val


def duration_to_iso(s):
    m = DURATION_RE.fullmatch(s or "")
    if not m:
        raise ValueError(f"unsupported duration {s!r}")
    return f"PT{m.group('n')}H"


def duration_from_iso(s):
    m = ISO_DURATION_RE.fullmatch(s or "")
    if not m:
        raise ValueError(f"unsupported ISO duration {s!r}")
    return f"{m.group('n')}h"


# ---------- lower: compact GRAFCET -> HTN ---------------------------------


def lower(grafcet):
    """Compact GRAFCET dict -> taskweft HTN dict."""
    variables = OrderedDict(grafcet["V"])
    steps = grafcet["S"]

    # walk S: gather ordinary steps with their (when, do, t) tuples,
    # and remember which steps sit inside an &> block whose parent is the
    # preceding ordinary step, so their sole implicit predecessor is that
    # parent when `when` is empty.
    ordinary = OrderedDict()   # name -> {when, do, t, extra_pred, implicit_parent}
    order = []
    last_step = None
    fanout_parent = None       # step before an open &> marker; pins for all siblings
    fanout_pending = None      # names still expected under the open &>
    pending_and_convergence = None
    for entry in steps:
        head = entry[0]
        if head == "^":
            continue
        if head == "&>":
            fanout_parent = last_step
            fanout_pending = list(entry[1:])
            continue
        if head == "&<":
            pending_and_convergence = list(entry[1:])
            continue
        if head in ("|>", "|<", "!>") or head.startswith(("%", "#")):
            raise NotImplementedError(f"lowering of {head!r} not in current scope")
        # ordinary step
        name, when, do, t = entry[0], entry[1], entry[2], entry[3]
        extra_pred = []
        if pending_and_convergence is not None:
            extra_pred = pending_and_convergence
            pending_and_convergence = None
        if fanout_pending and name in fanout_pending:
            implicit_parent = fanout_parent
            fanout_pending.remove(name)
            if not fanout_pending:
                fanout_pending = None
                fanout_parent = None
        else:
            implicit_parent = last_step
        ordinary[name] = {"when": when, "do": do, "t": t,
                          "extra_pred": extra_pred,
                          "implicit_parent": implicit_parent}
        order.append(name)
        last_step = name

    # build HTN
    def check_clause(pointer):
        return {"eval": {"type": "math/eq",
                         "a": {"type": "pointer/get", "pointer": pointer},
                         "b": True}}

    actions = OrderedDict()
    for name in order:
        info = ordinary[name]
        preds = parse_receptivity(info["when"]) + list(info["extra_pred"])
        # implicit parent (from AND-divergence or sequential position) is
        # dropped if it is already the only receptivity source, unless the
        # step's `when` is empty AND it has no explicit predecessors — then
        # the implicit parent becomes the sole precondition.
        if not preds and info["implicit_parent"]:
            preds = [info["implicit_parent"]]
        # dedupe, keep order
        seen = set(); ordered_preds = []
        for p in preds:
            if p not in seen:
                seen.add(p); ordered_preds.append(p)
        var, val = parse_action(info["do"])
        body = [check_clause(f"/done/{p}") for p in ordered_preds]
        body.append({"pointer/set": f"/done/{var}", "value": val if not isinstance(val, int) else bool(val)})
        actions[f"a_{name}"] = {
            "params": [],
            "duration": duration_to_iso(info["t"]),
            "body": body,
        }

    def method(name, done_key):
        return {
            "params": [],
            "alternatives": [
                {"name": "skip",
                 "check": [check_clause(f"/done/{done_key}")],
                 "subtasks": []},
                {"name": "do", "subtasks": [[f"a_{done_key}"]]},
            ],
        }

    methods = OrderedDict()
    for name in order:
        methods[f"m_{name}"] = method(name, name)
    methods["buildout"] = {
        "params": [],
        "alternatives": [{"name": "do",
                          "subtasks": [[f"m_{n}"] for n in order]}],
    }

    htn = OrderedDict()
    htn["@context"] = {"weftspun": "https://github.com/weftspun/",
                       "domain": "weftspun:planning/domain/"}
    htn["@type"] = "domain:Definition"
    htn["name"] = grafcet["sfc"]
    if "descr" in grafcet:
        htn["description"] = grafcet["descr"]
    htn["variables"] = [{"name": "done", "init": dict(variables)}]
    htn["actions"] = actions
    htn["methods"] = methods
    htn["tasks"] = [["buildout"]]
    return htn


# ---------- raise: HTN -> compact GRAFCET ---------------------------------


def raise_(htn):
    """taskweft HTN dict -> compact GRAFCET dict."""
    init = htn["variables"][0]["init"]
    action_order = list(htn["actions"].keys())

    # extract preds and (var, val) from each action
    parsed = OrderedDict()
    for aname in action_order:
        body = htn["actions"][aname]["body"]
        duration = htn["actions"][aname]["duration"]
        preds = []
        var_val = None
        for clause in body:
            if "eval" in clause:
                p = clause["eval"]["a"]["pointer"]
                assert p.startswith("/done/")
                preds.append(p[len("/done/"):])
            elif "pointer/set" in clause:
                p = clause["pointer/set"]; v = clause["value"]
                assert p.startswith("/done/")
                var_val = (p[len("/done/"):], v)
            else:
                raise ValueError(f"unrecognised body clause: {clause}")
        assert aname.startswith("a_")
        parsed[aname[2:]] = {"preds": preds, "var": var_val[0], "val": var_val[1],
                             "duration": duration}

    # topological order derived from preds; ties broken by HTN action order
    names = list(parsed.keys())
    pos = {n: i for i, n in enumerate(names)}
    # each step's preds are already back-references; we trust HTN order
    # is already topological (methods build it that way) and only compute
    # divergence/convergence markers.

    # A step with >= 2 direct successors gets &> right after it.
    # A step with >= 2 direct preds gets &< right before it.
    succs = {n: [] for n in names}
    for n in names:
        for p in parsed[n]["preds"]:
            if p in succs:
                succs[p].append(n)

    # A step X anchors a fan-out group if X has >=2 successors whose sole
    # pred is X. Members carry an empty `when`.
    fanout_members = {}   # child_name -> parent_name
    for parent, children in succs.items():
        single_pred_children = [c for c in children if parsed[c]["preds"] == [parent]]
        if len(single_pred_children) >= 2:
            for c in single_pred_children:
                fanout_members[c] = parent

    S = [["^"]]
    open_fanout_parent = None
    emitted_fanout = set()
    for i, name in enumerate(names):
        info = parsed[name]
        prev = names[i - 1] if i > 0 else None
        # emit &> once, before the first member of a new fanout group
        if name in fanout_members and fanout_members[name] not in emitted_fanout:
            parent = fanout_members[name]
            members = [c for c, p in fanout_members.items() if p == parent]
            S.append(["&>", *members])
            emitted_fanout.add(parent)
            open_fanout_parent = parent
        # emit &< before this step if it has >=2 preds
        fan_in = len(info["preds"]) >= 2
        if fan_in:
            S.append(["&<", *info["preds"]])
            open_fanout_parent = None
        # canonical `when`
        if fan_in or name in fanout_members:
            when = ""
        else:
            drop = prev
            when = " & ".join(f"X.{p}" for p in info["preds"] if p != drop)
        do = f"V.{info['var']}:={1 if info['val'] is True else info['val']}"
        t = duration_from_iso(info["duration"])
        S.append([name, when, do, t])

    grafcet = OrderedDict()
    grafcet["@context"] = {
        "@version": 1.1,
        "grafcet": "https://project-agrafe.github.io/ns/grafcet#",
        "sfc":   {"@id": "grafcet:name"},
        "descr": {"@id": "grafcet:description"},
        "V":     {"@id": "grafcet:internalVariables", "@container": "@index"},
        "S":     {"@id": "grafcet:steps", "@container": "@list"},
        "^":  "grafcet:InitialStep",
        "%":  "grafcet:MacroStep",
        "#":  "grafcet:EnclosingStep",
        "&>": "grafcet:AndDivergence",
        "&<": "grafcet:AndConvergence",
        "|>": "grafcet:OrDivergence",
        "|<": "grafcet:OrConvergence",
        "!>": "grafcet:ForcingOrder",
    }
    grafcet["@type"] = "grafcet:SFC"
    grafcet["sfc"] = htn["name"]
    if "description" in htn:
        grafcet["descr"] = htn["description"]
    grafcet["V"] = dict(init)
    grafcet["S"] = S
    return grafcet


# ---------- semantic equality --------------------------------------------


def _canon(x):
    """Order-insensitive canonical form for eq check. Sorts action-body
    check clauses and dict keys; leaves ordered S array intact."""
    if isinstance(x, dict):
        return {k: _canon(x[k]) for k in sorted(x)}
    if isinstance(x, list):
        return [_canon(v) for v in x]
    return x


def semantic_eq(a, b):
    return _canon(a) == _canon(b)


# ---------- CLI -----------------------------------------------------------


def _load(p):  return json.loads(Path(p).read_text())
def _dump(o, p): Path(p).write_text(json.dumps(o, indent=2) + "\n")


def _main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "lower":
        _dump(lower(_load(argv[2])), argv[3])
    elif cmd == "raise":
        _dump(raise_(_load(argv[2])), argv[3])
    elif cmd == "roundtrip":
        doc = _load(argv[2])
        if "S" in doc:  # grafcet: canonical iff raise(lower(doc)) == doc
            once = raise_(lower(doc))
            twice = raise_(lower(once))
        else:           # htn: canonical iff lower(raise(doc)) == doc
            once = lower(raise_(doc))
            twice = lower(raise_(once))
        canonical = semantic_eq(doc, once)
        idempotent = semantic_eq(once, twice)
        print(f"input canonical: {'yes' if canonical else 'no'}")
        print(f"idempotent:      {'yes' if idempotent else 'NO'}")
        if not idempotent:
            print(json.dumps(twice, indent=2))
            sys.exit(1)
    else:
        print(__doc__); sys.exit(2)


if __name__ == "__main__":
    _main(sys.argv)
