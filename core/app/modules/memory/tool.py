from ..base_tool import BaseTool
from typing import Any, Dict, List, Optional

class MemoryTool(BaseTool):
    """
    Implements the logic for a simple key-value memory store.
    This class interacts with the global state managed by the StateManager.
    """

    def __init__(self, state_manager: Any):
        """
        Initializes the MemoryTool with a reference to the state manager.

        Args:
            state_manager: An instance of the StateManager class.
        """
        self.state_manager = state_manager
        # Ensure the memory state exists as a dictionary
        if 'memory' not in self.state_manager.get_full_state():
            self.state_manager.set('memory', {})

    def set_memory(self, key: str, value: str) -> str:
        """
        Stores or updates a value in the memory scratchpad.
        """
        memory_state = self.state_manager.get('memory')
        memory_state[key] = value
        self.state_manager.set('memory', memory_state)
        
        print(f"SETTING MEMORY for key '{key}'")
        return f"Successfully set memory for key: '{key}'"

    def get_memory(self, key: str) -> Optional[str]:
        """
        Retrieves a value from the memory scratchpad using its key.
        """
        memory_state = self.state_manager.get('memory')
        value = memory_state.get(key)
        
        if value is None:
            return f"Error: No memory found for key: '{key}'"
        return value

    def delete_memory(self, key: str) -> str:
        """
        Deletes a key-value pair from the memory scratchpad.
        """
        memory_state = self.state_manager.get('memory')
        if key in memory_state:
            del memory_state[key]
            self.state_manager.set('memory', memory_state)
            return f"Successfully deleted memory for key: '{key}'"
        return f"Error: No memory found for key: '{key}'"

    def list_memories(self) -> List[Dict[str, str]]:
        """
        Lists all key-value pairs currently stored in the memory scratchpad.
        """
        memory_state = self.state_manager.get('memory')
        return [{"key": k, "value": v} for k, v in memory_state.items()]
