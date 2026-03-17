"""
SVIES — Shared Test Fixtures
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════════════════
# Mock data classes (same shapes as the real modules produce)
# ══════════════════════════════════════════════════════════

@dataclass
class MockDBResult:
    """Mimics modules.db_intelligence.VehicleIntelligence."""
    violations_found: list[str] = field(default_factory=list)


@dataclass
class MockFakePlateResult:
    """Mimics modules.fake_plate.FakePlateResult."""
    is_fake: bool = False
    flags: list[str] = field(default_factory=list)


# ══════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════

@pytest.fixture
def clean_db_result():
    """A vehicle with NO violations from DB intelligence."""
    return MockDBResult(violations_found=[])


@pytest.fixture
def expired_docs_db_result():
    """A vehicle with expired PUCC and insurance."""
    return MockDBResult(violations_found=["EXPIRED_PUCC", "EXPIRED_INSURANCE"])


@pytest.fixture
def stolen_db_result():
    """A stolen vehicle."""
    return MockDBResult(violations_found=["STOLEN_VEHICLE"])


@pytest.fixture
def unregistered_db_result():
    """An unregistered vehicle with no docs."""
    return MockDBResult(violations_found=["UNREGISTERED_VEHICLE", "NO_PUCC", "NO_INSURANCE"])


@pytest.fixture
def clean_plate():
    """A legitimate plate result."""
    return MockFakePlateResult(is_fake=False, flags=[])


@pytest.fixture
def fake_plate():
    """A fake plate result with flags."""
    return MockFakePlateResult(is_fake=True, flags=["TYPE_MISMATCH", "FORMAT_INVALID"])
