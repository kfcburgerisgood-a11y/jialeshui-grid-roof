"""T-006b: field-data skeleton tests (EPW wind rows, sector histogram, u_wind).

Not a validation of W_eff/H/salt; see grid_roof/fields_io.py and
fields/T-006_epw_wind_sun_spec.md for what remains unverified.
"""
import math

import numpy as np
import pytest

from grid_roof import fields_io as F


@pytest.fixture(scope="module")
def rows():
    assert F.EPW_PATH.exists(), "read-only EPW fixture missing: {}".format(F.EPW_PATH)
    return F.load_epw_wind_rows()


def test_load_epw_wind_rows_reads_full_year(rows):
    # TMYx file is a nominal 8760-hour year; every row has valid wd/ws.
    assert len(rows) == 8760
    for month, wd, ws in rows:
        assert 1 <= month <= 12
        assert 0.0 <= wd < 999
        assert 0.0 <= ws < 999


@pytest.mark.parametrize("season,expected_hours", [
    ("annual", 8725),
    ("winter", 2158),
    ("summer", 2197),
    ("spring", 2189),
    ("autumn", 2181),
])
def test_sector_histogram_hours_match_known_csv(rows, season, expected_hours):
    # Cross-check against fields/T-006_wind_sector_stats.csv (sum of the
    # "hours" column per period), which was produced by the independent
    # fields/T-006_wind_stats.py script from the same EPW.
    hist = F.sector_histogram(rows, season)
    assert sum(b["hours"] for b in hist.values()) == expected_hours


def test_sector_histogram_sums_to_hours_with_wind(rows):
    # Sector totals must equal hours with ws > 0 (calm hours excluded),
    # for every season, not just the ones spot-checked above.
    for season in ("annual", "winter", "spring", "summer", "autumn"):
        hist = F.sector_histogram(rows, season)
        if season == "annual":
            windy = sum(1 for _, _, ws in rows if ws > 0)
        else:
            windy = sum(1 for m, _, ws in rows if ws > 0 and F._season(m) == season)
        assert sum(b["hours"] for b in hist.values()) == windy


def test_sector_histogram_rejects_unknown_season(rows):
    with pytest.raises(ValueError):
        F.sector_histogram(rows, "monsoon")


def test_sector_histogram_zero_fills_missing_sectors():
    hist = F.sector_histogram([(1, 90.0, 5.0)], "annual")
    assert hist["E"] == {"hours": 1, "sum_ws": 5.0}
    assert hist["SW"] == {"hours": 0, "sum_ws": 0.0}
    assert set(hist) == set(F.SECTORS)


def test_u_wind_from_theta_deg_ene_default_is_unit_and_matches_spec():
    u = F.u_wind_from_theta_deg(F.WIND_DEFAULT["theta_deg"])
    assert F.WIND_DEFAULT["sector_label"] == "ENE"
    assert math.isclose(np.linalg.norm(u), 1.0, abs_tol=1e-9)
    # fields/T-006_epw_wind_sun_spec.md §3.1: ENE 67.5 deg -> approx (0.9239, 0.3827, 0)
    assert np.allclose(u, (0.9239, 0.3827, 0.0), atol=1e-4)


@pytest.mark.parametrize("theta_deg,expected_xy", [
    (0.0, (0.0, 1.0)),      # N: purely +Y
    (90.0, (1.0, 0.0)),     # E: purely +X
    (180.0, (0.0, -1.0)),   # S
    (270.0, (-1.0, 0.0)),   # W
])
def test_u_wind_from_theta_deg_known_components(theta_deg, expected_xy):
    u = F.u_wind_from_theta_deg(theta_deg)
    assert u[2] == 0.0
    assert np.allclose(u[:2], expected_xy, atol=1e-9)


def test_sun_vector_ground_to_sun_is_unit_with_positive_z():
    v = F.sun_vector_ground_to_sun(45.0, 180.0)
    assert math.isclose(np.linalg.norm(v), 1.0, abs_tol=1e-9)
    assert v[2] > 0


def test_sun_vector_ground_to_sun_rejects_non_positive_altitude():
    with pytest.raises(ValueError):
        F.sun_vector_ground_to_sun(0.0, 180.0)
    with pytest.raises(ValueError):
        F.sun_vector_ground_to_sun(-5.0, 180.0)
