import pytest
from app.state_manager import StateManager

@pytest.fixture
def state_manager() -> StateManager:
    """Provides a clean StateManager instance for each test."""
    return StateManager()

def test_initial_state(state_manager: StateManager):
    """Tests that the initial state of the manager is empty."""
    assert state_manager.get_full_state() == {}

def test_set_and_get_state(state_manager: StateManager):
    """Tests setting and retrieving a piece of state."""
    state_manager.set_state("test_key", {"value": "test_data"})
    retrieved_state = state_manager.get_state("test_key")
    assert retrieved_state == {"value": "test_data"}
    assert state_manager.get_full_state() == {"test_key": {"value": "test_data"}}

def test_get_nonexistent_state(state_manager: StateManager):
    """Tests that getting a nonexistent key returns None."""
    assert state_manager.get_state("nonexistent_key") is None

def test_add_and_get_tool(state_manager: StateManager):
    """Tests the logic for adding and retrieving a tool."""
    def dummy_tool_func():
        return "dummy result"

    state_manager.add_tool("module.dummy_tool", dummy_tool_func)
    
    tools = state_manager.get_state("tools")
    assert "module.dummy_tool" in tools
    assert tools["module.dummy_tool"]() == "dummy result"

def test_state_isolation(state_manager: StateManager):
    """Ensures that tool state and general state are isolated."""
    def another_tool():
        pass
    
    state_manager.set_state("general_key", "general_value")
    state_manager.add_tool("another.tool", another_tool)
    
    full_state = state_manager.get_full_state()
    assert full_state.get("general_key") == "general_value"
    assert "tools" in full_state
    assert "another.tool" in full_state["tools"]