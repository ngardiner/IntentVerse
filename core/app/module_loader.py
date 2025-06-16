import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, Type
import logging

from .state_manager import StateManager
from .modules.base_tool import BaseTool

# Set up logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class ModuleLoader:
    """
    Dynamically loads tool modules from the 'modules' directory,
    initializes them, and provides access to them.
    """

    def __init__(self, state_manager: StateManager, root_path: Path = None):
        self.state_manager = state_manager
        self.modules: Dict[str, BaseTool] = {}
        base_path = root_path if root_path else Path(__file__).parent
        self.modules_path = base_path / "modules"
        self.errors = [] # To store any errors encountered during loading

    def load_modules(self):
        """
        Scans the 'modules' directory, imports the 'tool.py' from each sub-directory,
        finds the class inheriting from BaseTool, and instantiates it.
        """
        log.info(f"Starting module scan in: {self.modules_path}")
        if not self.modules_path.is_dir():
            log.error(f"Modules directory not found at {self.modules_path}")
            self.errors.append(f"Modules directory not found at {self.modules_path}")
            return

        for module_dir in self.modules_path.iterdir():
            if module_dir.is_dir() and (module_dir / "__init__.py").exists():
                module_name = module_dir.name
                log.info(f"Found potential module package: '{module_name}'")
                try:
                    # Dynamically import the 'tool' submodule from the package
                    tool_module = importlib.import_module(
                        f".modules.{module_name}.tool", package="app"
                    )
                    log.info(f"Successfully imported module: {tool_module.__name__}")

                    # Find the class that inherits from BaseTool within the imported module
                    for name, obj in inspect.getmembers(tool_module):
                        if inspect.isclass(obj) and issubclass(obj, BaseTool) and obj is not BaseTool:
                            log.info(f"Found tool class '{name}' in '{module_name}'")
                            # Instantiate the tool with the state manager
                            self.modules[module_name] = obj(self.state_manager)
                            log.info(f"Successfully loaded and instantiated tool: '{module_name}'")
                            break
                except ImportError as e:
                    log.error(f"Could not import tool from module '{module_name}': {e}")
                    self.errors.append(f"ImportError in {module_name}: {e}")
                except Exception as e:
                    log.error(f"An unexpected error occurred loading module '{module_name}': {e}")
                    self.errors.append(f"Exception in {module_name}: {e}")

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Returns the instance of a loaded tool by its name."""
        return self.modules.get(tool_name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Returns a dictionary of all loaded tool instances."""
        return self.modules