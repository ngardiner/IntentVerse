import importlib
from pathlib import Path
from typing import Any, Dict, Type

from .state_manager import StateManager

class ModuleLoader:
    """
    Dynamically discovers and loads modules from the 'modules' directory.

    For each module found, it imports its 'tool.py' and 'schema.py',
    instantiates the tool class with the shared state_manager, and stores
    both the tool instance and the UI schema for later use.
    """

    def __init__(self, state_manager: StateManager):
        """
        Initializes the ModuleLoader.

        Args:
            state_manager: The shared instance of the StateManager.
        """
        self.state_manager = state_manager
        self.tools: Dict[str, Any] = {}
        self.schemas: Dict[str, Any] = {}

    def load_modules(self):
        """
        Scans the 'modules' directory and loads each module.
        """
        modules_path = Path(__file__).parent / "modules"
        print(f"Scanning for modules in: {modules_path}")

        for module_dir in modules_path.iterdir():
            if module_dir.is_dir() and (module_dir / "__init__.py").exists():
                module_name = module_dir.name
                print(f"Found module: {module_name}")
                try:
                    self._load_single_module(module_name)
                except Exception as e:
                    print(f"Error loading module '{module_name}': {e}")

    def _load_single_module(self, module_name: str):
        """
        Loads the tool and schema for a single module.
        """
        # Dynamically import the tool and schema modules
        tool_module = importlib.import_module(f".modules.{module_name}.tool", package="app")
        schema_module = importlib.import_module(f".modules.{module_name}.schema", package="app")

        # Find the tool class within the tool module (assuming one class per file)
        tool_class = self._find_class_in_module(tool_module)
        if not tool_class:
            raise ImportError(f"No tool class found in module '{module_name}'")

        # Instantiate the tool class, passing the state manager
        tool_instance = tool_class(self.state_manager)
        self.tools[module_name] = tool_instance
        print(f"  - Loaded tool: {tool_class.__name__}")

        # Load the UI schema
        ui_schema = getattr(schema_module, "UI_SCHEMA", {})
        self.schemas[module_name] = ui_schema
        print(f"  - Loaded UI schema")


    def _find_class_in_module(self, module: Any) -> Type[Any] | None:
        """
        A helper to find the first class defined in a given module.
        """
        for name, obj in module.__dict__.items():
            if isinstance(obj, type) and obj.__module__ == module.__name__:
                return obj
        return None

    def get_tools(self) -> Dict[str, Any]:
        """Returns the dictionary of loaded tool instances."""
        return self.tools

    def get_schemas(self) -> Dict[str, Any]:
        """Returns the dictionary of loaded UI schemas."""
        return self.schemas
