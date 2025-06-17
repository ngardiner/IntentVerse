"""
Unit tests for the ModuleLoader class.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os

from core.app.module_loader import ModuleLoader
from core.app.state_manager import StateManager
from core.app.modules.base_tool import BaseTool


class MockTool(BaseTool):
    """A mock tool for testing purposes."""
    
    def __init__(self, state_manager):
        super().__init__(state_manager)
        self.initialized = True


class TestModuleLoader:
    """Test the ModuleLoader class."""
    
    @pytest.fixture
    def state_manager(self):
        """Create a mock state manager."""
        return Mock(spec=StateManager)
    
    @pytest.fixture
    def temp_modules_dir(self):
        """Create a temporary modules directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            modules_path = Path(temp_dir) / "modules"
            modules_path.mkdir()
            yield modules_path
    
    def test_module_loader_initialization(self, state_manager):
        """Test ModuleLoader initialization."""
        loader = ModuleLoader(state_manager)
        
        assert loader.state_manager == state_manager
        assert loader.modules == {}
        assert loader.errors == []
        assert loader.modules_path.name == "modules"
    
    def test_module_loader_with_custom_root_path(self, state_manager, temp_modules_dir):
        """Test ModuleLoader initialization with custom root path."""
        root_path = temp_modules_dir.parent
        loader = ModuleLoader(state_manager, root_path=root_path)
        
        assert loader.modules_path == temp_modules_dir
    
    def test_load_modules_no_modules_directory(self, state_manager):
        """Test loading modules when modules directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_path = Path(temp_dir) / "nonexistent"
            loader = ModuleLoader(state_manager, root_path=non_existent_path)
            
            loader.load_modules()
            
            assert len(loader.modules) == 0
            assert len(loader.errors) == 1
            assert "Modules directory not found" in loader.errors[0]
    
    def test_load_modules_empty_directory(self, state_manager, temp_modules_dir):
        """Test loading modules from an empty directory."""
        loader = ModuleLoader(state_manager, root_path=temp_modules_dir.parent)
        
        loader.load_modules()
        
        assert len(loader.modules) == 0
        assert len(loader.errors) == 0
    
    def test_load_modules_directory_without_init(self, state_manager, temp_modules_dir):
        """Test that directories without __init__.py are skipped."""
        # Create a directory without __init__.py
        test_module_dir = temp_modules_dir / "test_module"
        test_module_dir.mkdir()
        
        loader = ModuleLoader(state_manager, root_path=temp_modules_dir.parent)
        loader.load_modules()
        
        assert len(loader.modules) == 0
        assert len(loader.errors) == 0
    
    @patch('core.app.module_loader.importlib.import_module')
    def test_load_modules_import_error(self, mock_import, state_manager, temp_modules_dir):
        """Test handling of import errors during module loading."""
        # Create a module directory with __init__.py
        test_module_dir = temp_modules_dir / "test_module"
        test_module_dir.mkdir()
        (test_module_dir / "__init__.py").touch()
        
        # Mock import_module to raise ImportError
        mock_import.side_effect = ImportError("Mock import error")
        
        loader = ModuleLoader(state_manager, root_path=temp_modules_dir.parent)
        loader.load_modules()
        
        assert len(loader.modules) == 0
        assert len(loader.errors) == 1
        assert "ImportError in test_module" in loader.errors[0]
    
    @patch('core.app.module_loader.importlib.import_module')
    def test_load_modules_no_tool_class(self, mock_import, state_manager, temp_modules_dir):
        """Test loading a module that doesn't contain a BaseTool subclass."""
        # Create a module directory with __init__.py
        test_module_dir = temp_modules_dir / "test_module"
        test_module_dir.mkdir()
        (test_module_dir / "__init__.py").touch()
        
        # Mock a module without BaseTool subclass
        mock_module = MagicMock()
        mock_module.__name__ = "app.modules.test_module.tool"
        # Add some non-BaseTool classes
        mock_module.SomeClass = type("SomeClass", (), {})
        mock_module.AnotherClass = type("AnotherClass", (), {})
        
        mock_import.return_value = mock_module
        
        # Mock inspect.getmembers to return our mock classes
        with patch('core.app.module_loader.inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [
                ("SomeClass", mock_module.SomeClass),
                ("AnotherClass", mock_module.AnotherClass)
            ]
            
            loader = ModuleLoader(state_manager, root_path=temp_modules_dir.parent)
            loader.load_modules()
        
        assert len(loader.modules) == 0
        assert len(loader.errors) == 0
    
    @patch('core.app.module_loader.importlib.import_module')
    def test_load_modules_successful_loading(self, mock_import, state_manager, temp_modules_dir):
        """Test successful loading of a module with a BaseTool subclass."""
        # Create a module directory with __init__.py
        test_module_dir = temp_modules_dir / "test_module"
        test_module_dir.mkdir()
        (test_module_dir / "__init__.py").touch()
        
        # Mock a module with BaseTool subclass
        mock_module = MagicMock()
        mock_module.__name__ = "app.modules.test_module.tool"
        mock_module.TestTool = MockTool
        
        mock_import.return_value = mock_module
        
        # Mock inspect.getmembers to return our mock tool class
        with patch('core.app.module_loader.inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [
                ("TestTool", MockTool),
                ("BaseTool", BaseTool)  # Should be ignored
            ]
            
            loader = ModuleLoader(state_manager, root_path=temp_modules_dir.parent)
            loader.load_modules()
        
        assert len(loader.modules) == 1
        assert "test_module" in loader.modules
        assert isinstance(loader.modules["test_module"], MockTool)
        assert loader.modules["test_module"].state_manager == state_manager
        assert len(loader.errors) == 0
    
    @patch('core.app.module_loader.importlib.import_module')
    def test_load_modules_instantiation_error(self, mock_import, state_manager, temp_modules_dir):
        """Test handling of errors during tool instantiation."""
        # Create a module directory with __init__.py
        test_module_dir = temp_modules_dir / "test_module"
        test_module_dir.mkdir()
        (test_module_dir / "__init__.py").touch()
        
        # Create a tool class that raises an error during instantiation
        class FailingTool(BaseTool):
            def __init__(self, state_manager):
                raise ValueError("Instantiation failed")
        
        # Mock a module with the failing tool class
        mock_module = MagicMock()
        mock_module.__name__ = "app.modules.test_module.tool"
        mock_module.FailingTool = FailingTool
        
        mock_import.return_value = mock_module
        
        # Mock inspect.getmembers to return our failing tool class
        with patch('core.app.module_loader.inspect.getmembers') as mock_getmembers:
            mock_getmembers.return_value = [
                ("FailingTool", FailingTool)
            ]
            
            loader = ModuleLoader(state_manager, root_path=temp_modules_dir.parent)
            loader.load_modules()
        
        assert len(loader.modules) == 0
        assert len(loader.errors) == 1
        assert "Exception in test_module" in loader.errors[0]
    
    def test_get_tool_existing(self, state_manager):
        """Test getting an existing tool."""
        loader = ModuleLoader(state_manager)
        mock_tool = Mock(spec=BaseTool)
        loader.modules["test_tool"] = mock_tool
        
        result = loader.get_tool("test_tool")
        assert result == mock_tool
    
    def test_get_tool_nonexistent(self, state_manager):
        """Test getting a non-existent tool."""
        loader = ModuleLoader(state_manager)
        
        result = loader.get_tool("nonexistent_tool")
        assert result is None
    
    def test_get_all_tools(self, state_manager):
        """Test getting all loaded tools."""
        loader = ModuleLoader(state_manager)
        mock_tool1 = Mock(spec=BaseTool)
        mock_tool2 = Mock(spec=BaseTool)
        loader.modules["tool1"] = mock_tool1
        loader.modules["tool2"] = mock_tool2
        
        result = loader.get_all_tools()
        assert result == {"tool1": mock_tool1, "tool2": mock_tool2}
    
    def test_get_all_tools_empty(self, state_manager):
        """Test getting all tools when none are loaded."""
        loader = ModuleLoader(state_manager)
        
        result = loader.get_all_tools()
        assert result == {}