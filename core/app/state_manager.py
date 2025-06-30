import threading
from typing import Any, Dict


class StateManager:
    """
    A thread-safe, in-memory state manager for the application.

    This class provides a simple key-value store for modules to maintain their
    state. It uses a lock to ensure that concurrent requests in the web server
    do not cause race conditions when modifying the state.
    """

    def __init__(self):
        """
        Initializes the StateManager with an empty state dictionary and a lock.
        """
        self._state: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Any) -> None:
        """
        Sets or updates the value for a given key in the state.

        Args:
            key: The key for the state entry (e.g., 'filesystem', 'email').
            value: The value to store.
        """
        with self._lock:
            self._state[key] = value

    def get(self, key: str) -> Any:
        """
        Gets the value for a given key from the state.

        Args:
            key: The key for the state entry.

        Returns:
            The value associated with the key, or None if the key doesn't exist.
        """
        with self._lock:
            return self._state.get(key)

    def get_full_state(self) -> Dict[str, Any]:
        """
        Returns a copy of the entire state dictionary.

        Returns:
            A shallow copy of the state dictionary to prevent direct modification.
        """
        with self._lock:
            return self._state.copy()


# A single, global instance of the StateManager that can be imported
# by other parts of the application to ensure shared state.
state_manager = StateManager()
