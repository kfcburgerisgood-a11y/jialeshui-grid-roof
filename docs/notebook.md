# Notebook

`walkthrough.ipynb` is the design written out step by step, laid out like a Grasshopper
definition: one cell per group of components, with the code as the parameters.

```bash
uv run jupyter lab walkthrough.ipynb
```

## M2 body_shell entry (T-005)

Open `body_walkthrough.ipynb` and set `SOURCE = "body_shell"` (default) or
`SOURCE = "slab"`. Both call `roof.design_roof`; the body branch passes
`body_mesh=mesh` and stops at design with a separate inner backplate keep.
`walkthrough.ipynb` remains the complete slab fabrication walkthrough.

The body preview loads the existing `inputs/body_a.obj` test box in mm and
centres it to exercise negative coordinates. Its sections and checks use the
mesh bbox, not `brief.bounds`. An already-mm closed mesh can be substituted.
The metre-unit SubD STL still needs the file-specific conversion in
`scripts/m2_subd.py`; `load_body` does no scaling.

`Brief(body_thickness=300, b_min=100, voxel=100)` uses provisional preview
thicknesses in mm. The keep band is `-T <= field <= -(T-b_min)` on the inside
of the shell. The check reports source-grid spacing, kept sample count and
missing material. It does not verify physical backplate thickness or margin;
thin curved shells and T=300 remain unverified. Slab water, openings, pores,
kit and weathering are not connected to the body route by this task.

Reproduce the recorded diagnostic run with:

```bash
uv run python scripts/m2_design.py 100 <new-run-id>
```

## Jupyter in brief

| To | Do |
|---|---|
| run a cell | click it, Shift+Enter |
| run everything | *Run › Run All Cells* |
| start again clean | *Kernel › Restart Kernel and Run All Cells* |
| stop a long cell | the ■ button |
| undo all your changes to the notebook | `git restore walkthrough.ipynb` |

Cells run in order and remember what earlier cells made: after a change, rerun from that
cell down.

## Working in it

- **Change a number, rerun from the step that reads it.** The brief is Step 1; each step's
  function lists the fields it reads (`help(roof.soffit)`).
- **Most steps end with Try:** one change, and what to look for.
- **Edit `grid_roof` and keep the kernel:** run this once at the top, and changes to the
  package are picked up on the next run of a cell:

  ```python
  %load_ext autoreload
  %autoreload 2
  ```

- **Resolution:** `voxel=40` is for looking and takes seconds; 10 to 15 mm is for making,
  in [build](build.md) and [print](print.md).
- **The switches in Step 1:** `RUN_ALL = True` builds all 53 pieces, about two minutes;
  `EXPORT = True` writes them to `out/`; `PRINT = True` builds a sample to print in Step 15.
- **Hand-off:** Step 14 saves `brief.json`; `build.py` and `print_sample.py` read it with
  `drawing.json`.

## Steps

| Step | Shows |
|---|---|
| 0 | what is installed |
| 1–2 | the brief and the drawing |
| 3–8 | the design: beams, water, slab, soffit, light and planters, what must stay |
| 9 | the checks for light and water |
| 10 | the kit of parts, and what each piece costs to sample |
| 11–13 | one piece weathered, inspected and meshed; then piece by piece |
| 14 | the hand-off to `build.py` |
| 15 | a sample to print ([print](print.md)) |
