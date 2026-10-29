"""T-006b: minimal, testable EPW wind/sun field I/O.

Scope: a field-data skeleton, not a verified environmental field. Does not
touch ``body.py``, ``keep``, or ``design.py``.

Conventions (see ``fields/T-006_epw_wind_sun_spec.md`` §3.1 for the full
table):

- EPW wind direction ``theta`` is where the wind comes FROM: N=0, E=90,
  clockwise, same as the raw EPW column.
- ``u_wind`` is a unit vector pointing toward the wind's *source*. In this
  project's Rhino world (X=east, Y=north): ``u_wind = (sin(theta), cos(theta), 0)``.
  Getting this backwards (pointing where the wind blows *to*) flips every
  downstream ``W = max(0, n . u_wind)`` sign.
- ``s_k`` points from the ground to the sun; only altitude > 0 is used.

Locked default (歐郎, 2026-10-29, ``ops/tasks/T-006b.md``, "跟舊圖走" / 選項
C): a single ``u_wind`` at theta=67.5 (ENE), matching the earlier drawing
and 總綱 §5.1. This is carried over as an ASSUMPTION, not re-derived from
the EPW. It conflicts with this EPW's own summer statistics -- see
``WIND_DEFAULT["conflict"]`` below and
``fields/T-006_epw_wind_sun_spec.md`` §2.3 -- which show no single summer
peak (W > E > ENE > WSW by hours). That conflict is accepted as a known,
flagged assumption, not resolved here.

Nothing in this module should be read as validating W_eff, H_am/H_pm, S,
or salt -- those remain unverified (see module docstring of
``fields/T-006_epw_wind_sun_spec.md`` §5).
"""
from __future__ import annotations

import math
from pathlib import Path

__all__ = [
    "EPW_PATH",
    "SECTORS",
    "WIND_DEFAULT",
    "load_epw_wind_rows",
    "sector_histogram",
    "u_wind_from_theta_deg",
    "sun_vector_ground_to_sun",
]

#: Read-only EPW source for T-006/T-006b (恆春 595590 TMYx 2011-2025).
EPW_PATH = Path("/workspace/jialeshui/epw/TWN_SOR_Hengchun.595590_TMYx.2011-2025.epw")

#: 16-point compass, matching fields/T-006_wind_stats.py and the CSV it writes.
SECTORS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

#: Meteorological-season month grouping, same as fields/T-006_wind_stats.py.
_SEASON_MONTHS = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}

#: Single locked u_wind default -- an assumption, not a verified field.
WIND_DEFAULT = {
    "theta_deg": 67.5,
    "sector_label": "ENE",
    "basis": "舊圖＋總綱 §5.1；2026-10-29 歐郎鎖定選項 C（ops/tasks/T-006b.md）",
    "conflict": (
        "推定：本 EPW 夏季統計（fields/T-006_wind_sector_stats.csv, period=summer）"
        "有風時數主峰為 W(16.6%) > E(14.8%) > ENE(14.1%) > WSW(11.6%)，並非單一 ENE 峰；"
        "此預設沿用舊圖，未對齊夏季 EPW，亦未經基地現場驗證。"
    ),
}


def _season(month: int) -> str:
    return _SEASON_MONTHS[int(month)]


def load_epw_wind_rows(path: Path | str = EPW_PATH):
    """Read hourly ``(month, wind_dir_deg, wind_speed_m_s)`` rows from an EPW file.

    Read-only: opens ``path`` for reading only, never writes it. Column
    layout and the wd/ws >= 999 missing-value rule mirror
    ``fields/T-006_wind_stats.py:load_rows`` so results stay comparable with
    ``fields/T-006_wind_sector_stats.csv``.

    Parameters
    ----------
    path : path-like
        EPW file. Defaults to ``EPW_PATH`` (恆春 595590 TMYx).

    Returns
    -------
    list[tuple[int, float, float]]
        ``(month, wind_direction_deg, wind_speed_m_s)`` for every hour with
        valid (< 999) direction and speed.
    """
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("LOCATION"):
                continue
            parts = line.strip().split(",")
            if len(parts) < 22 or not parts[0].lstrip("-").isdigit():
                continue
            try:
                month = int(parts[1])
                wd = float(parts[20])
                ws = float(parts[21])
            except ValueError:
                continue
            if wd >= 999 or ws >= 999:
                continue
            rows.append((month, wd, ws))
    return rows


