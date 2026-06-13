# Canva Designer — Tests

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Note: These are skeleton tests. Full integration tests require
# a running Chrome instance with CDP and an active Canva session.


@pytest.mark.asyncio
async def test_config_defaults():
    """Test configuration defaults."""
    from canva_designer.designer import Config
    assert Config.CDP_URL == "http://localhost:9222"
    assert Config.BRAND_FONT == "Lato"
    assert Config.BRAND_SIZE == 36
    assert Config.BOLD is True


@pytest.mark.asyncio
async def test_designer_init():
    """Test CanvaDesigner initialization."""
    from canva_designer.designer import CanvaDesigner
    d = CanvaDesigner()
    assert d.cdp_url == "http://localhost:9222"
    assert d.page is None
    assert d.browser is None


@pytest.mark.asyncio
async def test_designer_custom_url():
    """Test CanvaDesigner with custom CDP URL."""
    from canva_designer.designer import CanvaDesigner
    d = CanvaDesigner(cdp_url="http://localhost:9223")
    assert d.cdp_url == "http://localhost:9223"


# Integration tests (require Chrome + Canva session)

@pytest.mark.asyncio
@pytest.mark.integration
async def test_connect():
    """Test CDP connection (requires Chrome running)."""
    from canva_designer.designer import CanvaDesigner
    d = CanvaDesigner()
    connected = await d.connect()
    if connected:
        assert d.page is not None
        await d.disconnect()
    else:
        pytest.skip("Chrome not available")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_state():
    """Test state reading (requires Chrome + Canva)."""
    from canva_designer.designer import CanvaDesigner
    d = CanvaDesigner()
    if await d.connect():
        state = await d.get_state()
        assert isinstance(state, dict)
        await d.disconnect()
    else:
        pytest.skip("Chrome not available")
