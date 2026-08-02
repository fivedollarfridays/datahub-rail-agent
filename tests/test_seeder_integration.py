"""Integration tests for full seeder run."""
import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from seed_demo_estate import seed_demo_estate


@pytest.fixture
def mock_aiohttp():
    """Mock aiohttp session."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"data": {}})

    class AsyncContextManager:
        async def __aenter__(self):
            return mock_response
        async def __aexit__(self, *args):
            pass

    mock_session.post = MagicMock(return_value=AsyncContextManager())
    return mock_session


@pytest.mark.asyncio
async def test_seed_demo_estate_end_to_end(mock_aiohttp, monkeypatch):
    """GREEN: Full seeder run creates healthy controls + 3 fault classes."""
    # Patch the seeder to use mocked session
    import datahub_rail.seeder
    import seed_demo_estate as seed_module

    async def mock_connect(self):
        self.session = mock_aiohttp

    async def mock_disconnect(self):
        pass

    monkeypatch.setattr(datahub_rail.seeder.DatasetSeeder, "connect", mock_connect)
    monkeypatch.setattr(datahub_rail.seeder.DatasetSeeder, "disconnect", mock_disconnect)

    result = await seed_demo_estate(gms_url="http://localhost:8080")

    assert result["status"] == "success"
    assert "healthy_controls" in result
    assert "fault_classes" in result

    # Verify 3 fault classes planted
    fault_classes = result["fault_classes"]
    assert len(fault_classes) == 3
    assert any(f["type"] == "stale" for f in fault_classes)
    assert any(f["type"] == "broken_lineage" for f in fault_classes)
    assert any(f["type"] == "schema_drift" for f in fault_classes)

    # Verify healthy controls exist
    controls = result["healthy_controls"]
    assert len(controls) > 0

    # Verify we made GraphQL calls
    assert mock_aiohttp.post.called
