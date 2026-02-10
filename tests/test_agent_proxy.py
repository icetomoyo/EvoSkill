"""
Tests for AgentProxy - Multi-agent coordination
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from koda.agent.proxy import (
    AgentProxy,
    AgentProxyConfig,
    AgentPool,
    AgentStatus,
    TaskPriority,
    AgentInfo,
)
from koda.agent.loop import AgentLoop, AgentLoopConfig
from koda.ai.types import Context, AssistantMessage, UserMessage, TextContent, StopReason


@pytest.fixture
def mock_provider():
    """Create mock provider"""
    provider = Mock()
    provider.api_type = "test"
    provider.provider_id = "test"
    return provider


@pytest.fixture
def mock_model():
    """Create mock model"""
    model = Mock()
    model.id = "test-model"
    return model


@pytest.fixture
def mock_agent_loop(mock_provider, mock_model):
    """Create mock agent loop"""
    tools = []
    return AgentLoop(
        provider=mock_provider,
        model=mock_model,
        tools=tools,
        config=AgentLoopConfig(max_iterations=5)
    )


@pytest.fixture
def agent_proxy():
    """Create agent proxy"""
    return AgentProxy(config=AgentProxyConfig(max_agents=5))


class TestAgentProxy:
    """Test AgentProxy functionality"""
    
    def test_register_agent(self, agent_proxy, mock_agent_loop):
        """Test agent registration"""
        info = agent_proxy.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            agent_loop=mock_agent_loop,
            capabilities=["coding", "testing"],
            tools=["read", "write"]
        )
        
        assert info.id == "test-agent"
        assert info.name == "Test Agent"
        assert info.capabilities == ["coding", "testing"]
        assert info.tools == ["read", "write"]
        assert info.status == AgentStatus.IDLE
    
    def test_register_duplicate_agent(self, agent_proxy, mock_agent_loop):
        """Test registering duplicate agent raises error"""
        agent_proxy.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            agent_loop=mock_agent_loop
        )
        
        with pytest.raises(ValueError, match="already registered"):
            agent_proxy.register_agent(
                agent_id="test-agent",
                name="Test Agent 2",
                description="Another test agent",
                agent_loop=mock_agent_loop
            )
    
    def test_register_max_agents(self, agent_proxy, mock_agent_loop):
        """Test max agents limit"""
        for i in range(5):
            agent_proxy.register_agent(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                description=f"Agent {i}",
                agent_loop=mock_agent_loop
            )
        
        with pytest.raises(RuntimeError, match="Maximum number of agents"):
            agent_proxy.register_agent(
                agent_id="agent-5",
                name="Agent 5",
                description="Agent 5",
                agent_loop=mock_agent_loop
            )
    
    def test_unregister_agent(self, agent_proxy, mock_agent_loop):
        """Test agent unregistration"""
        agent_proxy.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            agent_loop=mock_agent_loop
        )
        
        result = agent_proxy.unregister_agent("test-agent")
        assert result is True
        assert "test-agent" not in agent_proxy._agents
    
    def test_unregister_nonexistent_agent(self, agent_proxy):
        """Test unregistering nonexistent agent"""
        result = agent_proxy.unregister_agent("nonexistent")
        assert result is False
    
    def test_get_agent(self, agent_proxy, mock_agent_loop):
        """Test getting agent info"""
        agent_proxy.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            agent_loop=mock_agent_loop
        )
        
        info = agent_proxy.get_agent("test-agent")
        assert info is not None
        assert info.name == "Test Agent"
        
        # Nonexistent agent
        assert agent_proxy.get_agent("nonexistent") is None
    
    def test_list_agents(self, agent_proxy, mock_agent_loop):
        """Test listing agents"""
        agent_proxy.register_agent(
            agent_id="agent-1",
            name="Agent 1",
            description="Coding agent",
            agent_loop=mock_agent_loop,
            capabilities=["coding"]
        )
        agent_proxy.register_agent(
            agent_id="agent-2",
            name="Agent 2",
            description="Testing agent",
            agent_loop=mock_agent_loop,
            capabilities=["testing"]
        )
        
        all_agents = agent_proxy.list_agents()
        assert len(all_agents) == 2
        
        # Filter by capability
        coding_agents = agent_proxy.list_agents(capability="coding")
        assert len(coding_agents) == 1
        assert coding_agents[0].id == "agent-1"
    
    def test_find_agents_for_task(self, agent_proxy, mock_agent_loop):
        """Test finding agents for task"""
        agent_proxy.register_agent(
            agent_id="coding-agent",
            name="Coding Agent",
            description="Coding specialist",
            agent_loop=mock_agent_loop,
            capabilities=["coding", "python"]
        )
        agent_proxy.register_agent(
            agent_id="testing-agent",
            name="Testing Agent",
            description="Testing specialist",
            agent_loop=mock_agent_loop,
            capabilities=["testing", "python"]
        )
        
        # Find agent with coding capability
        agents = agent_proxy.find_agents_for_task(["coding"])
        assert len(agents) == 1
        assert agents[0].id == "coding-agent"
        
        # Find agent with both capabilities
        agents = agent_proxy.find_agents_for_task(["coding", "python"])
        assert len(agents) == 1
        
        # No agent with this capability
        agents = agent_proxy.find_agents_for_task(["nonexistent"])
        assert len(agents) == 0
    
    @pytest.mark.asyncio
    async def test_delegate_success(self, agent_proxy, mock_agent_loop, mock_provider):
        """Test successful task delegation"""
        # Setup mock response
        mock_response = AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text="Task completed")],
            api="test",
            provider="test",
            model="test-model",
            stop_reason=StopReason.STOP
        )
        mock_provider.complete = AsyncMock(return_value=mock_response)
        
        agent_proxy.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            agent_loop=mock_agent_loop,
            capabilities=["coding"]
        )
        
        context = Context(
            system_prompt="You are a coding assistant",
            messages=[UserMessage(role="user", content="Write hello world")]
        )
        
        result = await agent_proxy.delegate(
            description="Write hello world",
            context=context,
            required_capabilities=["coding"]
        )
        
        assert isinstance(result, AssistantMessage)
        # Agent should have completed the task
        stats = agent_proxy.get_stats()
        assert stats["tasks_created"] == 1
    
    @pytest.mark.asyncio
    async def test_delegate_no_capable_agent(self, agent_proxy):
        """Test delegation with no capable agent"""
        context = Context(
            system_prompt="You are a coding assistant",
            messages=[UserMessage(role="user", content="Write hello world")]
        )
        
        with pytest.raises(RuntimeError, match="No agent found"):
            await agent_proxy.delegate(
                description="Write hello world",
                context=context,
                required_capabilities=["nonexistent"]
            )
    
    @pytest.mark.asyncio
    async def test_delegate_timeout(self, agent_proxy, mock_agent_loop, mock_provider):
        """Test delegation timeout"""
        # Setup mock to delay
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)
            return AssistantMessage(
                role="assistant",
                content=[TextContent(type="text", text="Done")],
                api="test",
                provider="test",
                model="test-model",
                stop_reason=StopReason.STOP
            )
        
        mock_provider.complete = slow_response
        
        agent_proxy.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            agent_loop=mock_agent_loop
        )
        
        context = Context(
            system_prompt="You are a coding assistant",
            messages=[UserMessage(role="user", content="Write hello world")]
        )
        
        with pytest.raises(TimeoutError):
            await agent_proxy.delegate(
                description="Write hello world",
                context=context,
                timeout=0.1  # Very short timeout
            )
    
    @pytest.mark.asyncio
    async def test_route_message(self, agent_proxy, mock_agent_loop, mock_provider):
        """Test message routing"""
        mock_response = AssistantMessage(
            role="assistant",
            content=[TextContent(type="text", text="Routed")],
            api="test",
            provider="test",
            model="test-model",
            stop_reason=StopReason.STOP
        )
        mock_provider.complete = AsyncMock(return_value=mock_response)
        
        agent_proxy.register_agent(
            agent_id="coding-agent",
            name="Coding Agent",
            description="Coding specialist",
            agent_loop=mock_agent_loop,
            capabilities=["coding"]
        )
        
        context = Context(
            system_prompt="You are a coding assistant",
            messages=[]
        )
        
        result = await agent_proxy.route_message(
            message="Help me code",
            context=context,
            routing_hint="coding"
        )
        
        assert isinstance(result, AssistantMessage)
    
    def test_get_stats(self, agent_proxy, mock_agent_loop):
        """Test getting stats"""
        stats = agent_proxy.get_stats()
        assert "tasks_created" in stats
        assert "tasks_completed" in stats
        assert "registered_agents" in stats
        
        # Register an agent
        agent_proxy.register_agent(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            agent_loop=mock_agent_loop
        )
        
        stats = agent_proxy.get_stats()
        assert stats["registered_agents"] == 1
    
    def test_event_handlers(self, agent_proxy):
        """Test event handler registration"""
        events = []
        
        @agent_proxy.on_event
        def handler(event):
            events.append(event)
        
        # Event handler should be registered
        assert len(agent_proxy._event_handlers) == 1


class TestAgentPool:
    """Test AgentPool functionality"""
    
    @pytest.mark.asyncio
    async def test_pool_initialization(self, agent_proxy, mock_provider, mock_model):
        """Test pool initialization"""
        def factory():
            return AgentLoop(
                provider=mock_provider,
                model=mock_model,
                tools=[],
                config=AgentLoopConfig()
            )
        
        pool = AgentPool(
            proxy=agent_proxy,
            agent_factory=factory,
            pool_size=3,
            name_prefix="worker"
        )
        
        await pool.initialize(
            capabilities=["processing"],
            tools=["read"],
            description="Worker pool"
        )
        
        assert len(pool.get_agent_ids()) == 3
        
        # Verify agents registered
        agents = agent_proxy.list_agents()
        assert len(agents) == 3
        
        # Check agent names
        agent_names = {a.name for a in agents}
        assert "Worker Agent 0" in agent_names
        assert "Worker Agent 1" in agent_names
        assert "Worker Agent 2" in agent_names


class TestAgentStatus:
    """Test AgentStatus enum"""
    
    def test_status_values(self):
        """Test status enum values"""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.BUSY.value == "busy"
        assert AgentStatus.OFFLINE.value == "offline"
        assert AgentStatus.ERROR.value == "error"


class TestTaskPriority:
    """Test TaskPriority enum"""
    
    def test_priority_values(self):
        """Test priority enum values"""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.NORMAL.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.CRITICAL.value == 4
    
    def test_priority_comparison(self):
        """Test priority comparison"""
        assert TaskPriority.CRITICAL.value > TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value > TaskPriority.NORMAL.value
        assert TaskPriority.NORMAL.value > TaskPriority.LOW.value


class TestAgentProxyConfig:
    """Test AgentProxyConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = AgentProxyConfig()
        assert config.max_agents == 10
        assert config.max_queue_size == 100
        assert config.default_timeout == 300.0
        assert config.enable_load_balancing is True
        assert config.task_retry_attempts == 2
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = AgentProxyConfig(
            max_agents=5,
            max_queue_size=50,
            enable_load_balancing=False
        )
        assert config.max_agents == 5
        assert config.max_queue_size == 50
        assert config.enable_load_balancing is False
