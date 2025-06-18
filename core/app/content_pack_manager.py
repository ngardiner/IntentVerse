import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

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
    
    def _validate_content_pack(self, content_pack: Dict[str, Any]) -> bool:
        """
        Validate the structure of a content pack.
        
        Args:
            content_pack: The content pack dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check that it's a dictionary
        if not isinstance(content_pack, dict):
            return False
        
        # Check for required top-level keys (at least one of database, state, or prompts)
        has_content = any(key in content_pack for key in ["database", "state", "prompts"])
        if not has_content:
            return False
        
        # Validate database section if present
        if "database" in content_pack:
            if not isinstance(content_pack["database"], list):
                return False
        
        # Validate state section if present
        if "state" in content_pack:
            if not isinstance(content_pack["state"], dict):
                return False
        
        # Validate prompts section if present
        if "prompts" in content_pack:
            if not isinstance(content_pack["prompts"], list):
                return False
        
        return True
    
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