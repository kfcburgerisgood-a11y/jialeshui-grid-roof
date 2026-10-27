# M2 body (branch `m2-body`)

New: `grid_roof/body.py` — closed mesh → `VolGrid.from_mesh` → `Shell(T, side=1.0)` (inward) → `design_body(shell)` → `design.design(...)`.
The flat-slab path (`design_roof`, `slab()`, `brief.thickness`) is unchanged.

## Input
`inputs/body_a.obj`: **test mesh, not an authored SubD** — closed box 10000×6000×4000 mm, origin at corner, no overhang.

## Provisional parameters (推定, §8 item 6 undecided)
- Shell T = 300 mm, side = 1.0 (inward)
- voxel = 40 mm → padding 400 mm → resolution = ceil((10000+800)/40) = **270** samples on the longest axis
- pytest uses voxel 100 mm for speed

## Run
    uv sync --group dev
    uv run python scripts/m2_body.py [run_id]   # writes inputs/body_a.obj if missing, docs/m2_body_section_y3000.png, appends runs.csv
    uv run --group dev python -m pytest tests/test_body.py

Run on the box (Linux), about 1175 s at voxel 40. Not run in Rhino.

## Limits
`design_body` only feeds the shell into `design()` as solid/porous/keep, with empty voids.
`water`, `soffit` (pores), `voids` (openings/planters), `keep`, `kit` and `weathering` still assume a flat slab:
a height field over `brief.length × brief.width` and depth `brief.thickness`, and `weathering` reads `slab.deck.height_at`.
They are out of scope this round (M3–M8), so `design_roof` does not run on a body.
