# Print

A sample is one piece of the kit at a scale, made printable: nothing thinner than 1.2 mm,
pins with 0.2 mm of play, and the piece the way it is built, soffit on the plate. It is
checked for a 0.4 mm nozzle on a Prusa CORE One L (300 × 300 × 330 mm) or a Prusa XL
(360 mm cube).

## 1 · Make the STL

In the `grid-roof` folder:

```bash
uv run python print_sample.py --list                    # every piece: printed size, and whether it fits
uv run python print_sample.py panel_0_1_00              # prints/panel_0_1_00-1to20.stl, and a .txt report
uv run python print_sample.py panel_0_1_00 --printer xl # checked against the XL
```

`--scale 25` prints smaller. The same is Step 15 in the notebook (`PRINT = True` in
Step 1). It uses your `brief.json` and `drawing.json` when they are there.

At 1:20, measured on the CORE One L with the settings below:

| Piece | Printed size | Making the STL | Printing | PLA |
|---|---|---|---|---|
| a node, `node_1_1` | 34 × 34 × 29 mm | 20 s | 28 min | 10 g |
| a beam, `beam_x1_0_0` | 259 × 34 × 30 mm | 1.5 min | 2 h 27 min | 71 g |
| a panel, `panel_0_1_00` | 154 × 154 × 30 mm | 3 min, 2.6 GB of memory | 4 h 32 min | 102 g |

Print a node first: it is quick, and it tells you whether the settings are right.

## 2 · Read the report

`prints/<piece>-1to20.txt` says what the slicer will meet:

| Line | Expect | If not |
|---|---|---|
| `fits` | yes | a larger scale number, or `--printer xl` |
| `wall thickness` | 0.0% under 1.2 mm | thin walls are removed already; rebuild if it is not 0 |
| `watertight` | True | rebuild; if it stays False, add `--voxel 16` |
| `sealed cavities` | 0 | harmless on these printers: it prints as a closed air pocket |
| `overhang`, `mid-air starts`, `unsupported` | some, for a panel | normal: the pores' ceilings print as overhangs |
| `verdict` | *ready* for nodes and beams; for a panel, the overhang lines above | print it |

## 3 · Slice in PrusaSlicer

1. Install [PrusaSlicer](https://www.prusa3d.com/page/prusaslicer_424/) 2.9 or newer. On
   first start the wizard asks for printers: under *Prusa Research* tick **CORE One L**
   or **XL**, with the 0.4 mm nozzle.
2. On the right, choose:

   | | CORE One L | XL |
   |---|---|---|
   | Printer | Prusa CORE One L 0.4 nozzle | Original Prusa XL Input Shaper 0.4 nozzle |
   | Print settings | 0.20mm STRUCTURAL | 0.20mm STRUCTURAL |
   | Filament | Generic PLA, or the PLA loaded | Generic PLA, or the PLA loaded |
   | Supports | Support on build plate only | Support on build plate only |
   | Infill | 15% | 15% |

3. *File › Import › Import STL* (Ctrl+I). It arrives at print size, in mm, the right way up:
   do not scale or rotate it.
4. *Slice now* (Ctrl+R). The preview shows the time and filament; they should be close to
   the table above. PrusaSlicer adds supports only where it needs them; for these pieces it
   adds none.
5. *Export G-code* (Ctrl+G) to a USB stick, or send it with Prusa Connect.

## 4 · After printing

- Pieces fit together. The piece on the low side of each cut carries 3 mm pins, its
  neighbour the sockets. Print two neighbours to try them:
  `print_sample.py panel_0_1_00 panel_0_1_01`.
- Joint faces stand 0.5 mm apart at 1:20: the roof's 10 mm gap.
- Keep STLs and G-code out of the repository; `.gitignore` leaves out `prints/`.

## From a terminal

The same slice, without opening PrusaSlicer (macOS; on Windows use
`prusa-slicer-console.exe` in PrusaSlicer's folder):

```bash
/Applications/PrusaSlicer.app/Contents/MacOS/PrusaSlicer --export-gcode \
  --printer-profile "Prusa CORE One L 0.4 nozzle" \
  --print-profile "0.20mm STRUCTURAL @COREONEL 0.4" \
  --material-profile "Generic PLA @COREONE" \
  --support-material --support-material-buildplate-only \
  --output prints/panel_0_1_00-1to20.bgcode prints/panel_0_1_00-1to20.stl
```

For the XL: `"Original Prusa XL Input Shaper 0.4 nozzle"`, `"0.20mm STRUCTURAL @XLIS 0.4"`
and `"Generic PLA @XLIS"`.
