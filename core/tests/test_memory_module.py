import pytest
from app.state_manager import StateManager
from app.modules.memory.tool import MemoryTool

@pytest.fixture
def memory_tool() -> MemoryTool:
    """Provides a clean MemoryTool instance for each test, initialized with a fresh StateManager."""
    state_manager = StateManager()
    return MemoryTool(state_manager)

def test_initialization(memory_tool: MemoryTool):
    """Tests that the memory tool initializes the state correctly."""
    memories_state = memory_tool.state_manager.get('user_memories')
    assert memories_state is not None
    assert isinstance(memories_state, dict)
    assert len(memories_state) == 0

def test_set_and_get_memory(memory_tool: MemoryTool):
    """Tests setting and retrieving a memory."""
    memory_tool.set_memory(key="test_key", value="test_value")
    
    # Verify the state directly
    memories = memory_tool.state_manager.get('user_memories')
    assert memories.get("test_key") == "test_value"
    
    # Verify via the get_memory tool method
    result = memory_tool.get_memory(key="test_key")
    assert result["key"] == "test_key"
    assert result["value"] == "test_value"

def test_get_nonexistent_memory(memory_tool: MemoryTool):
    """Tests that getting a non-existent key returns a value of None."""
    result = memory_tool.get_memory(key="nonexistent_key")
    assert result["key"] == "nonexistent_key"
    assert result["value"] is None

def test_overwrite_memory(memory_tool: MemoryTool):
    """Tests that setting an existing key overwrites its value."""
    memory_tool.set_memory(key="overwrite_key", value="initial_value")
    memory_tool.set_memory(key="overwrite_key", value="new_value")
    
    result = memory_tool.get_memory(key="overwrite_key")
    assert result["value"] == "new_value"

def test_delete_memory(memory_tool: MemoryTool):
    """Tests deleting an existing memory."""
    memory_tool.set_memory(key="delete_key", value="to_be_deleted")
    
    delete_result = memory_tool.delete_memory(key="delete_key")
    assert delete_result["status"] == "success"
    
    get_result = memory_tool.get_memory(key="delete_key")
    assert get_result["value"] is None

def test_delete_nonexistent_memory(memory_tool: MemoryTool):
    """Tests that attempting to delete a non-existent key returns 'not_found'."""
    result = memory_tool.delete_memory(key="nonexistent_key")
    assert result["status"] == "not_found"

def test_list_memories(memory_tool: MemoryTool):
    """Tests listing all memory keys."""
    memory_tool.set_memory(key="key1", value="value1")
    memory_tool.set_memory(key="key2", value="value2")
    
    result = memory_tool.list_memories()
    assert isinstance(result, list)
    assert len(result) == 2
    assert "key1" in result
    assert "key2" in result

def test_list_memories_empty(memory_tool: MemoryTool):
    """Tests listing when no memories have been set."""
    result = memory_tool.list_memories()
    assert result == []