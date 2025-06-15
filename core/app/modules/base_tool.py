from abc import ABC, abstractmethod
from typing import Any

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