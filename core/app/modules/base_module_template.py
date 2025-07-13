"""
Base module template for creating new IntentVerse modules.
This provides a standardized structure and common functionality for all module types.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseModuleTemplate(ABC):
    """
    Abstract base class for all IntentVerse modules.
    Provides common functionality and enforces standardized structure.
    """
    
    def __init__(self, module_id: str, category: str, display_name: str, description: str):
        """
        Initialize the base module.
        
        Args:
            module_id: Unique identifier for the module (e.g., "active_directory")
            category: Category this module belongs to (e.g., "identity")
            display_name: Human-readable name (e.g., "Active Directory")
            description: Brief description of module functionality
        """
        self.module_id = module_id
        self.category = category
        self.display_name = display_name
        self.description = description
        self.is_sandbox = True  # All new modules are sandbox by default
        self.default_enabled = False  # New modules disabled by default
        self.tools = {}
        self.mock_data = {}
        self.config = {}
        self.health_status = "unknown"
        self.last_health_check = None
        
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        Return the UI schema for this module.
        Must be implemented by each module.
        """
        pass
    
    @abstractmethod
    def initialize_mock_data(self) -> Dict[str, Any]:
        """
        Initialize mock data for sandbox mode.
        Must be implemented by each module.
        """
        pass
    
    @abstractmethod
    def get_tools(self) -> Dict[str, Any]:
        """
        Return the available tools for this module.
        Must be implemented by each module.
        """
        pass
    
    def get_base_schema_structure(self) -> Dict[str, Any]:
        """
        Return the base schema structure that all modules should follow.
        """
        return {
            "module_id": self.module_id,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "is_sandbox": self.is_sandbox,
            "default_enabled": self.default_enabled,
            "health_status": self.health_status,
            "last_updated": datetime.utcnow().isoformat(),
            "components": []
        }
    
    def validate_configuration(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate module configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Basic validation
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return False, errors
        
        # Check required fields
        required_fields = ["module_id", "category", "display_name"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Category validation
        valid_categories = [
            "productivity", "identity", "infrastructure", 
            "cloud", "security", "devops", "business"
        ]
        if config.get("category") not in valid_categories:
            errors.append(f"Invalid category. Must be one of: {', '.join(valid_categories)}")
        
        return len(errors) == 0, errors
    
    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the module.
        
        Returns:
            Health check results
        """
        try:
            # Basic health checks
            health_data = {
                "module_id": self.module_id,
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {
                    "schema_valid": self._check_schema_validity(),
                    "tools_available": self._check_tools_availability(),
                    "mock_data_loaded": self._check_mock_data(),
                    "configuration_valid": self._check_configuration()
                }
            }
            
            # Determine overall status
            failed_checks = [k for k, v in health_data["checks"].items() if not v]
            if failed_checks:
                health_data["status"] = "unhealthy"
                health_data["failed_checks"] = failed_checks
            
            self.health_status = health_data["status"]
            self.last_health_check = datetime.utcnow()
            
            return health_data
            
        except Exception as e:
            logger.error(f"Health check failed for module {self.module_id}: {e}")
            error_data = {
                "module_id": self.module_id,
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
            self.health_status = "error"
            self.last_health_check = datetime.utcnow()
            return error_data
    
    def _check_schema_validity(self) -> bool:
        """Check if the module schema is valid."""
        try:
            schema = self.get_schema()
            return isinstance(schema, dict) and "module_id" in schema
        except Exception:
            return False
    
    def _check_tools_availability(self) -> bool:
        """Check if module tools are available."""
        try:
            tools = self.get_tools()
            return isinstance(tools, dict)
        except Exception:
            return False
    
    def _check_mock_data(self) -> bool:
        """Check if mock data is properly loaded."""
        try:
            mock_data = self.initialize_mock_data()
            return isinstance(mock_data, dict)
        except Exception:
            return False
    
    def _check_configuration(self) -> bool:
        """Check if configuration is valid."""
        try:
            is_valid, _ = self.validate_configuration(self.config)
            return is_valid
        except Exception:
            return False
    
    def generate_mock_data_template(self, data_type: str, count: int = 10) -> List[Dict[str, Any]]:
        """
        Generate mock data template for common data types.
        
        Args:
            data_type: Type of data to generate (users, servers, etc.)
            count: Number of items to generate
            
        Returns:
            List of mock data items
        """
        from .mock_data_generator import MockDataGenerator
        generator = MockDataGenerator()
        
        if data_type == "users":
            return generator.generate_users(count)
        elif data_type == "servers":
            return generator.generate_servers(count)
        elif data_type == "applications":
            return generator.generate_applications(count)
        elif data_type == "network_devices":
            return generator.generate_network_devices(count)
        elif data_type == "cloud_resources":
            return generator.generate_cloud_resources(count)
        else:
            logger.warning(f"Unknown data type: {data_type}")
            return []
    
    def save_mock_data(self, file_path: Optional[str] = None) -> str:
        """
        Save mock data to a JSON file.
        
        Args:
            file_path: Optional custom file path
            
        Returns:
            Path where data was saved
        """
        if not file_path:
            file_path = f"mock_data_{self.module_id}.json"
        
        mock_data = self.initialize_mock_data()
        
        with open(file_path, 'w') as f:
            json.dump(mock_data, f, indent=2, default=str)
        
        logger.info(f"Mock data saved to {file_path}")
        return file_path
    
    def load_mock_data(self, file_path: str) -> Dict[str, Any]:
        """
        Load mock data from a JSON file.
        
        Args:
            file_path: Path to the JSON file
            
        Returns:
            Loaded mock data
        """
        try:
            with open(file_path, 'r') as f:
                mock_data = json.load(f)
            
            self.mock_data = mock_data
            logger.info(f"Mock data loaded from {file_path}")
            return mock_data
            
        except Exception as e:
            logger.error(f"Failed to load mock data from {file_path}: {e}")
            return {}
    
    def get_module_info(self) -> Dict[str, Any]:
        """
        Get comprehensive module information.
        
        Returns:
            Module information dictionary
        """
        return {
            "module_id": self.module_id,
            "display_name": self.display_name,
            "category": self.category,
            "description": self.description,
            "is_sandbox": self.is_sandbox,
            "default_enabled": self.default_enabled,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "tools_count": len(self.get_tools()),
            "mock_data_size": len(self.mock_data),
            "configuration": self.config
        }


class SandboxModule(BaseModuleTemplate):
    """
    Base class for sandbox/mock modules.
    Provides additional functionality for simulation and mock environments.
    """
    
    def __init__(self, module_id: str, category: str, display_name: str, description: str):
        super().__init__(module_id, category, display_name, description)
        self.simulation_state = {}
        self.mock_responses = {}
        self.scenario_data = {}
    
    def create_scenario(self, scenario_name: str, scenario_data: Dict[str, Any]) -> bool:
        """
        Create a predefined scenario for testing and learning.
        
        Args:
            scenario_name: Name of the scenario
            scenario_data: Scenario configuration and data
            
        Returns:
            Success status
        """
        try:
            self.scenario_data[scenario_name] = {
                "name": scenario_name,
                "data": scenario_data,
                "created_at": datetime.utcnow().isoformat(),
                "active": False
            }
            logger.info(f"Created scenario '{scenario_name}' for module {self.module_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to create scenario '{scenario_name}': {e}")
            return False
    
    def activate_scenario(self, scenario_name: str) -> bool:
        """
        Activate a specific scenario.
        
        Args:
            scenario_name: Name of the scenario to activate
            
        Returns:
            Success status
        """
        if scenario_name not in self.scenario_data:
            logger.error(f"Scenario '{scenario_name}' not found")
            return False
        
        try:
            # Deactivate all other scenarios
            for scenario in self.scenario_data.values():
                scenario["active"] = False
            
            # Activate the requested scenario
            self.scenario_data[scenario_name]["active"] = True
            self.mock_data = self.scenario_data[scenario_name]["data"]
            
            logger.info(f"Activated scenario '{scenario_name}' for module {self.module_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate scenario '{scenario_name}': {e}")
            return False
    
    def reset_simulation(self) -> bool:
        """
        Reset the simulation to initial state.
        
        Returns:
            Success status
        """
        try:
            self.simulation_state = {}
            self.mock_data = self.initialize_mock_data()
            
            # Deactivate all scenarios
            for scenario in self.scenario_data.values():
                scenario["active"] = False
            
            logger.info(f"Reset simulation for module {self.module_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset simulation: {e}")
            return False
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """
        Get current simulation status.
        
        Returns:
            Simulation status information
        """
        active_scenario = None
        for name, scenario in self.scenario_data.items():
            if scenario.get("active", False):
                active_scenario = name
                break
        
        return {
            "module_id": self.module_id,
            "simulation_active": bool(self.simulation_state),
            "active_scenario": active_scenario,
            "available_scenarios": list(self.scenario_data.keys()),
            "mock_data_loaded": bool(self.mock_data),
            "last_reset": self.simulation_state.get("last_reset"),
            "state_size": len(self.simulation_state)
        }