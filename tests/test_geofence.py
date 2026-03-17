"""
SVIES — Geofence Module Unit Tests
Tests the geofencing engine in modules/geofence.py.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.geofence import (
    check_zone,
    get_all_zones,
    get_zone_center,
    get_priority_multiplier,
    PRIORITY_MULTIPLIERS,
    ZoneResult,
)


# ══════════════════════════════════════════════════════════
# Priority Multiplier values
# ══════════════════════════════════════════════════════════

class TestPriorityMultipliers:

    def test_school_multiplier(self):
        assert get_priority_multiplier("SCHOOL") == 1.5

    def test_hospital_multiplier(self):
        assert get_priority_multiplier("HOSPITAL") == 1.5

    def test_govt_multiplier(self):
        assert get_priority_multiplier("GOVT") == 1.3

    def test_low_emission_multiplier(self):
        assert get_priority_multiplier("LOW_EMISSION") == 1.2

    def test_highway_multiplier(self):
        assert get_priority_multiplier("HIGHWAY") == 1.4

    def test_unknown_type_returns_1(self):
        assert get_priority_multiplier("UNKNOWN") == 1.0
        assert get_priority_multiplier("") == 1.0
        assert get_priority_multiplier("RANDOM_TYPE") == 1.0

    def test_case_insensitive(self):
        assert get_priority_multiplier("school") == 1.5
        assert get_priority_multiplier("School") == 1.5
        assert get_priority_multiplier("SCHOOL") == 1.5


# ══════════════════════════════════════════════════════════
# Zone loading
# ══════════════════════════════════════════════════════════

class TestZoneLoading:

    def test_zones_loaded(self):
        zones = get_all_zones()
        assert len(zones) == 14, f"Expected 14 zones, got {len(zones)}"

    def test_zones_have_required_fields(self):
        zones = get_all_zones()
        for zone in zones:
            assert "id" in zone, f"Zone missing 'id'"
            assert "name" in zone, f"Zone missing 'name'"
            assert "type" in zone, f"Zone missing 'type'"
            assert "priority" in zone, f"Zone missing 'priority'"
            assert "polygon" in zone, f"Zone missing 'polygon'"

    def test_zones_have_valid_polygon(self):
        zones = get_all_zones()
        for zone in zones:
            polygon = zone["polygon"]
            assert len(polygon) >= 3, f"Zone {zone['id']} has < 3 polygon points"

    def test_zone_types_are_known(self):
        known_types = {"SCHOOL", "HOSPITAL", "GOVT", "LOW_EMISSION", "HIGHWAY"}
        zones = get_all_zones()
        for zone in zones:
            assert zone["type"] in known_types, f"Unknown zone type: {zone['type']}"

    def test_returns_copy(self):
        """get_all_zones() should return a copy, not the internal list."""
        z1 = get_all_zones()
        z2 = get_all_zones()
        assert z1 is not z2


# ══════════════════════════════════════════════════════════
# check_zone — point inside/outside
# ══════════════════════════════════════════════════════════

class TestCheckZone:

    def test_point_outside_all_zones(self):
        result = check_zone(0.0, 0.0)
        assert result is None

    def test_point_far_away(self):
        result = check_zone(48.8566, 2.3522)  # Paris, France
        assert result is None

    def test_point_inside_jntu_school(self):
        """JNTU campus: polygon corners [78.49-78.4958, 17.488-17.4935]."""
        # Center of JNTU polygon: lon≈78.4929, lat≈17.49075
        result = check_zone(17.4910, 78.4930)
        assert result is not None
        assert result.zone_id == "SCHOOL_JNTU"
        assert result.zone_type == "SCHOOL"
        assert result.priority == "HIGH"

    def test_point_inside_nims_hospital(self):
        """NIMS Hospital: polygon corners [78.472-78.4772, 17.4175-17.421]."""
        result = check_zone(17.4193, 78.4746)
        assert result is not None
        assert result.zone_id == "HOSPITAL_NIMS"
        assert result.zone_type == "HOSPITAL"

    def test_point_inside_secretariat(self):
        """Telangana Secretariat: [78.471-78.477, 17.406-17.411]."""
        result = check_zone(17.4085, 78.4740)
        assert result is not None
        assert result.zone_id == "GOVT_SECRETARIAT"
        assert result.zone_type == "GOVT"

    def test_point_inside_charminar_low_emission(self):
        """Charminar Heritage: [78.47-78.479, 17.356-17.363]."""
        result = check_zone(17.3595, 78.4745)
        assert result is not None
        assert result.zone_id == "LOW_EMISSION_CHARMINAR"
        assert result.zone_type == "LOW_EMISSION"

    def test_point_inside_orr_highway(self):
        """ORR Gachibowli: [78.34-78.356, 17.438-17.445]."""
        result = check_zone(17.4415, 78.3480)
        assert result is not None
        assert result.zone_id == "HIGHWAY_ORR_GACHIBOWLI"
        assert result.zone_type == "HIGHWAY"

    def test_result_type(self):
        """check_zone returns ZoneResult or None."""
        result = check_zone(17.4910, 78.4930)
        if result is not None:
            assert isinstance(result, ZoneResult)


# ══════════════════════════════════════════════════════════
# get_zone_center
# ══════════════════════════════════════════════════════════

class TestGetZoneCenter:

    def test_known_zone_returns_tuple(self):
        center = get_zone_center("SCHOOL_JNTU")
        assert center is not None
        lat, lon = center
        assert 17.48 < lat < 17.50
        assert 78.48 < lon < 78.50

    def test_unknown_zone_returns_none(self):
        center = get_zone_center("NONEXISTENT_ZONE_XYZ")
        assert center is None

    def test_center_inside_own_zone(self):
        """The center of a zone should be inside that zone."""
        center = get_zone_center("SCHOOL_JNTU")
        assert center is not None
        lat, lon = center
        result = check_zone(lat, lon)
        assert result is not None
        assert result.zone_id == "SCHOOL_JNTU"
