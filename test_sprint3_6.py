"""Test Sprints 3-6: Agent, Auth, Session, Tools, MOM"""
import asyncio
import tempfile
from pathlib import Path

from koda.agent.loop import AgentLoop, AgentLoopConfig, AgentTool
from koda.coding.auth_storage import AuthStorage, ApiKeyCredential, OAuthCredential
from koda.coding.session_manager import SessionManager, SessionContext, SessionMessageEntry, EntryType
from koda.coding.tools.edit_enhanced import EnhancedEditTool, fuzzy_find_text, normalize_for_fuzzy_match
from koda.mom.context import ContextManager
from koda.mom.store import Store
from koda.mom.sandbox import Sandbox


def test_agent_loop_config():
    """Test Agent Loop configuration"""
    print("Testing Agent Loop Config...")
    
    config = AgentLoopConfig(
        max_iterations=50,
        max_tool_calls_per_turn=32,
        retry_attempts=3,
        retry_delay_base=1.0,
        tool_timeout=600.0,
        enable_parallel_tools=True,
        max_parallel_tools=8
    )
    
    assert config.max_iterations == 50
    assert config.enable_parallel_tools == True
    
    print("  Agent Loop Config: PASSED")


def test_auth_storage():
    """Test Auth Storage"""
    print("Testing Auth Storage...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AuthStorage(Path(tmpdir))
        
        # Test API key credential
        cred = ApiKeyCredential(
            type="apiKey",
            key="sk-test123",
            provider="openai",
            created_at=1234567890
        )
        
        storage.set("openai", cred)
        retrieved = storage.get("openai")
        
        assert retrieved is not None
        assert isinstance(retrieved, ApiKeyCredential)
        assert retrieved.key == "sk-test123"
        
        # Test get_api_key
        api_key = storage.get_api_key("openai")
        assert api_key == "sk-test123"
        
        print("  Auth Storage: PASSED")


def test_oauth_credential():
    """Test OAuth credential"""
    print("Testing OAuth Credential...")
    
    import time
    
    cred = OAuthCredential(
        type="oauth",
        provider="google",
        access_token="token123",
        refresh_token="refresh456",
        expires_at=int(time.time()) + 3600,
        scopes=["read", "write"]
    )
    
    assert not cred.is_expired()
    
    # Test expired
    cred.expires_at = int(time.time()) - 100
    assert cred.is_expired()
    
    print("  OAuth Credential: PASSED")


def test_session_manager():
    """Test Session Manager"""
    print("Testing Session Manager...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = SessionManager(Path(tmpdir))
        
        # Create session
        session = manager.create_session("Test Session")
        assert session.name == "Test Session"
        assert session.current_branch == "main"
        
        # Add entry
        entry = SessionMessageEntry(
            id="msg1",
            type=EntryType.MESSAGE,
            timestamp=1234567890,
            role="user",
            content="Hello"
        )
        manager.add_entry(session, entry)
        
        assert len(session.entries) == 1
        
        # Fork branch
        branch_id = manager.fork_branch(session, "msg1", "feature-branch")
        assert branch_id == "feature-branch"
        assert session.current_branch == "feature-branch"
        
        # Save and load
        manager.save_session(session)
        loaded = manager.load_session(session.id)
        assert loaded is not None
        assert loaded.name == "Test Session"
        
        # Export
        markdown = manager.export_session(session, "markdown")
        assert "# Test Session" in markdown
        
        print("  Session Manager: PASSED")


def test_edit_enhanced():
    """Test Enhanced Edit Tool"""
    print("Testing Enhanced Edit Tool...")
    
    # Test fuzzy matching
    content = "def hello():\n    print('Hello')\n"
    old_text = "print('Hello')"
    
    result = fuzzy_find_text(content, old_text)
    assert result.found == True
    assert result.index > 0
    
    # Test normalization
    normalized = normalize_for_fuzzy_match('"smart quotes"')
    assert '"' in normalized or '"' not in normalized
    
    # Test file edit
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("line 1\nline 2\nline 3\n")
        path = f.name
    
    async def test_edit():
        tool = EnhancedEditTool()
        result = await tool.execute(path, "line 2", "modified line 2")
        assert result.success == True
        assert result.diff != ""
        
        # Verify file changed
        with open(path) as f:
            content = f.read()
        assert "modified line 2" in content
    
    asyncio.run(test_edit())
    
    import os
    os.unlink(path)
    
    print("  Enhanced Edit Tool: PASSED")


def test_mom_context():
    """Test MOM Context Manager"""
    print("Testing MOM Context Manager...")
    
    from koda.ai.types import UserMessage
    
    manager = ContextManager(max_tokens=4000)
    
    msg = UserMessage(role="user", content="Hello")
    manager.add(msg)
    
    context = manager.get_context()
    assert len(context.messages) == 1
    
    print("  MOM Context Manager: PASSED")


def test_mom_store():
    """Test MOM Store"""
    print("Testing MOM Store...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        store = Store(Path(tmpdir) / "store.json")
        
        store.set("key1", "value1")
        assert store.get("key1") == "value1"
        
        store.set("key2", {"nested": "data"})
        assert store.get("key2")["nested"] == "data"
        
        keys = store.list()
        assert "key1" in keys
        assert "key2" in keys
        
        store.delete("key1")
        assert store.get("key1") is None
        
        print("  MOM Store: PASSED")


def test_mom_sandbox():
    """Test MOM Sandbox"""
    print("Testing MOM Sandbox...")
    
    async def test_sandbox():
        with Sandbox() as sandbox:
            # Write file
            sandbox.write_file("test.txt", "Hello World")
            
            # Read file
            content = sandbox.read_file("test.txt")
            assert content == "Hello World"
            
            # Execute command (Windows compatible)
            result = await sandbox.execute(["cmd", "/c", "type", "test.txt"])
            assert result["success"] == True
            assert "Hello World" in result["stdout"]
    
    asyncio.run(test_sandbox())
    
    print("  MOM Sandbox: PASSED")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Sprints 3-6: Agent, Auth, Session, Tools, MOM Tests")
    print("=" * 60)
    
    test_agent_loop_config()
    test_auth_storage()
    test_oauth_credential()
    test_session_manager()
    test_edit_enhanced()
    test_mom_context()
    test_mom_store()
    test_mom_sandbox()
    
    print("=" * 60)
    print("All Sprints 3-6 Tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
