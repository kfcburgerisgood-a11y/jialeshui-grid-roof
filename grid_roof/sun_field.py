"""T-009: minimal H_am / H_pm smoke test (direct-sun hours, with self-occlusion).

Scope (``ops/tasks/T-009.md``; 總綱 §5.3): ``H_am, H_pm = Sum_k V_k(x) *
I[n.s_k > 0] * dt`` -- morning/afternoon direct-sun hours on a mesh's outer
surface. Reuses ``wind_field``'s sampling/ray machinery
(``sample_outer_surface``, ``triangulate_faces``, ``ray_mesh_occluded``)
unchanged, and ``fields_io.sun_vector_ground_to_sun`` for the
altitude/azimuth -> unit-vector step. Does not touch ``body_shell``,
``body_keep``, ``design``, S/salt, or any opening/void/water rule.

No ``fields/T-009_sun_probe_spec.md`` existed from the parallel 風場 review
at the time this module was written (checked: absent from ``fields/``
alongside ``T-006``/``T-008``'s specs). The locked choices below --
representative days, am/pm clock boundary, time step, coordinates -- are
therefore **Claude's own stand-in assumptions**, not a 風場-reviewed
spec, and are flagged 推定/待風場覆核 in ``ops/reports/T-009.md``. If
``fields/T-009_sun_probe_spec.md`` is added later with different numbers,
treat this module's constants as superseded, not this module's mechanism.

Solar position: a plain closed-form approximation (the widely used
NOAA/Michalsky-style simplified solar-position formulas: fractional-year
angle `gamma`, Fourier series for the equation of time and declination,
then standard hour-angle/zenith/azimuth trig). This is **not** the full
NREL SPA algorithm and **not** Ladybug/Honeybee (CLAUDE.md: no heavy dep
not needed by the task) -- accuracy is on the order of a few hundredths of
a degree in declination, plenty for a smoke test, but not validated here
against an independent solar-position implementation.

Coordinates: 22.006N, 120.845E, UTC+8 -- the same 推定 Jialeshui
coordinates as ``fields/T-006_epw_wind_sun_spec.md`` §1 (station-offset
estimate, not a surveyed site coordinate).
"""
from __future__ import annotations

import math

import numpy as np

from .fields_io import sun_vector_ground_to_sun
from .wind_field import ray_mesh_occluded, sample_outer_surface, triangulate_faces

__all__ = [
    "JIALESHUI_LAT_DEG",
    "JIALESHUI_LON_DEG",
    "JIALESHUI_TZ_HOURS",
    "day_of_year",
    "solar_position",
    "sun_slot_contribution",
    "sun_field",
]

#: 推定 (T-006 §1, same as fields_io/WIND_DEFAULT's station-offset estimate).
JIALESHUI_LAT_DEG = 22.006
JIALESHUI_LON_DEG = 120.845
JIALESHUI_TZ_HOURS = 8.0


def day_of_year(month: int, day: int, year: int = 2026) -> int:
    """1-based day-of-year for a (month, day), default non-leap reference year 2026."""
    import datetime
    return datetime.date(year, month, day).timetuple().tm_yday


def solar_position(day_of_year: float, hour: float,
                    lat_deg: float = JIALESHUI_LAT_DEG,
                    lon_deg: float = JIALESHUI_LON_DEG,
                    tz_hours: float = JIALESHUI_TZ_HOURS):
    """Sun altitude/azimuth (deg) for a given day-of-year and local clock hour.

    Plain NOAA/Michalsky-style simplified algorithm (module docstring).
    ``hour`` is local clock time (0-24, ``tz_hours`` offset from UTC, e.g.
    8.0 for Taiwan). ``azimuth_deg`` is clockwise from north (N=0, E=90),
    the same convention as ``fields_io.sun_vector_ground_to_sun``'s
    ``azimuth_deg`` and the EPW wind-direction convention.

    Returns
    -------
    (altitude_deg, azimuth_deg) : tuple[float, float]
        ``altitude_deg`` may be <= 0 (sun below horizon); callers that feed
        this into ``sun_vector_ground_to_sun`` must check that first.

    Examples
    --------
    >>> alt, az = solar_position(172, 12.0)  # summer solstice, local noon
    >>> alt > 85.0  # near-zenith this close to the Tropic of Cancer
    True
    >>> alt2, az2 = solar_position(355, 12.0)  # winter solstice, local noon
    >>> 40.0 < alt2 < 50.0 and 170.0 < az2 < 190.0  # lower, due south
    True
    """
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour - 12.0) / 24.0)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma)
    )
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    )
    time_offset = eqtime + 4.0 * lon_deg - 60.0 * tz_hours
    true_solar_time = hour * 60.0 + time_offset
    hour_angle_deg = true_solar_time / 4.0 - 180.0

    lat = math.radians(lat_deg)
    ha = math.radians(hour_angle_deg)

    cos_zenith = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.acos(cos_zenith)
    altitude_deg = 90.0 - math.degrees(zenith)

    sin_zenith = math.sin(zenith)
    if abs(sin_zenith) < 1e-9:
        azimuth_deg = 180.0  # sun at/near zenith or nadir: azimuth undefined, pick a stable fallback
    else:
        cos_az = (math.sin(lat) * cos_zenith - math.sin(decl)) / (math.cos(lat) * sin_zenith)
        cos_az = max(-1.0, min(1.0, cos_az))
        az_acos_deg = math.degrees(math.acos(cos_az))
        if hour_angle_deg > 0.0:
            azimuth_deg = (az_acos_deg + 180.0) % 360.0
        else:
            azimuth_deg = (540.0 - az_acos_deg) % 360.0

    return altitude_deg, azimuth_deg


