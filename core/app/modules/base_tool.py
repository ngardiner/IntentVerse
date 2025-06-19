from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseTool(ABC):
    """
    An abstract base class for all tool modules in IntentVerse.

    This class defines the basic structure that every tool module must implement.
    It ensures that each tool is properly initialized with a reference to the
    shared StateManager instance.
    """

    @abstractmethod
    def __init__(self, state_manager: Any):
        """
        Initializes the tool with a reference to the state manager.

        This method must be implemented by all subclasses.

        Args:
            state_manager: An instance of the StateManager class.
        """
        self.state_manager = state_manager
        pass
        
    def get_ui_schema(self) -> Dict[str, Any]:
        """
        Returns the UI schema for this tool module.
        
        This method can be overridden by subclasses to provide custom UI schemas.
        By default, returns a basic schema with the module name.
        
        Returns:
            A dictionary containing the UI schema.
        """
        module_name = self.__class__.__module__.split('.')[-2]
        return {
            "name": module_name,
            "displayName": module_name.replace('_', ' ').title(),
            "description": self.__class__.__doc__ or f"Tool module for {module_name}",
            "version": "1.0.0",
            "components": []
        }