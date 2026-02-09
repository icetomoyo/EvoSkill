"""Tests for time_tool"""
import pytest
from ..main import get_current_time

async def test_get_current_time():
    result = await get_current_time(timezone="test")
    assert result["success"] is True

if __name__ == "__main__":
    asyncio.run(test_get_current_time())
    print("Tests passed!")
