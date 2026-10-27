"""Make pieces of the roof printable, as samples for a Prusa CORE One L or XL.

    uv run python print_sample.py --list                        # every piece, its printed size, whether it fits
    uv run python print_sample.py panel_0_1_00                  # prints/panel_0_1_00-1to20.stl and .txt
    uv run python print_sample.py panel_0_1_00 panel_0_1_01     # neighbours: their pins and sockets meet
    uv run python print_sample.py beam_x1_0_0 --scale 25 --printer xl

Reads brief.json and drawing.json when present, as build.py does. A panel at 1:20
takes about three minutes and 2.6 GB. Then slice the STL: docs/print.md.
"""

import argparse
import os
import time

import grid_roof as roof
from compas_vol.meshing import is_watertight, write_stl
from grid_roof.printing import PRINTERS

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pieces", nargs="*", help="piece names, from --list")
    parser.add_argument("--list", action="store_true", help="list the pieces, their printed size and fit")
    parser.add_argument("--scale", type=float, default=20.0, help="1:SCALE (default 20)")
    parser.add_argument("--printer", choices=sorted(PRINTERS), default="core-one-l", help="default core-one-l")
    parser.add_argument("--voxel", type=float, help="sample spacing in mm at full size (default: 0.6 mm printed)")
    parser.add_argument("--out", default=os.path.join(HERE, "prints"), help="folder for the STL and report")
    parser.add_argument("--brief", default=os.path.join(HERE, "brief.json"))
    parser.add_argument("--drawing", default=os.path.join(HERE, "drawing.json"))
    args = parser.parse_args()
    if not args.pieces and not args.list:
        parser.error("name at least one piece, or --list them")

    brief = roof.Brief.load(args.brief) if os.path.exists(args.brief) else roof.Brief()
    drawing = roof.Drawing.load(args.drawing) if os.path.exists(args.drawing) else roof.Drawing.sample()
    built = roof.design_roof(brief, drawing)
    bed = PRINTERS[args.printer]

    if args.list:
        print("{:<14} {:>22}  fits the {}".format("piece", "at 1:{:g}, mm".format(args.scale), args.printer))
        for piece in built.assembly:
            x, y, z = (v / args.scale for v in piece.size)
            fits = z <= bed[2] and ((x <= bed[0] and y <= bed[1]) or (x <= bed[1] and y <= bed[0]))
            print("{:<14} {:>6.0f} x {:>4.0f} x {:>4.0f}  {}".format(piece.name, x, y, z, "yes" if fits else "no"))

    os.makedirs(args.out, exist_ok=True)
    for name in args.pieces:
        started = time.time()
        printable = roof.printing.sample(brief, built.design, built.weathering, name, scale=args.scale,
                                         voxel=args.voxel, printer=args.printer)
        stem = os.path.join(args.out, "{}-1to{:g}".format(name, args.scale))
        write_stl(stem + ".stl", printable.vertices, printable.faces, name=name)
        summary = printable.summary()
        watertight = is_watertight(printable.vertices, printable.faces)
        with open(stem + ".txt", "w", encoding="utf-8") as f:
            f.write(summary + "\nwatertight     : {}\n".format(watertight))
        print(summary)
        print("watertight     : {}".format(watertight))
        print("wrote {}.stl and .txt in {:.0f}s\n".format(os.path.relpath(stem, HERE), time.time() - started))


if __name__ == "__main__":
    main()
