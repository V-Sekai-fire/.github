# weftfit

Intersection-free garment retargeting for user-made 3D worlds.

Refits a garment authored for one body onto a different avatar without the cloth
intersecting the body — a PolyFEM-based solve that respects skeleton
correspondence and stays collision-free, shipped as self-contained Elixir
binaries over OpenUSD. Built for [V-Sekai](https://v-sekai.org).

weftfit is a **hexagonal cluster** (core / ports / adapters): a pure solver core
defines narrow C-ABI port contracts, and adapters bind real I/O. One port admits
many adapters, so a single solve fans out to several destinations from one pass.

- **[retarget](https://github.com/weftfit/retarget)** — the garment-retargeting **core** + port contracts (`mesh_source` / `mesh_sink`)
- **[stage](https://github.com/weftfit/stage)** — scene-description (OpenUSD) source+sink **adapter** (via `stage_runtime`)
- **[obj](https://github.com/weftfit/obj)** — Wavefront OBJ source+sink **adapter**
- **[cli](https://github.com/weftfit/cli)** — driving **adapter**: Elixir + Fine NIF, packaged as a Burrito binary
- **viewer** — output **adapter** for QA visualization (planned)

Naming avoids the OpenUSD trademark in repo/package names (kept only in descriptions and build flags), following `stage_runtime`.
