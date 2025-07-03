import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import tempfile
from urllib.parse import urljoin
import time
from sqlmodel import Session
from .config import Config
from .version_utils import get_app_version, check_compatibility_conditions, supports_content_pack_variables, supports_new_prompt_categories
from .variable_resolver import VariableResolver, create_variable_resolver
from .content_pack_variables import get_variable_manager
from .database_compat import get_session


class ContentPackManager:
    """
    Manages loading and exporting of content packs for IntentVerse.

    Content packs contain:
    - Metadata: Information about the pack
    - Database: SQL statements to populate the database
    - Prompts: Text prompts for AI interaction
    - State: StateManager content for all modules except database
    """

    def __init__(self, state_manager: Any, module_loader: Any):
        self.state_manager = state_manager
        self.module_loader = module_loader
        self.content_packs_dir = Path(__file__).parent.parent / "content_packs"
        self.loaded_packs = []

        # Variable resolution system
        self.variable_resolver = None
        self._init_variable_resolver()

        # Remote repository configuration
        self.remote_repo_url = Config.get_remote_repo_url()
        self.manifest_url = Config.get_manifest_url()
        self.remote_cache_dir = Path(__file__).parent.parent / "cache" / "remote_packs"
        self.remote_cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache for remote manifest
        self._remote_manifest = None
        self._manifest_cache_time = None
        self._manifest_cache_duration = Config.get_cache_duration()

        # HTTP client for remote requests
        self._http_client = httpx.Client(timeout=Config.get_http_timeout())

    def _init_variable_resolver(self):
        """Initialize the variable resolver with database support if available."""
        try:
            if supports_content_pack_variables():
                # Create variable resolver with database support
                for session in get_session():
                    variable_manager = get_variable_manager(session)
                    self.variable_resolver = VariableResolver(variable_manager)
                    break
                logging.debug("Variable resolver initialized with database support")
            else:
                # Create basic variable resolver without database support
                self.variable_resolver = create_variable_resolver()
                logging.debug("Variable resolver initialized without database support")
        except Exception as e:
            logging.warning(f"Failed to initialize variable resolver: {e}")
            self.variable_resolver = create_variable_resolver()

    def load_default_content_pack(self):
        """Load the default content pack if it exists."""
        default_pack_path = self.content_packs_dir / "default.json"
        if default_pack_path.exists():
            try:
                self.load_content_pack(default_pack_path)
                logging.info("Default content pack loaded successfully")
            except Exception as e:
                logging.error(f"Failed to load default content pack: {e}")
        else:
            logging.warning("Default content pack not found")

    def load_content_pack(self, pack_path, user_id: Optional[int] = None) -> bool:
        """
        Load a content pack from a JSON file with variable resolution support.

        Args:
            pack_path: Path to the content pack JSON file
            user_id: User ID for variable resolution (optional)

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Convert string path to Path object if needed
            if isinstance(pack_path, str):
                pack_path = Path(pack_path)
            
            with open(pack_path, "r", encoding="utf-8") as f:
                content_pack = json.load(f)

            # Validate content pack structure
            if not self._validate_content_pack(content_pack):
                logging.error(f"Invalid content pack structure: {pack_path}")
                return False

            # Check compatibility
            if not self._is_pack_compatible(content_pack):
                pack_name = content_pack.get("metadata", {}).get("name", str(pack_path))
                reason = self._get_incompatibility_reason(content_pack)
                logging.error(
                    f"Content pack '{pack_name}' is incompatible with IntentVerse {get_app_version()}: {reason}"
                )
                return False

            # Get pack name for variable resolution
            pack_name = content_pack.get("metadata", {}).get("name", pack_path.stem)

            # Resolve variables if supported and variables are defined
            resolved_content_pack = content_pack
            if supports_content_pack_variables() and "variables" in content_pack:
                resolved_content_pack = self._resolve_content_pack_variables(
                    content_pack, pack_name, user_id
                )

            # Load database content
            if "database" in resolved_content_pack and resolved_content_pack["database"]:
                database_tool = self.module_loader.get_tool("database")
                if database_tool:
                    database_tool.load_content_pack_database(resolved_content_pack["database"])
                    logging.info(f"Loaded database content from {pack_path.name}")

            # Load state content (merge with existing state)
            if "state" in resolved_content_pack and resolved_content_pack["state"]:
                self._merge_state_content(resolved_content_pack["state"])
                logging.info(f"Loaded state content from {pack_path.name}")

            # Store metadata for tracking (include new prompt fields if present)
            pack_info = {
                "path": str(pack_path),
                "metadata": resolved_content_pack.get("metadata", {}),
                "loaded_at": datetime.now().isoformat(),
                "has_variables": "variables" in content_pack,
                "has_content_prompts": "content_prompts" in content_pack,
                "has_usage_prompts": "usage_prompts" in content_pack,
                "has_legacy_prompts": "prompts" in content_pack,
                "user_id": user_id,
            }
            
            # Check if a pack with the same name already exists and replace it
            pack_name = resolved_content_pack.get("metadata", {}).get("name", pack_path.stem)
            existing_pack_index = None
            for i, existing_pack in enumerate(self.loaded_packs):
                if existing_pack.get("metadata", {}).get("name") == pack_name:
                    existing_pack_index = i
                    break
            
            if existing_pack_index is not None:
                # Replace existing pack
                self.loaded_packs[existing_pack_index] = pack_info
                logging.info(f"Replaced existing content pack: {pack_name}")
            else:
                # Add new pack
                self.loaded_packs.append(pack_info)

            logging.info(f"Successfully loaded content pack: {pack_path.name}")
            return True

        except Exception as e:
            logging.error(f"Error loading content pack {pack_path}: {e}")
            return False

    def _resolve_content_pack_variables(
        self, content_pack: Dict[str, Any], pack_name: str, user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Resolve variables in a content pack using the variable resolver.

        Args:
            content_pack: Original content pack data
            pack_name: Name of the content pack
            user_id: User ID for variable resolution

        Returns:
            Content pack with variables resolved
        """
        try:
            if not self.variable_resolver:
                logging.warning("Variable resolver not available, returning original content pack")
                return content_pack

            # Get pack defaults
            pack_defaults = content_pack.get("variables", {})
            
            # Validate variables before resolution
            validation = self.variable_resolver.validate_content_pack_variables(
                content_pack, pack_defaults
            )
            
            if not validation["valid"]:
                logging.warning(
                    f"Content pack '{pack_name}' has undefined variables: {validation['undefined_variables']}"
                )
                # Continue with resolution in non-strict mode
            
            # Resolve variables in the content pack
            resolved_pack = self.variable_resolver.resolve_data_structure(
                content_pack, pack_defaults, pack_name, user_id, strict=False
            )
            
            logging.info(
                f"Resolved {len(validation.get('used_variables', []))} variables in content pack '{pack_name}'"
            )
            
            return resolved_pack

        except Exception as e:
            logging.error(f"Error resolving variables in content pack '{pack_name}': {e}")
            return content_pack

    def export_content_pack(
        self, output_path: Path, metadata: Optional[Dict[str, Any]] = None, 
        include_variables: bool = True, variables: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Export current system state as a content pack with v1.1.0 structure.

        Args:
            output_path: Path where to save the content pack
            metadata: Optional metadata to include
            include_variables: Whether to include variables section
            variables: Optional variables to include in the pack

        Returns:
            True if exported successfully, False otherwise
        """
        try:
            content_pack = {
                "metadata": metadata or self._generate_default_metadata(),
                "database": [],
                "state": {},
            }

            # Determine if we should include v1.1.0 fields based on loaded packs
            has_v11_features = any(
                pack.get("has_content_prompts", False) or pack.get("has_usage_prompts", False) or pack.get("has_variables", False)
                for pack in self.loaded_packs
            )
            
            # Add new v1.1.0 fields if supported and we have v1.1.0 features
            if supports_new_prompt_categories() and has_v11_features:
                content_pack["content_prompts"] = []
                content_pack["usage_prompts"] = []
            
            # Keep legacy prompts field for backward compatibility
            content_pack["prompts"] = []

            # Add variables section if supported and requested and we have v1.1.0 features
            if supports_content_pack_variables() and include_variables and has_v11_features:
                content_pack["variables"] = variables or {}

            # Export database content
            database_tool = self.module_loader.get_tool("database")
            if database_tool:
                content_pack["database"] = database_tool.export_database_content()

            # Export state content (exclude database module)
            full_state = self.state_manager.get_full_state()
            for module_name, module_state in full_state.items():
                if module_name != "database":  # Database is handled separately
                    content_pack["state"][module_name] = module_state

            # Export prompts from loaded content packs
            all_prompts = []
            all_content_prompts = []
            all_usage_prompts = []
            
            for pack in self.loaded_packs:
                try:
                    pack_path = Path(pack["path"])
                    if pack_path.exists():
                        with open(pack_path, "r", encoding="utf-8") as f:
                            pack_data = json.load(f)
                        
                        # Collect legacy prompts
                        if "prompts" in pack_data:
                            all_prompts.extend(pack_data["prompts"])
                        
                        # Collect v1.1.0 prompts
                        if "content_prompts" in pack_data:
                            all_content_prompts.extend(pack_data["content_prompts"])
                        if "usage_prompts" in pack_data:
                            all_usage_prompts.extend(pack_data["usage_prompts"])
                            
                except Exception as e:
                    logging.warning(f"Could not export prompts from pack {pack['path']}: {e}")
            
            # Update the content pack with collected prompts
            content_pack["prompts"] = all_prompts
            if supports_new_prompt_categories() and has_v11_features:
                content_pack["content_prompts"] = all_content_prompts
                content_pack["usage_prompts"] = all_usage_prompts

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(content_pack, f, indent=2, ensure_ascii=False)

            logging.info(f"Content pack exported to: {output_path}")
            return True

        except Exception as e:
            logging.error(f"Error exporting content pack to {output_path}: {e}")
            return False

    def get_pack_variables(self, pack_name: str, user_id: int) -> Dict[str, str]:
        """
        Get all variable overrides for a specific content pack and user.

        Args:
            pack_name: Name of the content pack
            user_id: ID of the user

        Returns:
            Dictionary mapping variable names to their values
        """
        try:
            if not supports_content_pack_variables():
                logging.warning("Content pack variables not supported in this version")
                return {}

            for session in get_session():
                variable_manager = get_variable_manager(session)
                return variable_manager.get_pack_variables(pack_name, user_id)

        except Exception as e:
            logging.error(f"Error getting variables for pack '{pack_name}' and user {user_id}: {e}")
            return {}

    def set_pack_variable(self, pack_name: str, variable_name: str, value: str, user_id: int) -> bool:
        """
        Set a variable value for a content pack and user.

        Args:
            pack_name: Name of the content pack
            variable_name: Name of the variable
            value: Value to set
            user_id: ID of the user

        Returns:
            True if successful, False otherwise
        """
        try:
            if not supports_content_pack_variables():
                logging.warning("Content pack variables not supported in this version")
                return False

            for session in get_session():
                variable_manager = get_variable_manager(session)
                return variable_manager.set_variable_value(pack_name, variable_name, value, user_id)

        except Exception as e:
            logging.error(f"Error setting variable '{variable_name}' for pack '{pack_name}' and user {user_id}: {e}")
            return False

    def reset_pack_variables(self, pack_name: str, user_id: int) -> bool:
        """
        Reset all variable overrides for a specific content pack and user.

        Args:
            pack_name: Name of the content pack
            user_id: ID of the user

        Returns:
            True if successful, False otherwise
        """
        try:
            if not supports_content_pack_variables():
                logging.warning("Content pack variables not supported in this version")
                return False

            for session in get_session():
                variable_manager = get_variable_manager(session)
                return variable_manager.reset_pack_variables(pack_name, user_id)

        except Exception as e:
            logging.error(f"Error resetting variables for pack '{pack_name}' and user {user_id}: {e}")
            return False

    def list_available_content_packs(self) -> List[Dict[str, Any]]:
        """
        List all available content packs in the content_packs directory.

        Returns:
            List of content pack information
        """
        packs = []

        if not self.content_packs_dir.exists():
            return packs

        for pack_file in self.content_packs_dir.glob("*.json"):
            try:
                with open(pack_file, "r", encoding="utf-8") as f:
                    content_pack = json.load(f)

                pack_info = {
                    "filename": pack_file.name,
                    "path": str(pack_file),
                    "metadata": content_pack.get("metadata", {}),
                    "has_database": bool(content_pack.get("database")),
                    "has_state": bool(content_pack.get("state")),
                    "has_prompts": bool(content_pack.get("prompts")),
                    "has_variables": bool(content_pack.get("variables")),
                    "has_content_prompts": bool(content_pack.get("content_prompts")),
                    "has_usage_prompts": bool(content_pack.get("usage_prompts")),
                    "variable_count": len(content_pack.get("variables", {})),
                    "content_prompts_count": len(content_pack.get("content_prompts", [])),
                    "usage_prompts_count": len(content_pack.get("usage_prompts", [])),
                }
                packs.append(pack_info)

            except Exception as e:
                logging.error(f"Error reading content pack {pack_file}: {e}")

        return packs

    def get_loaded_packs_info(self) -> List[Dict[str, Any]]:
        """Get information about currently loaded content packs."""
        return self.loaded_packs.copy()

    def get_loaded_content_packs(self) -> List[Dict[str, Any]]:
        """Get information about currently loaded content packs with features."""
        result = []
        for pack in self.loaded_packs:
            pack_info = pack.copy()
            # Add features information
            pack_info["features"] = {
                "has_variables": pack.get("has_variables", False),
                "has_content_prompts": pack.get("has_content_prompts", False),
                "has_usage_prompts": pack.get("has_usage_prompts", False),
                "has_prompts": pack.get("has_legacy_prompts", False),
                "has_database": self._pack_has_database(pack),
                "has_state": self._pack_has_state(pack),
            }
            # Extract name from metadata for easier access
            pack_info["name"] = pack.get("metadata", {}).get("name", "")
            result.append(pack_info)
        return result

    def get_content_pack_data(self, pack_name: str) -> Dict[str, Any]:
        """Get the data for a specific loaded content pack."""
        for pack in self.loaded_packs:
            if pack.get("metadata", {}).get("name") == pack_name:
                # Load the pack data from file
                pack_path = Path(pack["path"])
                if pack_path.exists():
                    try:
                        with open(pack_path, "r", encoding="utf-8") as f:
                            return json.load(f)
                    except Exception as e:
                        logging.error(f"Error reading pack data from {pack_path}: {e}")
                        raise ValueError(f"Could not read pack data: {e}")
        raise ValueError(f"Content pack '{pack_name}' not found in loaded packs")

    def _pack_has_database(self, pack_info: Dict[str, Any]) -> bool:
        """Check if a loaded pack has database content."""
        try:
            pack_path = Path(pack_info["path"])
            if pack_path.exists():
                with open(pack_path, "r", encoding="utf-8") as f:
                    pack_data = json.load(f)
                return bool(pack_data.get("database"))
        except Exception:
            pass
        return False

    def _pack_has_state(self, pack_info: Dict[str, Any]) -> bool:
        """Check if a loaded pack has state content."""
        try:
            pack_path = Path(pack_info["path"])
            if pack_path.exists():
                with open(pack_path, "r", encoding="utf-8") as f:
                    pack_data = json.load(f)
                return bool(pack_data.get("state"))
        except Exception:
            pass
        return False

    def load_content_pack_by_filename(self, filename: str) -> bool:
        """
        Load a content pack by filename from the content_packs directory.

        Args:
            filename: Name of the content pack file to load

        Returns:
            True if loaded successfully, False otherwise
        """
        pack_path = self.content_packs_dir / filename
        if not pack_path.exists():
            logging.error(f"Content pack file not found: {filename}")
            return False

        return self.load_content_pack(pack_path)

    def unload_content_pack(self, pack_identifier: str) -> bool:
        """
        Unload a content pack. Note: This only removes it from the loaded_packs list.
        The actual state and database changes cannot be easily reverted without
        implementing a more complex state management system.

        Args:
            pack_identifier: Either the filename or the pack name to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        try:
            # Find the pack to unload
            pack_to_remove = None
            for i, pack in enumerate(self.loaded_packs):
                pack_filename = Path(pack["path"]).name
                pack_name = pack.get("metadata", {}).get("name", "")

                if pack_identifier == pack_filename or pack_identifier == pack_name:
                    pack_to_remove = i
                    break

            if pack_to_remove is not None:
                self.loaded_packs.pop(pack_to_remove)
                logging.info(f"Unloaded content pack: {pack_identifier}")
                return True
            else:
                logging.warning(
                    f"Content pack not found in loaded packs: {pack_identifier}"
                )
                return False

        except Exception as e:
            logging.error(f"Error unloading content pack {pack_identifier}: {e}")
            return False

    def clear_all_loaded_packs(self) -> bool:
        """
        Clear all loaded content packs from the tracking list.
        Note: This does not revert state or database changes.

        Returns:
            True if cleared successfully
        """
        try:
            self.loaded_packs.clear()
            logging.info("Cleared all loaded content packs from tracking")
            return True
        except Exception as e:
            logging.error(f"Error clearing loaded packs: {e}")
            return False

    def validate_content_pack_detailed(
        self, content_pack: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform detailed validation of a content pack and return validation results.

        Args:
            content_pack: The content pack dictionary to validate

        Returns:
            Dictionary with validation results, errors, and warnings
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "summary": {
                "has_metadata": False,
                "has_database": False,
                "has_state": False,
                "has_prompts": False,
                "database_statements": 0,
                "state_modules": [],
                "prompts_count": 0,
            },
        }

        # Check that it's a dictionary
        if not isinstance(content_pack, dict):
            validation_result["is_valid"] = False
            validation_result["errors"].append("Content pack must be a JSON object")
            return validation_result

        # Check for required top-level keys (include new v1.1.0 fields)
        content_fields = ["database", "state", "prompts", "content_prompts", "usage_prompts"]
        has_content = any(key in content_pack for key in content_fields)
        if not has_content:
            validation_result["is_valid"] = False
            validation_result["errors"].append(
                "Content pack must contain at least one of: database, state, prompts, content_prompts, or usage_prompts"
            )

        # Validate metadata section
        if "metadata" in content_pack:
            validation_result["summary"]["has_metadata"] = True
            metadata = content_pack["metadata"]
            if not isinstance(metadata, dict):
                validation_result["errors"].append("Metadata section must be an object")
            else:
                # Check for recommended metadata fields
                recommended_fields = ["name", "summary", "version"]
                missing_fields = [
                    field for field in recommended_fields if not metadata.get(field)
                ]
                if missing_fields:
                    validation_result["warnings"].append(
                        f"Missing recommended metadata fields: {', '.join(missing_fields)}"
                    )
        else:
            validation_result["warnings"].append(
                "No metadata section found - recommended for content pack identification"
            )

        # Validate database section
        if "database" in content_pack:
            validation_result["summary"]["has_database"] = True
            database = content_pack["database"]
            if not isinstance(database, list):
                validation_result["errors"].append(
                    "Database section must be an array of SQL statements"
                )
            else:
                validation_result["summary"]["database_statements"] = len(database)
                # Validate database content - support both v1.1.0 (SQL strings) and v1.0.0 (objects) formats
                for i, item in enumerate(database):
                    if isinstance(item, str):
                        # v1.1.0 format: SQL string
                        if not item.strip():
                            validation_result["warnings"].append(
                                f"Database statement {i+1} is empty"
                            )
                        elif not any(
                            item.strip().upper().startswith(cmd)
                            for cmd in ["CREATE", "INSERT", "UPDATE", "DELETE", "ALTER"]
                        ):
                            validation_result["warnings"].append(
                                f"Database statement {i+1} may not be a valid SQL command"
                            )
                    elif isinstance(item, dict):
                        # v1.0.0 format: object with table and data
                        if not item.get("table"):
                            validation_result["warnings"].append(
                                f"Database item {i+1} missing table name (v1.0 format)"
                            )
                        if not item.get("data"):
                            validation_result["warnings"].append(
                                f"Database item {i+1} missing data (v1.0 format)"
                            )
                    else:
                        validation_result["errors"].append(
                            f"Database item {i+1} must be either a SQL string (v1.1+) or an object with table/data (v1.0)"
                        )

        # Validate state section
        if "state" in content_pack:
            validation_result["summary"]["has_state"] = True
            state = content_pack["state"]
            if not isinstance(state, dict):
                validation_result["errors"].append("State section must be an object")
            else:
                validation_result["summary"]["state_modules"] = list(state.keys())
                # Check for known module types
                known_modules = ["filesystem", "email", "memory", "web_search"]
                unknown_modules = [
                    module
                    for module in state.keys()
                    if module not in known_modules and module != "database"
                ]
                if unknown_modules:
                    validation_result["warnings"].append(
                        f"Unknown state modules (may be custom): {', '.join(unknown_modules)}"
                    )

        # Validate prompts section
        if "prompts" in content_pack:
            validation_result["summary"]["has_prompts"] = True
            prompts = content_pack["prompts"]
            if not isinstance(prompts, list):
                validation_result["errors"].append("Prompts section must be an array")
            else:
                validation_result["summary"]["prompts_count"] = len(prompts)
                # Validate prompt structure
                for i, prompt in enumerate(prompts):
                    if not isinstance(prompt, dict):
                        validation_result["errors"].append(
                            f"Prompt {i+1} must be an object"
                        )
                    else:
                        # Support both v1.1.0 format (name, content) and v1.0.0 format (title/id, prompt)
                        has_v11_fields = prompt.get("name") and prompt.get("content")
                        has_v10_fields = (prompt.get("title") or prompt.get("id")) and prompt.get("prompt")
                        
                        if not has_v11_fields and not has_v10_fields:
                            validation_result["errors"].append(
                                f"Prompt {i+1} missing required fields: either (name, content) for v1.1+ or (title/id, prompt) for v1.0"
                            )

        # Validate variables section (v1.1.0+)
        if "variables" in content_pack:
            validation_result["summary"]["has_variables"] = True
            variables = content_pack["variables"]
            if not isinstance(variables, dict):
                validation_result["errors"].append("Variables section must be an object")
            else:
                validation_result["summary"]["variables_count"] = len(variables)
                # Validate variable names and values
                for var_name, var_value in variables.items():
                    if not isinstance(var_name, str):
                        validation_result["errors"].append(
                            f"Variable name must be a string: {var_name}"
                        )
                    elif not self._is_valid_variable_name(var_name):
                        validation_result["errors"].append(
                            f"Invalid variable name '{var_name}': must start with letter/underscore, followed by letters/numbers/underscores"
                        )
                    
                    if not isinstance(var_value, str):
                        validation_result["errors"].append(
                            f"Variable value must be a string: {var_name} = {var_value}"
                        )

                # Validate variable usage if variable resolver is available
                if hasattr(self, 'variable_resolver') and self.variable_resolver:
                    try:
                        var_validation = self.variable_resolver.validate_content_pack_variables(
                            content_pack, variables
                        )
                        if not var_validation["valid"]:
                            for undefined_var in var_validation.get("undefined_variables", []):
                                validation_result["warnings"].append(
                                    f"Variable '{undefined_var}' is used but not defined"
                                )
                        
                        for unused_var in var_validation.get("unused_variables", []):
                            validation_result["warnings"].append(
                                f"Variable '{unused_var}' is defined but not used"
                            )
                    except Exception as e:
                        validation_result["warnings"].append(
                            f"Could not validate variable usage: {e}"
                        )

        # Validate content_prompts section (v1.1.0+)
        if "content_prompts" in content_pack:
            validation_result["summary"]["has_content_prompts"] = True
            content_prompts = content_pack["content_prompts"]
            if not isinstance(content_prompts, list):
                validation_result["errors"].append("Content prompts section must be an array")
            else:
                validation_result["summary"]["content_prompts_count"] = len(content_prompts)
                # Validate content prompt structure
                for i, prompt in enumerate(content_prompts):
                    if not isinstance(prompt, dict):
                        validation_result["errors"].append(
                            f"Content prompt {i+1} must be an object"
                        )
                    else:
                        # Support both v1.1.0 format (name, content) and v1.0.0 format (title/id, prompt)
                        has_v11_fields = prompt.get("name") and prompt.get("content")
                        has_v10_fields = (prompt.get("title") or prompt.get("id")) and prompt.get("prompt")
                        
                        if not has_v11_fields and not has_v10_fields:
                            validation_result["errors"].append(
                                f"Content prompt {i+1} missing required fields: either (name, content) for v1.1+ or (title/id, prompt) for v1.0"
                            )

        # Validate usage_prompts section (v1.1.0+)
        if "usage_prompts" in content_pack:
            validation_result["summary"]["has_usage_prompts"] = True
            usage_prompts = content_pack["usage_prompts"]
            if not isinstance(usage_prompts, list):
                validation_result["errors"].append("Usage prompts section must be an array")
            else:
                validation_result["summary"]["usage_prompts_count"] = len(usage_prompts)
                # Validate usage prompt structure
                for i, prompt in enumerate(usage_prompts):
                    if not isinstance(prompt, dict):
                        validation_result["errors"].append(
                            f"Usage prompt {i+1} must be an object"
                        )
                    else:
                        # Support both v1.1.0 format (name, content) and v1.0.0 format (title/id, prompt)
                        has_v11_fields = prompt.get("name") and prompt.get("content")
                        has_v10_fields = (prompt.get("title") or prompt.get("id")) and prompt.get("prompt")
                        
                        if not has_v11_fields and not has_v10_fields:
                            validation_result["errors"].append(
                                f"Usage prompt {i+1} missing required fields: either (name, content) for v1.1+ or (title/id, prompt) for v1.0"
                            )

        # Set final validation status
        if validation_result["errors"]:
            validation_result["is_valid"] = False

        return validation_result

    def _is_valid_variable_name(self, name: str) -> bool:
        """
        Check if a variable name follows the correct syntax.

        Args:
            name: Variable name to check

        Returns:
            True if valid, False otherwise
        """
        if hasattr(self, 'variable_resolver') and self.variable_resolver:
            return self.variable_resolver.validate_variable_name(name)
        else:
            # Fallback validation if variable resolver is not available
            import re
            pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
            return bool(pattern.match(name))

    def _validate_content_pack(self, content_pack: Dict[str, Any]) -> bool:
        """
        Simple validation for backward compatibility.

        Args:
            content_pack: The content pack dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        validation_result = self.validate_content_pack_detailed(content_pack)
        return validation_result["is_valid"]

    def _is_pack_compatible(self, content_pack: Dict[str, Any]) -> bool:
        """
        Check if a content pack is compatible with the current IntentVerse version.

        Args:
            content_pack: The content pack dictionary to check

        Returns:
            True if compatible, False otherwise
        """
        metadata = content_pack.get("metadata", {})
        compatibility_conditions = metadata.get("compatibility_conditions", [])

        app_version = get_app_version()
        is_compatible, failure_reasons = check_compatibility_conditions(
            app_version, compatibility_conditions
        )

        if not is_compatible:
            pack_name = metadata.get("name", "Unknown")
            logging.info(
                f"Content pack '{pack_name}' is incompatible: {'; '.join(failure_reasons)}"
            )

        return is_compatible

    def _get_incompatibility_reason(self, content_pack: Dict[str, Any]) -> str:
        """
        Get the reason why a content pack is incompatible.

        Args:
            content_pack: The content pack dictionary to check

        Returns:
            Human-readable incompatibility reason
        """
        metadata = content_pack.get("metadata", {})
        compatibility_conditions = metadata.get("compatibility_conditions", [])

        app_version = get_app_version()
        is_compatible, failure_reasons = check_compatibility_conditions(
            app_version, compatibility_conditions
        )

        if not is_compatible and failure_reasons:
            return failure_reasons[0]  # Return first reason

        return "Unknown compatibility issue"

    def preview_content_pack(self, filename: str) -> Dict[str, Any]:
        """
        Preview a content pack without loading it, including validation results.

        Args:
            filename: Name of the content pack file to preview

        Returns:
            Dictionary with content pack preview and validation information
        """
        pack_path = self.content_packs_dir / filename

        preview_result = {
            "filename": filename,
            "exists": False,
            "content_pack": None,
            "validation": None,
            "preview": {
                "metadata": {},
                "database_preview": [],
                "state_preview": {},
                "prompts_preview": [],
            },
        }

        if not pack_path.exists():
            preview_result["validation"] = {
                "is_valid": False,
                "errors": [f"Content pack file '{filename}' not found"],
                "warnings": [],
                "summary": {},
            }
            return preview_result

        try:
            with open(pack_path, "r", encoding="utf-8") as f:
                content_pack = json.load(f)

            preview_result["exists"] = True
            preview_result["content_pack"] = content_pack

            # Perform detailed validation
            preview_result["validation"] = self.validate_content_pack_detailed(
                content_pack
            )

            # Generate preview information
            if "metadata" in content_pack:
                preview_result["preview"]["metadata"] = content_pack["metadata"]

            if "database" in content_pack and isinstance(
                content_pack["database"], list
            ):
                # Show first few database statements as preview
                db_statements = content_pack["database"]
                preview_result["preview"]["database_preview"] = db_statements[
                    :5
                ]  # First 5 statements

            if "state" in content_pack and isinstance(content_pack["state"], dict):
                # Create a summary of state content
                state_summary = {}
                for module_name, module_state in content_pack["state"].items():
                    if isinstance(module_state, dict):
                        state_summary[module_name] = {
                            "type": type(module_state).__name__,
                            "keys": list(module_state.keys())[:10],  # First 10 keys
                            "total_keys": (
                                len(module_state.keys())
                                if hasattr(module_state, "keys")
                                else 0
                            ),
                        }
                    else:
                        state_summary[module_name] = {
                            "type": type(module_state).__name__,
                            "value": (
                                str(module_state)[:100] + "..."
                                if len(str(module_state)) > 100
                                else str(module_state)
                            ),
                        }
                preview_result["preview"]["state_preview"] = state_summary

            if "prompts" in content_pack and isinstance(content_pack["prompts"], list):
                # Show prompt summaries
                prompts_preview = []
                for prompt in content_pack["prompts"][:5]:  # First 5 prompts
                    if isinstance(prompt, dict):
                        prompt_summary = {
                            "name": prompt.get("name", "Unnamed"),
                            "description": prompt.get("description", "No description"),
                            "content_length": len(prompt.get("content", "")),
                        }
                        prompts_preview.append(prompt_summary)
                preview_result["preview"]["prompts_preview"] = prompts_preview

        except json.JSONDecodeError as e:
            preview_result["validation"] = {
                "is_valid": False,
                "errors": [f"Invalid JSON format: {str(e)}"],
                "warnings": [],
                "summary": {},
            }
        except Exception as e:
            preview_result["validation"] = {
                "is_valid": False,
                "errors": [f"Error reading content pack: {str(e)}"],
                "warnings": [],
                "summary": {},
            }

        return preview_result

    def _merge_state_content(self, new_state: Dict[str, Any]):
        """
        Merge new state content with existing state using intelligent merging strategies.

        Args:
            new_state: State content to merge
        """
        for module_name, module_state in new_state.items():
            if module_name == "database":
                continue  # Skip database - handled separately

            # Get existing state for this module
            existing_state = self.state_manager.get(module_name)

            if existing_state is None:
                # No existing state, just set the new state
                self.state_manager.set(module_name, module_state)
                logging.debug(f"Set initial state for module: {module_name}")
            else:
                # Merge with existing state using appropriate strategy
                merged_state = self._merge_module_state(
                    module_name, existing_state, module_state
                )
                self.state_manager.set(module_name, merged_state)
                logging.debug(f"Merged state for module: {module_name}")

    def _merge_module_state(
        self, module_name: str, existing_state: Any, new_state: Any
    ) -> Any:
        """
        Merge module state using appropriate strategy based on module type and data structure.

        Args:
            module_name: Name of the module
            existing_state: Current state of the module
            new_state: New state to merge in

        Returns:
            Merged state
        """
        # Handle different module types with appropriate merging strategies
        if module_name == "email":
            return self._merge_email_state(existing_state, new_state)
        elif module_name == "filesystem":
            return self._merge_filesystem_state(existing_state, new_state)
        elif module_name == "memory":
            return self._merge_memory_state(existing_state, new_state)
        elif module_name == "web_search":
            return self._merge_web_search_state(existing_state, new_state)
        else:
            # For unknown modules, try generic dictionary merging
            return self._merge_generic_state(existing_state, new_state)

    def _merge_email_state(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge email module state by combining inbox, sent, and drafts arrays.

        Args:
            existing: Existing email state
            new: New email state to merge

        Returns:
            Merged email state
        """
        if not isinstance(existing, dict) or not isinstance(new, dict):
            logging.warning("Email state is not a dictionary, using new state")
            return new

        merged = existing.copy()

        # Merge each email folder (inbox, sent, drafts)
        for folder_name in ["inbox", "sent", "drafts"]:
            existing_emails = existing.get(folder_name, [])
            new_emails = new.get(folder_name, [])

            if not isinstance(existing_emails, list):
                existing_emails = []
            if not isinstance(new_emails, list):
                new_emails = []

            # Combine emails, avoiding duplicates based on id if present
            merged_emails = existing_emails.copy()
            existing_ids = {
                email.get("id")
                for email in existing_emails
                if isinstance(email, dict) and "id" in email
            }

            for email in new_emails:
                if isinstance(email, dict):
                    email_id = email.get("id")
                    if email_id is None or email_id not in existing_ids:
                        merged_emails.append(email)
                else:
                    merged_emails.append(email)

            merged[folder_name] = merged_emails

        # Merge any other keys that might exist
        for key, value in new.items():
            if key not in ["inbox", "sent", "drafts"]:
                merged[key] = value

        return merged

    def _merge_filesystem_state(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge filesystem state by combining directory trees.

        Args:
            existing: Existing filesystem state
            new: New filesystem state to merge

        Returns:
            Merged filesystem state
        """
        if not isinstance(existing, dict) or not isinstance(new, dict):
            logging.warning("Filesystem state is not a dictionary, using new state")
            return new

        # If either is not a proper filesystem node, use new state
        if existing.get("type") != "directory" or new.get("type") != "directory":
            return new

        # Merge directory trees
        return self._merge_filesystem_node(existing, new)

    def _merge_filesystem_node(
        self, existing_node: Dict[str, Any], new_node: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively merge filesystem nodes (files and directories).

        Args:
            existing_node: Existing filesystem node
            new_node: New filesystem node to merge

        Returns:
            Merged filesystem node
        """
        if not isinstance(existing_node, dict) or not isinstance(new_node, dict):
            return new_node

        # Start with existing node
        merged = existing_node.copy()

        # If it's a file, new content overwrites existing
        if new_node.get("type") == "file":
            return new_node

        # If it's a directory, merge children
        if (
            new_node.get("type") == "directory"
            and existing_node.get("type") == "directory"
        ):
            existing_children = existing_node.get("children", [])
            new_children = new_node.get("children", [])

            if not isinstance(existing_children, list):
                existing_children = []
            if not isinstance(new_children, list):
                new_children = []

            # Create a map of existing children by name
            existing_children_map = {}
            for child in existing_children:
                if isinstance(child, dict) and "name" in child:
                    existing_children_map[child["name"]] = child

            # Merge new children
            merged_children = []
            processed_names = set()

            # First, process existing children
            for child in existing_children:
                if isinstance(child, dict) and "name" in child:
                    child_name = child["name"]
                    # Check if there's a new child with the same name
                    new_child = None
                    for nc in new_children:
                        if isinstance(nc, dict) and nc.get("name") == child_name:
                            new_child = nc
                            break

                    if new_child:
                        # Merge the children
                        merged_child = self._merge_filesystem_node(child, new_child)
                        merged_children.append(merged_child)
                    else:
                        # Keep existing child
                        merged_children.append(child)

                    processed_names.add(child_name)
                else:
                    merged_children.append(child)

            # Add new children that don't exist in existing
            for new_child in new_children:
                if isinstance(new_child, dict) and "name" in new_child:
                    if new_child["name"] not in processed_names:
                        merged_children.append(new_child)
                else:
                    merged_children.append(new_child)

            merged["children"] = merged_children

        # Update other properties from new node
        for key, value in new_node.items():
            if key not in ["children"]:
                merged[key] = value

        return merged

    def _merge_memory_state(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge memory module state by deep merging dictionaries.

        Args:
            existing: Existing memory state
            new: New memory state to merge

        Returns:
            Merged memory state
        """
        if not isinstance(existing, dict) or not isinstance(new, dict):
            logging.warning("Memory state is not a dictionary, using new state")
            return new

        return self._deep_merge_dict(existing, new)

    def _merge_web_search_state(
        self, existing: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge web search module state.

        Args:
            existing: Existing web search state
            new: New web search state to merge

        Returns:
            Merged web search state
        """
        if not isinstance(existing, dict) or not isinstance(new, dict):
            logging.warning("Web search state is not a dictionary, using new state")
            return new

        # For web search, merge search history and cache
        merged = existing.copy()

        # Merge search history if it exists
        if "search_history" in new:
            existing_history = existing.get("search_history", [])
            new_history = new.get("search_history", [])

            if isinstance(existing_history, list) and isinstance(new_history, list):
                # Combine histories, avoiding duplicates
                merged_history = existing_history.copy()
                for item in new_history:
                    if item not in merged_history:
                        merged_history.append(item)
                merged["search_history"] = merged_history
            else:
                merged["search_history"] = new_history

        # Merge other keys
        for key, value in new.items():
            if key != "search_history":
                merged[key] = value

        return merged

    def _merge_generic_state(self, existing: Any, new: Any) -> Any:
        """
        Generic state merging for unknown module types.

        Args:
            existing: Existing state
            new: New state to merge

        Returns:
            Merged state
        """
        # If both are dictionaries, try deep merge
        if isinstance(existing, dict) and isinstance(new, dict):
            return self._deep_merge_dict(existing, new)

        # If both are lists, combine them
        if isinstance(existing, list) and isinstance(new, list):
            return existing + new

        # Otherwise, new state overwrites existing
        return new

    def _deep_merge_dict(
        self, dict1: Dict[str, Any], dict2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.

        Args:
            dict1: First dictionary
            dict2: Second dictionary (takes precedence)

        Returns:
            Merged dictionary
        """
        result = dict1.copy()

        for key, value in dict2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge_dict(result[key], value)
            else:
                result[key] = value

        return result

    def _generate_default_metadata(self) -> Dict[str, Any]:
        """Generate default metadata for content pack export."""
        return {
            "name": "",
            "summary": "",
            "detailed_description": "",
            "date_exported": datetime.now().isoformat(),
            "author_name": "",
            "author_email": "",
            "version": "1.1.0",
        }

    def fetch_remote_manifest(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch the remote content pack manifest from the repository.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Remote manifest dictionary or None if fetch fails
        """
        current_time = time.time()

        # Check if we have cached data and it's still valid
        if (
            not force_refresh
            and self._remote_manifest is not None
            and self._manifest_cache_time is not None
            and (current_time - self._manifest_cache_time)
            < self._manifest_cache_duration
        ):
            logging.debug("Using cached remote manifest")
            return self._remote_manifest

        try:
            logging.info(f"Fetching remote manifest from: {self.manifest_url}")
            response = self._http_client.get(self.manifest_url)
            response.raise_for_status()

            manifest_data = response.json()

            # Cache the manifest
            self._remote_manifest = manifest_data
            self._manifest_cache_time = current_time

            logging.info(
                f"Successfully fetched remote manifest with {len(manifest_data.get('content_packs', []))} content packs"
            )
            return manifest_data

        except httpx.RequestError as e:
            logging.error(f"Network error fetching remote manifest: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error fetching remote manifest: {e.response.status_code}"
            )
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in remote manifest: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching remote manifest: {e}")
            return None

    def list_remote_content_packs(
        self, force_refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List all available remote content packs that are compatible with current version.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            List of compatible remote content pack information
        """
        manifest = self.fetch_remote_manifest(force_refresh)
        if not manifest:
            logging.warning("Could not fetch remote manifest")
            return []

        all_content_packs = manifest.get("content_packs", [])
        compatible_packs = []

        for pack in all_content_packs:
            # Check compatibility
            if self._is_pack_compatible(pack):
                # Add remote-specific metadata
                pack["source"] = "remote"
                pack["download_url"] = urljoin(
                    self.remote_repo_url,
                    f"content-packs/{pack.get('relative_path', pack.get('filename', ''))}",
                )
                compatible_packs.append(pack)
            else:
                # Log why this pack was excluded
                pack_name = pack.get("name", pack.get("filename", "Unknown"))
                reason = self._get_incompatibility_reason(pack)
                logging.info(
                    f"Excluding incompatible remote pack '{pack_name}': {reason}"
                )

        logging.info(
            f"Filtered {len(all_content_packs)} remote packs to {len(compatible_packs)} compatible packs"
        )
        return compatible_packs

    def download_remote_content_pack(self, pack_filename: str) -> Optional[Path]:
        """
        Download a remote content pack to the local cache.

        Args:
            pack_filename: Filename of the content pack to download

        Returns:
            Path to downloaded file or None if download fails
        """
        # First get the manifest to find the pack details
        manifest = self.fetch_remote_manifest()
        if not manifest:
            logging.error("Could not fetch remote manifest for download")
            return None

        # Find the pack in the manifest
        pack_info = None
        for pack in manifest.get("content_packs", []):
            if pack.get("filename") == pack_filename:
                pack_info = pack
                break

        if not pack_info:
            logging.error(
                f"Content pack '{pack_filename}' not found in remote manifest"
            )
            return None

        # Construct download URL
        relative_path = pack_info.get("relative_path", pack_filename)
        download_url = urljoin(self.remote_repo_url, f"content-packs/{relative_path}")

        # Download to cache directory
        cache_file_path = self.remote_cache_dir / pack_filename

        try:
            logging.info(f"Downloading content pack from: {download_url}")
            response = self._http_client.get(download_url)
            response.raise_for_status()

            # Validate it's valid JSON
            content_pack_data = response.json()

            # Write to cache file
            with open(cache_file_path, "w", encoding="utf-8") as f:
                json.dump(content_pack_data, f, indent=2, ensure_ascii=False)

            logging.info(f"Successfully downloaded content pack to: {cache_file_path}")
            return cache_file_path

        except httpx.RequestError as e:
            logging.error(f"Network error downloading content pack: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(
                f"HTTP error downloading content pack: {e.response.status_code}"
            )
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Downloaded content pack is not valid JSON: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error downloading content pack: {e}")
            return None

    def install_remote_content_pack(
        self, pack_filename: str, load_immediately: bool = True
    ) -> bool:
        """
        Download and install a remote content pack.

        Args:
            pack_filename: Filename of the content pack to install
            load_immediately: If True, load the pack after installation

        Returns:
            True if installed successfully, False otherwise
        """
        # Download the pack
        downloaded_path = self.download_remote_content_pack(pack_filename)
        if not downloaded_path:
            return False

        # Copy to local content packs directory
        local_path = self.content_packs_dir / pack_filename

        try:
            # Ensure local content packs directory exists
            self.content_packs_dir.mkdir(parents=True, exist_ok=True)

            # Copy from cache to local directory
            with open(downloaded_path, "r", encoding="utf-8") as src:
                content = src.read()

            with open(local_path, "w", encoding="utf-8") as dst:
                dst.write(content)

            logging.info(f"Installed content pack to: {local_path}")

            # Load immediately if requested
            if load_immediately:
                success = self.load_content_pack(local_path)
                if success:
                    logging.info(
                        f"Successfully installed and loaded content pack: {pack_filename}"
                    )
                else:
                    logging.warning(
                        f"Installed content pack but failed to load: {pack_filename}"
                    )
                return success
            else:
                logging.info(f"Successfully installed content pack: {pack_filename}")
                return True

        except Exception as e:
            logging.error(f"Error installing content pack {pack_filename}: {e}")
            return False

    def get_remote_content_pack_info(
        self, pack_filename: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a remote content pack.

        Args:
            pack_filename: Filename of the content pack

        Returns:
            Content pack information or None if not found
        """
        manifest = self.fetch_remote_manifest()
        if not manifest:
            return None

        for pack in manifest.get("content_packs", []):
            if pack.get("filename") == pack_filename:
                pack["source"] = "remote"
                pack["download_url"] = urljoin(
                    self.remote_repo_url,
                    f"content-packs/{pack.get('relative_path', pack_filename)}",
                )
                return pack

        return None

    def search_remote_content_packs(
        self, query: str = "", category: str = "", tags: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search compatible remote content packs by query, category, or tags.

        Args:
            query: Search query to match against name, summary, or description
            category: Filter by category
            tags: Filter by tags (must contain all specified tags)

        Returns:
            List of matching compatible content packs
        """
        # list_remote_content_packs already filters for compatibility
        all_compatible_packs = self.list_remote_content_packs()
        filtered_packs = []

        for pack in all_compatible_packs:
            # Category filter
            if category and pack.get("category", "").lower() != category.lower():
                continue

            # Tags filter
            if tags:
                pack_tags = [tag.lower() for tag in pack.get("tags", [])]
                if not all(tag.lower() in pack_tags for tag in tags):
                    continue

            # Query filter (search in name, summary, description)
            if query:
                query_lower = query.lower()
                searchable_text = " ".join(
                    [
                        pack.get("name", ""),
                        pack.get("summary", ""),
                        pack.get("detailed_description", ""),
                    ]
                ).lower()

                if query_lower not in searchable_text:
                    continue

            filtered_packs.append(pack)

        return filtered_packs

    def clear_remote_cache(self) -> bool:
        """
        Clear the remote content pack cache.

        Returns:
            True if cleared successfully
        """
        try:
            # Clear manifest cache
            self._remote_manifest = None
            self._manifest_cache_time = None

            # Clear cached files
            if self.remote_cache_dir.exists():
                for cache_file in self.remote_cache_dir.glob("*.json"):
                    cache_file.unlink()
                logging.info("Remote cache cleared successfully")

            return True
        except Exception as e:
            logging.error(f"Error clearing remote cache: {e}")
            return False

    def get_remote_repository_info(self) -> Dict[str, Any]:
        """
        Get information about the remote repository.

        Returns:
            Repository information including statistics
        """
        manifest = self.fetch_remote_manifest()
        if not manifest:
            return {"status": "unavailable", "error": "Could not fetch remote manifest"}

        return {
            "status": "available",
            "repository_url": manifest.get("repository_url", ""),
            "manifest_version": manifest.get("manifest_version", ""),
            "generated_at": manifest.get("generated_at", ""),
            "statistics": manifest.get("statistics", {}),
            "cache_status": {
                "cached": self._remote_manifest is not None,
                "cache_time": self._manifest_cache_time,
                "cache_age_seconds": (
                    time.time() - self._manifest_cache_time
                    if self._manifest_cache_time
                    else None
                ),
            },
        }
