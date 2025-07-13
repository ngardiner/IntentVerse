import importlib
import inspect
from pathlib import Path
from typing import Dict, Any, Type, List
import logging
from sqlmodel import Session, select

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
        self.disabled_modules: Dict[str, BaseTool] = {}  # Store disabled modules
        base_path = root_path if root_path else Path(__file__).parent
        self.modules_path = base_path / "modules"
        self.errors = []  # To store any errors encountered during loading

    def load_modules(self, session: Session = None):
        """
        Scans the 'modules' directory, imports the 'tool.py' from each sub-directory,
        finds the class inheriting from BaseTool, and instantiates it.
        Only loads modules that are enabled in the configuration.
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

                # Check if module is enabled (if session is available)
                if session and not self._is_module_enabled(module_name, session):
                    log.info(f"Module '{module_name}' is disabled, skipping load")
                    continue

                try:
                    # Dynamically import the 'tool' submodule from the package
                    tool_module = importlib.import_module(
                        f".modules.{module_name}.tool", package="app"
                    )
                    log.info(f"Successfully imported module: {tool_module.__name__}")

                    # Find the class that inherits from BaseTool within the imported module
                    for name, obj in inspect.getmembers(tool_module):
                        if (
                            inspect.isclass(obj)
                            and issubclass(obj, BaseTool)
                            and obj is not BaseTool
                        ):
                            log.info(f"Found tool class '{name}' in '{module_name}'")
                            # Instantiate the tool with the state manager
                            self.modules[module_name] = obj(self.state_manager)
                            log.info(
                                f"Successfully loaded and instantiated tool: '{module_name}'"
                            )
                            break
                except ImportError as e:
                    log.error(f"Could not import tool from module '{module_name}': {e}")
                    self.errors.append(f"ImportError in {module_name}: {e}")
                except Exception as e:
                    log.error(
                        f"An unexpected error occurred loading module '{module_name}': {e}"
                    )
                    self.errors.append(f"Exception in {module_name}: {e}")

    def get_tool(self, tool_name: str) -> BaseTool | None:
        """Returns the instance of a loaded tool by its name."""
        return self.modules.get(tool_name)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Returns a dictionary of all loaded tool instances."""
        return self.modules

    def get_schemas(self) -> Dict[str, Any]:
        """Returns a dictionary of UI schemas for all loaded modules."""
        schemas = {}
        for module_name, tool_instance in self.modules.items():
            if hasattr(tool_instance, "get_ui_schema"):
                schemas[module_name] = tool_instance.get_ui_schema()
        return schemas

    def _is_module_enabled(self, module_name: str, session: Session) -> bool:
        """Check if a module is enabled in the database configuration."""
        from .models import ModuleConfiguration

        # Query for module-level configuration (tool_name is None)
        stmt = select(ModuleConfiguration).where(
            ModuleConfiguration.module_name == module_name,
            ModuleConfiguration.tool_name.is_(None),
        )
        config = session.exec(stmt).first()

        # If no configuration exists, default to enabled
        return config.is_enabled if config else True

    def get_module_status(self, session: Session) -> Dict[str, Dict[str, Any]]:
        """Get the status of all available modules (enabled and disabled)."""
        from .models import ModuleConfiguration

        all_modules = {}

        # Get all available modules from the filesystem
        if self.modules_path.is_dir():
            for module_dir in self.modules_path.iterdir():
                if module_dir.is_dir() and (module_dir / "__init__.py").exists():
                    module_name = module_dir.name
                    is_enabled = self._is_module_enabled(module_name, session)
                    is_loaded = module_name in self.modules
                    category = self._get_module_category(module_name, session)

                    # Get available tools for this module
                    tools = self._get_module_tools(module_name, session)

                    all_modules[module_name] = {
                        "name": module_name,
                        "display_name": module_name.replace("_", " ").title(),
                        "category": category,
                        "is_enabled": is_enabled,
                        "is_loaded": is_loaded,
                        "description": self._get_module_description(module_name),
                        "tools": tools,
                    }

        return all_modules

    def _get_module_description(self, module_name: str) -> str:
        """Get the description of a module from its tool class."""
        try:
            if module_name in self.modules:
                return (
                    self.modules[module_name].__class__.__doc__
                    or f"Tool module for {module_name}"
                )
            elif module_name in self.disabled_modules:
                return (
                    self.disabled_modules[module_name].__class__.__doc__
                    or f"Tool module for {module_name}"
                )
            else:
                # Try to import and get description without instantiating
                tool_module = importlib.import_module(
                    f".modules.{module_name}.tool", package="app"
                )
                for name, obj in inspect.getmembers(tool_module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseTool)
                        and obj is not BaseTool
                    ):
                        return obj.__doc__ or f"Tool module for {module_name}"
        except Exception:
            pass
        return f"Tool module for {module_name}"

    def set_module_enabled(
        self, module_name: str, enabled: bool, session: Session
    ) -> bool:
        """Enable or disable a module."""
        from .models import ModuleConfiguration
        from datetime import datetime

        # Get or create module configuration
        stmt = select(ModuleConfiguration).where(
            ModuleConfiguration.module_name == module_name,
            ModuleConfiguration.tool_name.is_(None),
        )
        config = session.exec(stmt).first()

        if not config:
            config = ModuleConfiguration(
                module_name=module_name,
                tool_name=None,
                is_enabled=enabled,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(config)
        else:
            config.is_enabled = enabled
            config.updated_at = datetime.utcnow()

        session.commit()

        # Handle module loading/unloading
        if enabled and module_name not in self.modules:
            self._load_single_module(module_name)
        elif not enabled and module_name in self.modules:
            self._unload_single_module(module_name)

        return True

    def _load_single_module(self, module_name: str) -> bool:
        """Load a single module."""
        try:
            # Check if it's in disabled modules first
            if module_name in self.disabled_modules:
                self.modules[module_name] = self.disabled_modules[module_name]
                del self.disabled_modules[module_name]
                log.info(f"Re-enabled module: '{module_name}'")
                return True

            # Try to import and instantiate the module
            tool_module = importlib.import_module(
                f".modules.{module_name}.tool", package="app"
            )

            for name, obj in inspect.getmembers(tool_module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseTool)
                    and obj is not BaseTool
                ):
                    self.modules[module_name] = obj(self.state_manager)
                    log.info(f"Successfully loaded module: '{module_name}'")
                    return True

        except Exception as e:
            log.error(f"Failed to load module '{module_name}': {e}")
            self.errors.append(f"Failed to load {module_name}: {e}")
            return False

        return False

    def _unload_single_module(self, module_name: str) -> bool:
        """Unload a single module."""
        if module_name in self.modules:
            # Move to disabled modules to preserve instance
            self.disabled_modules[module_name] = self.modules[module_name]
            del self.modules[module_name]
            log.info(f"Disabled module: '{module_name}'")
            return True
        return False

    def _get_module_tools(self, module_name: str, session: Session) -> Dict[str, Dict[str, Any]]:
        """Get all available tools for a module with their enabled status."""
        from .models import ModuleConfiguration
        import inspect

        tools = {}
        
        try:
            # Try to get the tool class methods
            if module_name in self.modules:
                tool_instance = self.modules[module_name]
            elif module_name in self.disabled_modules:
                tool_instance = self.disabled_modules[module_name]
            else:
                # Try to import and inspect without instantiating
                tool_module = importlib.import_module(
                    f".modules.{module_name}.tool", package="app"
                )
                tool_class = None
                for name, obj in inspect.getmembers(tool_module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, BaseTool)
                        and obj is not BaseTool
                    ):
                        tool_class = obj
                        break
                
                if not tool_class:
                    return tools
                
                # Get methods from the class
                for method_name, method in inspect.getmembers(tool_class, inspect.isfunction):
                    if not method_name.startswith("_") and method_name not in ["get_ui_schema", "__init__"]:
                        is_enabled = self._is_tool_enabled(module_name, method_name, session)
                        tools[method_name] = {
                            "name": method_name,
                            "display_name": method_name.replace("_", " ").title(),
                            "is_enabled": is_enabled,
                            "description": inspect.getdoc(method) or f"{method_name} tool",
                        }
                return tools
            
            # Get public methods from the tool instance
            for method_name, method in inspect.getmembers(tool_instance, inspect.ismethod):
                if not method_name.startswith("_") and method_name not in ["get_ui_schema"]:
                    is_enabled = self._is_tool_enabled(module_name, method_name, session)
                    tools[method_name] = {
                        "name": method_name,
                        "display_name": method_name.replace("_", " ").title(),
                        "is_enabled": is_enabled,
                        "description": inspect.getdoc(method) or f"{method_name} tool",
                    }
                    
        except Exception as e:
            log.error(f"Error getting tools for module '{module_name}': {e}")
            
        return tools

    def _is_tool_enabled(self, module_name: str, tool_name: str, session: Session) -> bool:
        """Check if a specific tool is enabled in the database configuration."""
        from .models import ModuleConfiguration

        # Query for tool-level configuration
        stmt = select(ModuleConfiguration).where(
            ModuleConfiguration.module_name == module_name,
            ModuleConfiguration.tool_name == tool_name,
        )
        config = session.exec(stmt).first()

        # If no tool-specific configuration exists, check if the module is enabled
        if not config:
            return self._is_module_enabled(module_name, session)
        
        return config.is_enabled

    def set_tool_enabled(
        self, module_name: str, tool_name: str, enabled: bool, session: Session
    ) -> bool:
        """Enable or disable a specific tool within a module."""
        from .models import ModuleConfiguration
        from datetime import datetime

        # Validate that the module and tool exist
        modules_status = self.get_module_status(session)
        if module_name not in modules_status:
            return False
        
        if tool_name not in modules_status[module_name].get("tools", {}):
            return False

        # Get or create tool configuration
        stmt = select(ModuleConfiguration).where(
            ModuleConfiguration.module_name == module_name,
            ModuleConfiguration.tool_name == tool_name,
        )
        config = session.exec(stmt).first()

        if not config:
            config = ModuleConfiguration(
                module_name=module_name,
                tool_name=tool_name,
                is_enabled=enabled,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(config)
        else:
            config.is_enabled = enabled
            config.updated_at = datetime.utcnow()

        session.commit()
        return True

    def _get_module_category(self, module_name: str, session: Session) -> str:
        """Get the category for a module."""
        from .models import ModuleConfiguration

        # Query for module-level configuration (tool_name is None)
        stmt = select(ModuleConfiguration).where(
            ModuleConfiguration.module_name == module_name,
            ModuleConfiguration.tool_name.is_(None),
        )
        config = session.exec(stmt).first()

        # If no configuration exists, default to productivity
        return config.category if config else "productivity"

    def get_categories(self, session: Session) -> Dict[str, Dict[str, Any]]:
        """Get all available categories with their status."""
        from .models import ModuleCategory

        categories = {}
        
        # Get all categories from database
        stmt = select(ModuleCategory).order_by(ModuleCategory.sort_order)
        db_categories = session.exec(stmt).all()
        
        for category in db_categories:
            categories[category.name] = {
                "name": category.name,
                "display_name": category.display_name,
                "description": category.description,
                "is_enabled": category.is_enabled,
                "sort_order": category.sort_order,
                "module_count": self._count_modules_in_category(category.name, session)
            }
        
        return categories

    def _count_modules_in_category(self, category_name: str, session: Session) -> int:
        """Count the number of modules in a specific category."""
        from .models import ModuleConfiguration

        stmt = select(ModuleConfiguration).where(
            ModuleConfiguration.category == category_name,
            ModuleConfiguration.tool_name.is_(None)
        )
        return len(session.exec(stmt).all())

    def set_category_enabled(self, category_name: str, enabled: bool, session: Session) -> bool:
        """Enable or disable an entire category."""
        from .models import ModuleCategory
        from datetime import datetime

        # Update category status
        stmt = select(ModuleCategory).where(ModuleCategory.name == category_name)
        category = session.exec(stmt).first()
        
        if not category:
            return False
            
        category.is_enabled = enabled
        category.updated_at = datetime.utcnow()
        session.commit()
        
        return True

    def get_modules_by_category(self, session: Session) -> Dict[str, List[Dict[str, Any]]]:
        """Get modules organized by category."""
        all_modules = self.get_module_status(session)
        categories = self.get_categories(session)
        
        modules_by_category = {}
        
        # Initialize with empty lists for all categories
        for category_name in categories.keys():
            modules_by_category[category_name] = []
        
        # Add modules to their respective categories
        for module_name, module_info in all_modules.items():
            category = module_info.get("category", "productivity")
            if category not in modules_by_category:
                modules_by_category[category] = []
            modules_by_category[category].append(module_info)
        
        return modules_by_category
