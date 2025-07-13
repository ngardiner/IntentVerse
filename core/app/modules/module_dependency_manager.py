"""
Module dependency management system for IntentVerse modules.
Handles module dependencies, loading order, and conflict resolution.
"""

from typing import Dict, Any, List, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of module dependencies."""
    REQUIRED = "required"  # Module cannot function without this dependency
    OPTIONAL = "optional"  # Module has enhanced functionality with this dependency
    CONFLICTS = "conflicts"  # Module cannot coexist with this dependency


@dataclass
class ModuleDependency:
    """Represents a dependency between modules."""
    source_module: str
    target_module: str
    dependency_type: DependencyType
    version_constraint: Optional[str] = None
    description: Optional[str] = None


class ModuleDependencyManager:
    """
    Manages module dependencies and loading order.
    """
    
    def __init__(self):
        self.dependencies: Dict[str, List[ModuleDependency]] = {}
        self.module_metadata: Dict[str, Dict[str, Any]] = {}
        self.loading_order: List[str] = []
        self.conflict_resolution_strategy = "disable_conflicting"
    
    def register_module_metadata(self, module_id: str, metadata: Dict[str, Any]) -> None:
        """
        Register metadata for a module.
        
        Args:
            module_id: Module identifier
            metadata: Module metadata including dependencies
        """
        self.module_metadata[module_id] = metadata
        
        # Extract dependencies from metadata
        if "dependencies" in metadata:
            self._parse_dependencies(module_id, metadata["dependencies"])
    
    def _parse_dependencies(self, module_id: str, dependencies: Dict[str, Any]) -> None:
        """Parse dependencies from module metadata."""
        module_deps = []
        
        # Required dependencies
        for dep in dependencies.get("required", []):
            if isinstance(dep, str):
                module_deps.append(ModuleDependency(
                    source_module=module_id,
                    target_module=dep,
                    dependency_type=DependencyType.REQUIRED
                ))
            elif isinstance(dep, dict):
                module_deps.append(ModuleDependency(
                    source_module=module_id,
                    target_module=dep["module"],
                    dependency_type=DependencyType.REQUIRED,
                    version_constraint=dep.get("version"),
                    description=dep.get("description")
                ))
        
        # Optional dependencies
        for dep in dependencies.get("optional", []):
            if isinstance(dep, str):
                module_deps.append(ModuleDependency(
                    source_module=module_id,
                    target_module=dep,
                    dependency_type=DependencyType.OPTIONAL
                ))
            elif isinstance(dep, dict):
                module_deps.append(ModuleDependency(
                    source_module=module_id,
                    target_module=dep["module"],
                    dependency_type=DependencyType.OPTIONAL,
                    version_constraint=dep.get("version"),
                    description=dep.get("description")
                ))
        
        # Conflicts
        for dep in dependencies.get("conflicts", []):
            if isinstance(dep, str):
                module_deps.append(ModuleDependency(
                    source_module=module_id,
                    target_module=dep,
                    dependency_type=DependencyType.CONFLICTS
                ))
            elif isinstance(dep, dict):
                module_deps.append(ModuleDependency(
                    source_module=module_id,
                    target_module=dep["module"],
                    dependency_type=DependencyType.CONFLICTS,
                    description=dep.get("description")
                ))
        
        self.dependencies[module_id] = module_deps
    
    def add_dependency(self, dependency: ModuleDependency) -> bool:
        """
        Add a dependency relationship.
        
        Args:
            dependency: Dependency to add
            
        Returns:
            Success status
        """
        try:
            if dependency.source_module not in self.dependencies:
                self.dependencies[dependency.source_module] = []
            
            # Check for duplicate dependencies
            existing = [d for d in self.dependencies[dependency.source_module] 
                       if d.target_module == dependency.target_module and 
                          d.dependency_type == dependency.dependency_type]
            
            if existing:
                logger.warning(f"Dependency already exists: {dependency.source_module} -> {dependency.target_module}")
                return False
            
            self.dependencies[dependency.source_module].append(dependency)
            logger.info(f"Added dependency: {dependency.source_module} -> {dependency.target_module} ({dependency.dependency_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add dependency: {e}")
            return False
    
    def remove_dependency(self, source_module: str, target_module: str, dependency_type: DependencyType) -> bool:
        """
        Remove a dependency relationship.
        
        Args:
            source_module: Source module ID
            target_module: Target module ID
            dependency_type: Type of dependency to remove
            
        Returns:
            Success status
        """
        try:
            if source_module not in self.dependencies:
                return False
            
            original_count = len(self.dependencies[source_module])
            self.dependencies[source_module] = [
                d for d in self.dependencies[source_module]
                if not (d.target_module == target_module and d.dependency_type == dependency_type)
            ]
            
            removed = original_count - len(self.dependencies[source_module])
            if removed > 0:
                logger.info(f"Removed dependency: {source_module} -> {target_module} ({dependency_type.value})")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove dependency: {e}")
            return False
    
    def calculate_loading_order(self, enabled_modules: List[str]) -> Tuple[List[str], List[str]]:
        """
        Calculate the optimal loading order for modules based on dependencies.
        
        Args:
            enabled_modules: List of modules that should be loaded
            
        Returns:
            Tuple of (loading_order, failed_modules)
        """
        try:
            # Filter to only enabled modules
            available_modules = set(enabled_modules)
            loading_order = []
            failed_modules = []
            remaining_modules = available_modules.copy()
            
            # Resolve conflicts first
            conflicting_modules = self._resolve_conflicts(available_modules)
            for module in conflicting_modules:
                remaining_modules.discard(module)
                failed_modules.append(module)
            
            # Topological sort with dependency resolution
            max_iterations = len(remaining_modules) * 2  # Prevent infinite loops
            iteration = 0
            
            while remaining_modules and iteration < max_iterations:
                iteration += 1
                modules_loaded_this_iteration = []
                
                for module in list(remaining_modules):
                    if self._can_load_module(module, loading_order, available_modules):
                        loading_order.append(module)
                        modules_loaded_this_iteration.append(module)
                
                # Remove loaded modules from remaining
                for module in modules_loaded_this_iteration:
                    remaining_modules.remove(module)
                
                # If no modules were loaded this iteration, we have circular dependencies
                if not modules_loaded_this_iteration and remaining_modules:
                    logger.warning(f"Circular dependencies detected for modules: {remaining_modules}")
                    # Add remaining modules to failed list
                    failed_modules.extend(list(remaining_modules))
                    break
            
            self.loading_order = loading_order
            logger.info(f"Calculated loading order: {loading_order}")
            if failed_modules:
                logger.warning(f"Failed to load modules due to dependencies: {failed_modules}")
            
            return loading_order, failed_modules
            
        except Exception as e:
            logger.error(f"Failed to calculate loading order: {e}")
            return [], enabled_modules
    
    def _resolve_conflicts(self, available_modules: Set[str]) -> List[str]:
        """
        Resolve module conflicts based on the configured strategy.
        
        Args:
            available_modules: Set of available modules
            
        Returns:
            List of modules to disable due to conflicts
        """
        conflicting_modules = []
        
        for module in available_modules:
            if module in self.dependencies:
                for dep in self.dependencies[module]:
                    if (dep.dependency_type == DependencyType.CONFLICTS and 
                        dep.target_module in available_modules):
                        
                        if self.conflict_resolution_strategy == "disable_conflicting":
                            # Disable the conflicting target module
                            conflicting_modules.append(dep.target_module)
                            logger.warning(f"Disabling {dep.target_module} due to conflict with {module}")
                        elif self.conflict_resolution_strategy == "disable_source":
                            # Disable the source module
                            conflicting_modules.append(module)
                            logger.warning(f"Disabling {module} due to conflict with {dep.target_module}")
        
        return list(set(conflicting_modules))  # Remove duplicates
    
    def _can_load_module(self, module: str, already_loaded: List[str], available_modules: Set[str]) -> bool:
        """
        Check if a module can be loaded given current state.
        
        Args:
            module: Module to check
            already_loaded: Modules already loaded
            available_modules: All available modules
            
        Returns:
            Whether the module can be loaded
        """
        if module not in self.dependencies:
            return True  # No dependencies, can load
        
        for dep in self.dependencies[module]:
            if dep.dependency_type == DependencyType.REQUIRED:
                if dep.target_module not in already_loaded:
                    if dep.target_module in available_modules:
                        return False  # Required dependency not yet loaded
                    else:
                        logger.error(f"Required dependency {dep.target_module} not available for {module}")
                        return False
            elif dep.dependency_type == DependencyType.CONFLICTS:
                if dep.target_module in already_loaded:
                    logger.error(f"Conflicting module {dep.target_module} already loaded, cannot load {module}")
                    return False
        
        return True
    
    def get_module_dependencies(self, module_id: str) -> Dict[str, List[str]]:
        """
        Get all dependencies for a specific module.
        
        Args:
            module_id: Module to get dependencies for
            
        Returns:
            Dictionary of dependency types and their targets
        """
        result = {
            "required": [],
            "optional": [],
            "conflicts": []
        }
        
        if module_id in self.dependencies:
            for dep in self.dependencies[module_id]:
                if dep.dependency_type == DependencyType.REQUIRED:
                    result["required"].append(dep.target_module)
                elif dep.dependency_type == DependencyType.OPTIONAL:
                    result["optional"].append(dep.target_module)
                elif dep.dependency_type == DependencyType.CONFLICTS:
                    result["conflicts"].append(dep.target_module)
        
        return result
    
    def get_dependent_modules(self, module_id: str) -> List[str]:
        """
        Get all modules that depend on the specified module.
        
        Args:
            module_id: Module to find dependents for
            
        Returns:
            List of modules that depend on this module
        """
        dependents = []
        
        for source_module, deps in self.dependencies.items():
            for dep in deps:
                if (dep.target_module == module_id and 
                    dep.dependency_type in [DependencyType.REQUIRED, DependencyType.OPTIONAL]):
                    dependents.append(source_module)
        
        return list(set(dependents))  # Remove duplicates
    
    def validate_dependencies(self, available_modules: List[str]) -> Dict[str, Any]:
        """
        Validate all dependencies against available modules.
        
        Args:
            available_modules: List of available modules
            
        Returns:
            Validation results
        """
        validation_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "valid",
            "issues": [],
            "warnings": [],
            "statistics": {
                "total_dependencies": 0,
                "missing_dependencies": 0,
                "circular_dependencies": 0,
                "conflicts": 0
            }
        }
        
        available_set = set(available_modules)
        
        # Check each module's dependencies
        for module_id, deps in self.dependencies.items():
            validation_result["statistics"]["total_dependencies"] += len(deps)
            
            for dep in deps:
                if dep.dependency_type == DependencyType.REQUIRED:
                    if dep.target_module not in available_set:
                        validation_result["issues"].append(
                            f"Module {module_id} requires {dep.target_module} which is not available"
                        )
                        validation_result["statistics"]["missing_dependencies"] += 1
                        validation_result["overall_status"] = "invalid"
                
                elif dep.dependency_type == DependencyType.OPTIONAL:
                    if dep.target_module not in available_set:
                        validation_result["warnings"].append(
                            f"Module {module_id} has optional dependency {dep.target_module} which is not available"
                        )
                
                elif dep.dependency_type == DependencyType.CONFLICTS:
                    if dep.target_module in available_set:
                        validation_result["issues"].append(
                            f"Module {module_id} conflicts with {dep.target_module} which is available"
                        )
                        validation_result["statistics"]["conflicts"] += 1
                        if validation_result["overall_status"] == "valid":
                            validation_result["overall_status"] = "warning"
        
        # Check for circular dependencies
        try:
            loading_order, failed_modules = self.calculate_loading_order(available_modules)
            if failed_modules:
                validation_result["statistics"]["circular_dependencies"] = len(failed_modules)
                validation_result["issues"].extend([
                    f"Circular dependency detected for module {module}" for module in failed_modules
                ])
                validation_result["overall_status"] = "invalid"
        except Exception as e:
            validation_result["issues"].append(f"Failed to check circular dependencies: {str(e)}")
            validation_result["overall_status"] = "invalid"
        
        return validation_result
    
    def export_dependency_graph(self) -> Dict[str, Any]:
        """
        Export the dependency graph for visualization or analysis.
        
        Returns:
            Dependency graph data
        """
        graph = {
            "nodes": [],
            "edges": [],
            "metadata": {
                "exported_at": datetime.utcnow().isoformat(),
                "total_modules": len(self.dependencies),
                "total_dependencies": sum(len(deps) for deps in self.dependencies.values())
            }
        }
        
        # Add nodes (modules)
        all_modules = set(self.dependencies.keys())
        for deps in self.dependencies.values():
            for dep in deps:
                all_modules.add(dep.target_module)
        
        for module in all_modules:
            metadata = self.module_metadata.get(module, {})
            graph["nodes"].append({
                "id": module,
                "label": metadata.get("display_name", module),
                "category": metadata.get("category", "unknown"),
                "enabled": metadata.get("enabled", False)
            })
        
        # Add edges (dependencies)
        for source_module, deps in self.dependencies.items():
            for dep in deps:
                graph["edges"].append({
                    "source": source_module,
                    "target": dep.target_module,
                    "type": dep.dependency_type.value,
                    "description": dep.description,
                    "version_constraint": dep.version_constraint
                })
        
        return graph
    
    def import_dependency_graph(self, graph_data: Dict[str, Any]) -> bool:
        """
        Import dependency graph from external data.
        
        Args:
            graph_data: Graph data to import
            
        Returns:
            Success status
        """
        try:
            # Clear existing dependencies
            self.dependencies.clear()
            self.module_metadata.clear()
            
            # Import nodes (module metadata)
            for node in graph_data.get("nodes", []):
                self.module_metadata[node["id"]] = {
                    "display_name": node.get("label", node["id"]),
                    "category": node.get("category", "unknown"),
                    "enabled": node.get("enabled", False)
                }
            
            # Import edges (dependencies)
            for edge in graph_data.get("edges", []):
                dependency = ModuleDependency(
                    source_module=edge["source"],
                    target_module=edge["target"],
                    dependency_type=DependencyType(edge["type"]),
                    version_constraint=edge.get("version_constraint"),
                    description=edge.get("description")
                )
                self.add_dependency(dependency)
            
            logger.info("Successfully imported dependency graph")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import dependency graph: {e}")
            return False
    
    def get_dependency_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the dependency system status.
        
        Returns:
            Dependency summary
        """
        total_deps = sum(len(deps) for deps in self.dependencies.values())
        required_deps = sum(
            len([d for d in deps if d.dependency_type == DependencyType.REQUIRED])
            for deps in self.dependencies.values()
        )
        optional_deps = sum(
            len([d for d in deps if d.dependency_type == DependencyType.OPTIONAL])
            for deps in self.dependencies.values()
        )
        conflicts = sum(
            len([d for d in deps if d.dependency_type == DependencyType.CONFLICTS])
            for deps in self.dependencies.values()
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_modules": len(self.dependencies),
            "total_dependencies": total_deps,
            "required_dependencies": required_deps,
            "optional_dependencies": optional_deps,
            "conflicts": conflicts,
            "loading_order_calculated": bool(self.loading_order),
            "conflict_resolution_strategy": self.conflict_resolution_strategy
        }