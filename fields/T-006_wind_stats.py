"""T-006: seasonal wind sector stats from EPW. Re-runnable; not grid_roof code."""
from __future__ import annotations
import csv
import sys
from pathlib import Path

SECTORS = ["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
DEFAULT_EPW = Path(__file__).resolve().parent.parent / "epw" / "TWN_SOR_Hengchun.595590_TMYx.2011-2025.epw"

def sector(wd: float) -> int:
    return int(((wd + 11.25) % 360) / 22.5)

def season(m: int) -> str:
    if m in (12, 1, 2):
        return "winter"
    if m in (6, 7, 8):
        return "summer"
    if m in (3, 4, 5):
        return "spring"
    return "autumn"

def load_rows(epw: Path):
    rows = []
    location = None
    with epw.open() as f:
        for line in f:
            if line.startswith("LOCATION"):
                location = line.strip()
                continue
            parts = line.strip().split(",")
            if len(parts) < 22 or not parts[0].lstrip("-").isdigit():
                continue
            try:
                m = int(parts[1])
                wd = float(parts[20])
                ws = float(parts[21])
            except ValueError:
                continue
            if wd >= 999 or ws >= 999:
                continue
            rows.append((m, wd, ws))
    return location, rows

def main(epw: Path, out_csv: Path) -> None:
    location, rows = load_rows(epw)
    periods = ("annual", "winter", "summer", "spring", "autumn")
    acc = {p: {i: {"hours": 0, "sum_ws": 0.0} for i in range(16)} for p in periods}
    for m, wd, ws in rows:
        if ws <= 0:
            continue
        i = sector(wd)
        for p in ("annual", season(m)):
            acc[p][i]["hours"] += 1
            acc[p][i]["sum_ws"] += ws
    with out_csv.open("w", newline="") as cf:
        w = csv.writer(cf)
        w.writerow(["period", "sector", "hours", "sum_ws", "mean_ws", "pct_hours"])
        for p in periods:
            total = sum(acc[p][i]["hours"] for i in range(16)) or 1
            for i in range(16):
                h = acc[p][i]["hours"]
                s = acc[p][i]["sum_ws"]
                mean = (s / h) if h else 0.0
                w.writerow([p, SECTORS[i], h, f"{s:.1f}", f"{mean:.3f}", f"{100 * h / total:.2f}"])
    print("LOCATION:", location)
    print("wrote", out_csv)
    print("n_hours", len(rows))

if __name__ == "__main__":
    epw = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EPW
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).with_name("T-006_wind_sector_stats.csv")
    main(epw, out)
