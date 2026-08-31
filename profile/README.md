<!--
  The visitor arrives here having come through the shuttle's front door
  ("THE STUDIO & THE SHUTTLE"). This page is the workshop behind that
  door. Match the diegesis: warm, generic vocabulary, no trademarks,
  no counting announcements, no em-dash joins.
-->

# Weftspun

A workshop that turns a language prompt into a portable character you
can carry into a world. If you came in through the shuttle, this is
the room behind the wall.

## The ladder, as repositories

The pipeline is a ladder of small working systems (RFD 2136). Each
rung is a repository you can open on its own:

| Rung | What it does | Repository |
|--:|---|---|
| 0 | text becomes an image | (upstream, folded in by the ladder) |
| 1 | image becomes a mesh | [interactor-pixal3d-image-to-textured-mesh](https://github.com/weftspun/interactor-pixal3d-image-to-textured-mesh) |
| 2 | the mesh is judged | [interactor-editscore](https://github.com/weftspun/interactor-editscore) |
| 3 | the mesh is repaired | [interactor-voxhammer-image-mesh-editing](https://github.com/weftspun/interactor-voxhammer-image-mesh-editing) |
| 4 | the mesh is rigged | [interactor-skintokens-auto-rig](https://github.com/weftspun/interactor-skintokens-auto-rig) |
| 5 | the parts are tagged | recovered by rungs 2 + 3 against the canonical partition |
| 6 | the file is assembled | [interactor-shuttle](https://github.com/weftspun/spot-broker) (formerly spot-broker; RFD 2138) |
| 7 | a pool is generated | brokered on the shuttle |
| 8 | a stranger rolls one | served by the shuttle |
| 9 | it is public | hosted alongside a disclosure page |

## The workshop's foundations

- [request-for-discussion](https://github.com/weftspun/request-for-discussion) is the record: every decision, every measurement, every retraction. The rendered site is at [weftspun.github.io/request-for-discussion](https://weftspun.github.io/request-for-discussion/).
- [weftspun-keypoint](https://github.com/weftspun/weftspun-keypoint) is the manifest. It lists which repository sits on which side of the hexagon and which revision the workspace pins.
- [datasource-store](https://github.com/weftspun/datasource-store) is a SQLite whose pages live in a FoundationDB cluster. The shuttle's ledger rides it.
- [pose-consensus](https://github.com/weftspun/interactor-pose-consensus) is the four-estimator agreement gate: a keypoint set is accepted only when independent estimators agree, and disagreement is a fault rather than an average.

## What you can do here

- Read a specific RFD directly, or the [book export (EPUB and PDF)](https://weftspun.github.io/request-for-discussion/) at the bottom of the site.
- Watch [request-for-discussion](https://github.com/weftspun/request-for-discussion/subscription) for notifications when a decision changes.
- Open an issue on the repository whose rung you found a problem with.

## The visual language of these pages

Serif display (Cinzel) over a serif body (Cormorant Garamond), with
JetBrains Mono for numbers. Parchment panels sit inside a deep-indigo
ground. The chrome is inline SVG with beveled gold corners; no
JavaScript, no framework, one Google Font link. It matches the
shuttle's front door because the workshop and the shuttle are one
place viewed from two sides.
