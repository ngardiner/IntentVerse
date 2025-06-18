import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx
import tempfile
from urllib.parse import urljoin
import time
from .config import Config

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
    
    def load_content_pack(self, pack_path: Path) -> bool:
        """
        Load a content pack from a JSON file.
        
        Args:
            pack_path: Path to the content pack JSON file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            with open(pack_path, 'r', encoding='utf-8') as f:
                content_pack = json.load(f)
            
            # Validate content pack structure
            if not self._validate_content_pack(content_pack):
                logging.error(f"Invalid content pack structure: {pack_path}")
                return False
            
            # Load database content
            if "database" in content_pack and content_pack["database"]:
                database_tool = self.module_loader.get_tool("database")
                if database_tool:
                    database_tool.load_content_pack_database(content_pack["database"])
                    logging.info(f"Loaded database content from {pack_path.name}")
            
            # Load state content (merge with existing state)
            if "state" in content_pack and content_pack["state"]:
                self._merge_state_content(content_pack["state"])
                logging.info(f"Loaded state content from {pack_path.name}")
            
            # Store metadata for tracking
            pack_info = {
                "path": str(pack_path),
                "metadata": content_pack.get("metadata", {}),
                "loaded_at": datetime.now().isoformat()
            }
            self.loaded_packs.append(pack_info)
            
            logging.info(f"Successfully loaded content pack: {pack_path.name}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading content pack {pack_path}: {e}")
            return False
    
    def export_content_pack(self, output_path: Path, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Export current system state as a content pack.
        
        Args:
            output_path: Path where to save the content pack
            metadata: Optional metadata to include
            
        Returns:
            True if exported successfully, False otherwise
        """
        try:
            content_pack = {
                "metadata": metadata or self._generate_default_metadata(),
                "database": [],
                "prompts": [],
                "state": {}
            }
            
            # Export database content
            database_tool = self.module_loader.get_tool("database")
            if database_tool:
                content_pack["database"] = database_tool.export_database_content()
            
            # Export state content (exclude database module)
            full_state = self.state_manager.get_full_state()
            for module_name, module_state in full_state.items():
                if module_name != "database":  # Database is handled separately
                    content_pack["state"][module_name] = module_state
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(content_pack, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Content pack exported to: {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Error exporting content pack to {output_path}: {e}")
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
                with open(pack_file, 'r', encoding='utf-8') as f:
                    content_pack = json.load(f)
                
                pack_info = {
                    "filename": pack_file.name,
                    "path": str(pack_file),
                    "metadata": content_pack.get("metadata", {}),
                    "has_database": bool(content_pack.get("database")),
                    "has_state": bool(content_pack.get("state")),
                    "has_prompts": bool(content_pack.get("prompts"))
                }
                packs.append(pack_info)
                
            except Exception as e:
                logging.error(f"Error reading content pack {pack_file}: {e}")
        
        return packs
    
    def get_loaded_packs_info(self) -> List[Dict[str, Any]]:
        """Get information about currently loaded content packs."""
        return self.loaded_packs.copy()
    
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
                removed_pack = self.loaded_packs.pop(pack_to_remove)
                logging.info(f"Unloaded content pack: {pack_identifier}")
                return True
            else:
                logging.warning(f"Content pack not found in loaded packs: {pack_identifier}")
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
    
    def validate_content_pack_detailed(self, content_pack: Dict[str, Any]) -> Dict[str, Any]:
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
                "prompts_count": 0
            }
        }
        
        # Check that it's a dictionary
        if not isinstance(content_pack, dict):
            validation_result["is_valid"] = False
            validation_result["errors"].append("Content pack must be a JSON object")
            return validation_result
        
        # Check for required top-level keys
        has_content = any(key in content_pack for key in ["database", "state", "prompts"])
        if not has_content:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Content pack must contain at least one of: database, state, or prompts")
        
        # Validate metadata section
        if "metadata" in content_pack:
            validation_result["summary"]["has_metadata"] = True
            metadata = content_pack["metadata"]
            if not isinstance(metadata, dict):
                validation_result["errors"].append("Metadata section must be an object")
            else:
                # Check for recommended metadata fields
                recommended_fields = ["name", "summary", "version"]
                missing_fields = [field for field in recommended_fields if not metadata.get(field)]
                if missing_fields:
                    validation_result["warnings"].append(f"Missing recommended metadata fields: {', '.join(missing_fields)}")
        else:
            validation_result["warnings"].append("No metadata section found - recommended for content pack identification")
        
        # Validate database section
        if "database" in content_pack:
            validation_result["summary"]["has_database"] = True
            database = content_pack["database"]
            if not isinstance(database, list):
                validation_result["errors"].append("Database section must be an array of SQL statements")
            else:
                validation_result["summary"]["database_statements"] = len(database)
                # Validate SQL statements
                for i, statement in enumerate(database):
                    if not isinstance(statement, str):
                        validation_result["errors"].append(f"Database statement {i+1} must be a string")
                    elif not statement.strip():
                        validation_result["warnings"].append(f"Database statement {i+1} is empty")
                    elif not any(statement.strip().upper().startswith(cmd) for cmd in ["CREATE", "INSERT", "UPDATE", "DELETE", "ALTER"]):
                        validation_result["warnings"].append(f"Database statement {i+1} may not be a valid SQL command")
        
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
                unknown_modules = [module for module in state.keys() if module not in known_modules and module != "database"]
                if unknown_modules:
                    validation_result["warnings"].append(f"Unknown state modules (may be custom): {', '.join(unknown_modules)}")
        
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
                        validation_result["errors"].append(f"Prompt {i+1} must be an object")
                    else:
                        required_prompt_fields = ["name", "content"]
                        missing_prompt_fields = [field for field in required_prompt_fields if not prompt.get(field)]
                        if missing_prompt_fields:
                            validation_result["errors"].append(f"Prompt {i+1} missing required fields: {', '.join(missing_prompt_fields)}")
        
        # Set final validation status
        if validation_result["errors"]:
            validation_result["is_valid"] = False
        
        return validation_result
    
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
                "prompts_preview": []
            }
        }
        
        if not pack_path.exists():
            preview_result["validation"] = {
                "is_valid": False,
                "errors": [f"Content pack file '{filename}' not found"],
                "warnings": [],
                "summary": {}
            }
            return preview_result
        
        try:
            with open(pack_path, 'r', encoding='utf-8') as f:
                content_pack = json.load(f)
            
            preview_result["exists"] = True
            preview_result["content_pack"] = content_pack
            
            # Perform detailed validation
            preview_result["validation"] = self.validate_content_pack_detailed(content_pack)
            
            # Generate preview information
            if "metadata" in content_pack:
                preview_result["preview"]["metadata"] = content_pack["metadata"]
            
            if "database" in content_pack and isinstance(content_pack["database"], list):
                # Show first few database statements as preview
                db_statements = content_pack["database"]
                preview_result["preview"]["database_preview"] = db_statements[:5]  # First 5 statements
            
            if "state" in content_pack and isinstance(content_pack["state"], dict):
                # Create a summary of state content
                state_summary = {}
                for module_name, module_state in content_pack["state"].items():
                    if isinstance(module_state, dict):
                        state_summary[module_name] = {
                            "type": type(module_state).__name__,
                            "keys": list(module_state.keys())[:10],  # First 10 keys
                            "total_keys": len(module_state.keys()) if hasattr(module_state, 'keys') else 0
                        }
                    else:
                        state_summary[module_name] = {
                            "type": type(module_state).__name__,
                            "value": str(module_state)[:100] + "..." if len(str(module_state)) > 100 else str(module_state)
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
                            "content_length": len(prompt.get("content", ""))
                        }
                        prompts_preview.append(prompt_summary)
                preview_result["preview"]["prompts_preview"] = prompts_preview
            
        except json.JSONDecodeError as e:
            preview_result["validation"] = {
                "is_valid": False,
                "errors": [f"Invalid JSON format: {str(e)}"],
                "warnings": [],
                "summary": {}
            }
        except Exception as e:
            preview_result["validation"] = {
                "is_valid": False,
                "errors": [f"Error reading content pack: {str(e)}"],
                "warnings": [],
                "summary": {}
            }
        
        return preview_result
    
    def _merge_state_content(self, new_state: Dict[str, Any]):
        """
        Merge new state content with existing state.
        
        Args:
            new_state: State content to merge
        """
        for module_name, module_state in new_state.items():
            if module_name == "database":
                continue  # Skip database - handled separately
            
            # Set the state for each module
            # This will overwrite existing state for the module
            # In the future, we might want more sophisticated merging
            self.state_manager.set(module_name, module_state)
            logging.debug(f"Merged state for module: {module_name}")
    
    def _generate_default_metadata(self) -> Dict[str, Any]:
        """Generate default metadata for content pack export."""
        return {
            "name": "",
            "summary": "",
            "detailed_description": "",
            "date_exported": datetime.now().isoformat(),
            "author_name": "",
            "author_email": "",
            "version": "1.0.0"
        }
    
    def fetch_remote_manifest(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetch the remote content pack manifest from the repository.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            Remote manifest dictionary or None if fetch fails
        """
        current_time = time.time()
        
        # Check if we have cached data and it's still valid
        if (not force_refresh and 
            self._remote_manifest is not None and 
            self._manifest_cache_time is not None and
            (current_time - self._manifest_cache_time) < self._manifest_cache_duration):
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
            
            logging.info(f"Successfully fetched remote manifest with {len(manifest_data.get('content_packs', []))} content packs")
            return manifest_data
            
        except httpx.RequestError as e:
            logging.error(f"Network error fetching remote manifest: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error fetching remote manifest: {e.response.status_code}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in remote manifest: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error fetching remote manifest: {e}")
            return None
    
    def list_remote_content_packs(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        List all available remote content packs.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh data
            
        Returns:
            List of remote content pack information
        """
        manifest = self.fetch_remote_manifest(force_refresh)
        if not manifest:
            logging.warning("Could not fetch remote manifest")
            return []
        
        content_packs = manifest.get("content_packs", [])
        
        # Add remote-specific metadata
        for pack in content_packs:
            pack["source"] = "remote"
            pack["download_url"] = urljoin(
                self.remote_repo_url, 
                f"content-packs/{pack.get('relative_path', pack.get('filename', ''))}"
            )
        
        return content_packs
    
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
            logging.error(f"Content pack '{pack_filename}' not found in remote manifest")
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
            with open(cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(content_pack_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Successfully downloaded content pack to: {cache_file_path}")
            return cache_file_path
            
        except httpx.RequestError as e:
            logging.error(f"Network error downloading content pack: {e}")
            return None
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error downloading content pack: {e.response.status_code}")
            return None
        except json.JSONDecodeError as e:
            logging.error(f"Downloaded content pack is not valid JSON: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error downloading content pack: {e}")
            return None
    
    def install_remote_content_pack(self, pack_filename: str, load_immediately: bool = True) -> bool:
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
            with open(downloaded_path, 'r', encoding='utf-8') as src:
                content = src.read()
            
            with open(local_path, 'w', encoding='utf-8') as dst:
                dst.write(content)
            
            logging.info(f"Installed content pack to: {local_path}")
            
            # Load immediately if requested
            if load_immediately:
                success = self.load_content_pack(local_path)
                if success:
                    logging.info(f"Successfully installed and loaded content pack: {pack_filename}")
                else:
                    logging.warning(f"Installed content pack but failed to load: {pack_filename}")
                return success
            else:
                logging.info(f"Successfully installed content pack: {pack_filename}")
                return True
                
        except Exception as e:
            logging.error(f"Error installing content pack {pack_filename}: {e}")
            return False
    
    def get_remote_content_pack_info(self, pack_filename: str) -> Optional[Dict[str, Any]]:
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
                    f"content-packs/{pack.get('relative_path', pack_filename)}"
                )
                return pack
        
        return None
    
    def search_remote_content_packs(self, query: str = "", category: str = "", tags: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search remote content packs by query, category, or tags.
        
        Args:
            query: Search query to match against name, summary, or description
            category: Filter by category
            tags: Filter by tags (must contain all specified tags)
            
        Returns:
            List of matching content packs
        """
        all_packs = self.list_remote_content_packs()
        filtered_packs = []
        
        for pack in all_packs:
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
                searchable_text = " ".join([
                    pack.get("name", ""),
                    pack.get("summary", ""),
                    pack.get("detailed_description", "")
                ]).lower()
                
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
            return {
                "status": "unavailable",
                "error": "Could not fetch remote manifest"
            }
        
        return {
            "status": "available",
            "repository_url": manifest.get("repository_url", ""),
            "manifest_version": manifest.get("manifest_version", ""),
            "generated_at": manifest.get("generated_at", ""),
            "statistics": manifest.get("statistics", {}),
            "cache_status": {
                "cached": self._remote_manifest is not None,
                "cache_time": self._manifest_cache_time,
                "cache_age_seconds": time.time() - self._manifest_cache_time if self._manifest_cache_time else None
            }
        }