def sector_histogram(rows, season: str = "annual"):
    """Aggregate ``(month, wd, ws)`` rows into the 16-sector wind histogram.

    Matches the method in ``fields/T-006_wind_sector_stats.csv``: hours with
    ``ws <= 0`` are excluded from the sector sums (calm hours don't carry a
    direction), sectors are 22.5 degree wide centred on each compass point.

    Parameters
    ----------
    rows : iterable of (month, wd, ws)
        As returned by :func:`load_epw_wind_rows`.
    season : str
        One of ``"annual"``, ``"winter"``, ``"spring"``, ``"summer"``,
        ``"autumn"``. ``"annual"`` takes every row regardless of month.

    Returns
    -------
    dict[str, dict]
        ``{sector_label: {"hours": int, "sum_ws": float}}`` for all 16
        sectors (zero-filled if a sector saw no hours).
    """
    if season != "annual" and season not in set(_SEASON_MONTHS.values()):
        raise ValueError("Unknown season: {!r}".format(season))
    acc = {label: {"hours": 0, "sum_ws": 0.0} for label in SECTORS}
    for month, wd, ws in rows:
        if ws <= 0:
            continue
        if season != "annual" and _season(month) != season:
            continue
        i = int(((wd + 11.25) % 360) / 22.5)
        bucket = acc[SECTORS[i]]
        bucket["hours"] += 1
        bucket["sum_ws"] += ws
    return acc


def u_wind_from_theta_deg(theta_deg: float):
    """Unit vector pointing toward the wind's source, for EPW direction theta.

    ``theta_deg`` is degrees clockwise from north (N=0, E=90), the raw EPW
    wind-direction convention. In this project's Rhino world (X=east,
    Y=north): ``u_wind = (sin(theta), cos(theta), 0)`` -- see
    ``fields/T-006_epw_wind_sun_spec.md`` §3.1. This function only converts
    an angle to a vector; it does not choose which theta to use (see
    ``WIND_DEFAULT`` for the locked default).

    Examples
    --------
    >>> import numpy as np
    >>> u = u_wind_from_theta_deg(WIND_DEFAULT["theta_deg"])  # ENE, 67.5 deg
    >>> np.allclose(u, (0.9238795325112867, 0.3826834323650898, 0.0))
    True
    >>> round(float(np.linalg.norm(u)), 9)
    1.0
    """
    theta = math.radians(theta_deg)
    return (math.sin(theta), math.cos(theta), 0.0)


def sun_vector_ground_to_sun(altitude_deg: float, azimuth_deg: float):
    """Unit vector from the ground to the sun, given altitude and azimuth.

    Plain-trig construction of ``s_k`` from a known solar position; it does
    **not** compute the solar position itself (time-of-day/year ->
    altitude/azimuth), since no Ladybug/Honeybee dependency is installed
    for this task (CLAUDE.md: don't add heavy deps not needed by the task).
    ``azimuth_deg`` uses the same clockwise-from-north convention as the
    wind theta above (N=0, E=90).

    Per spec (``fields/T-006_epw_wind_sun_spec.md`` §3.1), ``s_k`` only takes
    altitude > 0; this raises ``ValueError`` otherwise rather than silently
    returning a below-horizon vector.

    Ladybug reversal risk (documented, **not verified against Ladybug
    output** by this task): ``ladybug.sunpath.Sun.sun_vector`` is commonly
    reported as pointing FROM the sun TO the ground (z usually negative).
    If this stub is ever replaced by a Ladybug-derived vector, check the
    sign first (e.g. z > 0 at local solar noon) and negate if needed to
    keep the ground-to-sun / z>0 convention this module and ``s_k`` use.
    Do not assume that check has already been done.

    Examples
    --------
    >>> import numpy as np
    >>> v = sun_vector_ground_to_sun(45.0, 180.0)  # due south, 45 deg up
    >>> round(float(np.linalg.norm(v)), 9)
    1.0
    >>> v[2] > 0
    True
    """
    if altitude_deg <= 0:
        raise ValueError(
            "sun_vector_ground_to_sun only takes altitude_deg > 0 "
            "(fields/T-006_epw_wind_sun_spec.md §3.1)"
        )
    alt = math.radians(altitude_deg)
    az = math.radians(azimuth_deg)
    horizontal = math.cos(alt)
    return (horizontal * math.sin(az), horizontal * math.cos(az), math.sin(alt))