def sun_slot_contribution(points, normals, vertices, triangles,
                           altitude_deg, azimuth_deg, dt_hours, eps=1e-3):
    """H contribution (h) for one sun position: ``dt_hours`` where facing and unoccluded, else 0.

    Implements ``V_k(x) * I[n.s_k > 0] * Delta t`` for a single time slot.
    Below-horizon (``altitude_deg <= 0``) returns all-zero, matching
    ``sun_vector_ground_to_sun``'s altitude > 0 requirement.
    """
    n = len(points)
    if altitude_deg <= 0.0:
        return np.zeros(n)

    s_k = np.array(sun_vector_ground_to_sun(altitude_deg, azimuth_deg))
    facing = (normals @ s_k) > 0.0
    origins = points + eps * normals
    occluded = ray_mesh_occluded(origins, s_k, vertices, triangles)
    visible = facing & ~occluded
    return np.where(visible, dt_hours, 0.0)


def sun_field(mesh, day_of_year_value, dt_hours=0.5,
              am_hours=(6.0, 12.0), pm_hours=(12.0, 18.0),
              lat_deg=JIALESHUI_LAT_DEG, lon_deg=JIALESHUI_LON_DEG,
              tz_hours=JIALESHUI_TZ_HOURS, eps=1e-3):
    """H_am, H_pm (h) on ``mesh``'s outer face samples, for one representative day.

    Samples local clock hours ``[am_hours[0], am_hours[1])`` and
    ``[pm_hours[0], pm_hours[1])`` every ``dt_hours``, summing
    ``sun_slot_contribution`` per slot. The am/pm boundary is **local clock
    noon**, a Claude 推定 choice (no 風場 spec exists to fix it otherwise --
    see module docstring); true-solar-noon would differ slightly (±tens of
    minutes depending on ``day_of_year_value``/``lon_deg``) and is not what
    this uses.

    Returns
    -------
    dict
        ``points``, ``normals`` (mm, unit), ``H_am``, ``H_pm`` (h, one row
        per face sample), plus the day/dt/hours/coords actually used.
    """
    points, normals = sample_outer_surface(mesh)
    vertices, triangles = triangulate_faces(mesh)
    n = len(points)
    H_am = np.zeros(n)
    H_pm = np.zeros(n)

    for hour in np.arange(am_hours[0], am_hours[1], dt_hours):
        altitude_deg, azimuth_deg = solar_position(day_of_year_value, float(hour), lat_deg, lon_deg, tz_hours)
        H_am += sun_slot_contribution(points, normals, vertices, triangles, altitude_deg, azimuth_deg, dt_hours, eps)
    for hour in np.arange(pm_hours[0], pm_hours[1], dt_hours):
        altitude_deg, azimuth_deg = solar_position(day_of_year_value, float(hour), lat_deg, lon_deg, tz_hours)
        H_pm += sun_slot_contribution(points, normals, vertices, triangles, altitude_deg, azimuth_deg, dt_hours, eps)

    return dict(
        points=points, normals=normals, H_am=H_am, H_pm=H_pm,
        day_of_year=day_of_year_value, dt_hours=dt_hours,
        am_hours=am_hours, pm_hours=pm_hours,
        lat_deg=lat_deg, lon_deg=lon_deg, tz_hours=tz_hours, eps_mm=eps,
    )
