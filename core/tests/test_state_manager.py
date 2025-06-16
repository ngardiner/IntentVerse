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
    state_manager.set("test_key", {"value": "test_data"})
    retrieved_state = state_manager.get_state("test_key")
    assert retrieved_state == {"value": "test_data"}
    assert state_manager.get_full_state() == {"test_key": {"value": "test_data"}}

def test_get_nonexistent_state(state_manager: StateManager):
    """Tests that getting a nonexistent key returns None."""
    assert state_manager.get("nonexistent_key") is None

def test_state_isolation(state_manager: StateManager):
    """Ensures that tool state and general state are isolated."""
    def another_tool():
        pass
    
    state_manager.set("general_key", "general_value")
    state_manager.add_tool("another.tool", another_tool)
    
    full_state = state_manager.get_full_state()
    assert full_state.get("general_key") == "general_value"
    assert "tools" in full_state
    assert "another.tool" in full_state["tools"]