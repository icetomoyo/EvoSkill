"""
Tests for git skill
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import git_status, git_diff, git_log, git_branch


@pytest.mark.asyncio
async def test_git_status_in_git_repo():
    """Test git_status in a git repository"""
    result = await git_status()
    
    assert isinstance(result, dict)
    assert "success" in result
    
    if result["success"]:
        assert "status" in result
        assert result["status"] in ["clean", "modified"]


@pytest.mark.asyncio
async def test_git_diff_no_changes():
    """Test git_diff when no changes"""
    # First ensure no changes
    result = await git_diff()
    
    assert isinstance(result, dict)
    assert "success" in result
    
    if result["success"] and not result.get("has_changes"):
        assert result.get("message") == "没有可显示的更改"


@pytest.mark.asyncio
async def test_git_log():
    """Test git_log"""
    result = await git_log(limit=3)
    
    assert isinstance(result, dict)
    assert "success" in result
    
    if result["success"]:
        assert "commits" in result
        assert isinstance(result["commits"], list)


@pytest.mark.asyncio
async def test_git_branch():
    """Test git_branch"""
    result = await git_branch()
    
    assert isinstance(result, dict)
    assert "success" in result
    
    if result["success"]:
        assert "branches" in result
        assert "current_branch" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
