from ..base_tool import BaseTool
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException


class FileSystemTool(BaseTool):
    """
    Implements the logic for a fully functional, in-memory file system.
    This class interacts with the global state managed by the StateManager.
    """

    def __init__(self, state_manager: Any):
        super().__init__(state_manager)
        if "filesystem" not in self.state_manager.get_full_state():
            root = {"type": "directory", "name": "/", "children": []}
            self.state_manager.set("filesystem", root)

    def get_ui_schema(self) -> Dict[str, Any]:
        """Returns the UI schema for the filesystem module."""
        from .schema import UI_SCHEMA

        return UI_SCHEMA

    def _find_node_and_parent(self, path: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        """A helper to find an existing node and its parent given a path."""
        root = self.state_manager.get("filesystem")
        if path == "/":
            return root, None

        parts = [part for part in path.split("/") if part]
        current_node = root
        parent_node = None

        for part in parts:
            if current_node.get("type") != "directory":
                return None, None

            found_child = None
            for child in current_node.get("children", []):
                if child.get("name") == part:
                    parent_node = current_node
                    current_node = child
                    found_child = True
                    break

            if not found_child:
                # If this is the last part, the node isn't found, but its parent is current_node
                if part == parts[-1]:
                    return None, current_node
                # Otherwise, an intermediate directory is missing
                return None, None

        return current_node, parent_node

    def _create_parent_dirs(self, path: str) -> Dict:
        """Helper to create all necessary parent directories for a given path."""
        root = self.state_manager.get("filesystem")
        parts = [part for part in path.split("/") if part]

        current_node = root
        # Iterate through all parts except the last one (which is the filename)
        for part in parts[:-1]:
            if current_node.get("type") != "directory":
                raise HTTPException(
                    status_code=400,
                    detail=f"A part of the path '{part}' is a file, not a directory.",
                )

            found_child = None
            for child in current_node.get("children", []):
                if child.get("name") == part:
                    # Check if the found child is a directory
                    if child.get("type") != "directory":
                        raise HTTPException(
                            status_code=400,
                            detail=f"A part of the path '{part}' is a file, not a directory.",
                        )
                    current_node = child
                    found_child = True
                    break

            if not found_child:
                new_dir = {"type": "directory", "name": part, "children": []}
                current_node.get("children", []).append(new_dir)
                current_node = new_dir

        return current_node

    def list_files(self, path: str = "/") -> List[Dict[str, Any]]:
        """Lists files and directories at a given path."""
        node, _ = self._find_node_and_parent(path)
        if not node or node.get("type") != "directory":
            raise HTTPException(status_code=404, detail=f"Directory not found: {path}")

        return [
            {
                "name": item.get("name"),
                "type": item.get("type"),
                "size_bytes": len(item.get("content", "")),
            }
            for item in node.get("children", [])
        ]

    def read_file(self, path: str) -> str:
        """Reads the content of a specified file."""
        node, _ = self._find_node_and_parent(path)
        if not node or node.get("type") != "file":
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        return node.get("content", "")

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a specified file, creating directories as needed."""
        # 1. Perform all validation first.
        if not path or not path.startswith("/"):
            raise HTTPException(
                status_code=400, detail="Path must be absolute and not empty."
            )
        if path.strip() == "/":
            raise HTTPException(
                status_code=400, detail="Cannot write to the root directory itself."
            )

        # 2. Find the target and its parent.
        node, parent = self._find_node_and_parent(path)

        # 3. Handle validation based on what was found.
        if node and node.get("type") == "directory":
            raise HTTPException(
                status_code=400, detail=f"A directory already exists at path: {path}"
            )

        # 4. If parent doesn't exist, create all necessary parent directories
        if not parent:
            try:
                parent = self._create_parent_dirs(path)
            except HTTPException:
                # Re-raise if _create_parent_dirs found an invalid path structure
                raise
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid path: cannot create parent directories for {path}",
                )

        file_name = path.split("/")[-1]

        # 5. Perform the write/overwrite.
        # Remove the old file if it exists.
        parent["children"] = [
            child
            for child in parent.get("children", [])
            if not (child.get("name") == file_name and child.get("type") == "file")
        ]

        # Add the new file.
        new_file = {"type": "file", "name": file_name, "content": content}
        parent["children"].append(new_file)
        self.state_manager.set("filesystem", self.state_manager.get("filesystem"))
        return f"Successfully wrote to file: {path}"

    def delete_file(self, path: str) -> str:
        """Deletes a specified file."""
        node, parent = self._find_node_and_parent(path)

        if not node:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        if not parent:
            raise HTTPException(status_code=500, detail="Cannot delete root directory.")
        if node.get("type") != "file":
            raise HTTPException(
                status_code=400, detail="Path is a directory, not a file."
            )

        parent["children"] = [
            child for child in parent["children"] if child["name"] != node["name"]
        ]

        self.state_manager.set("filesystem", self.state_manager.get("filesystem"))
        return f"Successfully deleted file: {path}"

    def create_directory(self, path: str) -> str:
        """Creates a new directory at the specified path."""
        # 1. Perform all validation first.
        if not path or not path.startswith("/"):
            raise HTTPException(
                status_code=400, detail="Path must be absolute and not empty."
            )
        if path.strip() == "/":
            raise HTTPException(
                status_code=400, detail="Cannot create the root directory."
            )

        # 2. Find the target and its parent.
        node, parent = self._find_node_and_parent(path)

        # 3. Handle validation based on what was found.
        if node:
            if node.get("type") == "directory":
                raise HTTPException(
                    status_code=400, detail=f"Directory already exists at path: {path}"
                )
            else:
                raise HTTPException(
                    status_code=400, detail=f"A file already exists at path: {path}"
                )

        # 4. If parent doesn't exist, create all necessary parent directories
        if not parent:
            try:
                parent = self._create_parent_dirs(path)
            except HTTPException:
                # Re-raise if _create_parent_dirs found an invalid path structure
                raise
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid path: cannot create parent directories for {path}",
                )

        directory_name = path.split("/")[-1]

        # 5. Create the new directory.
        new_directory = {"type": "directory", "name": directory_name, "children": []}
        parent["children"].append(new_directory)
        self.state_manager.set("filesystem", self.state_manager.get("filesystem"))
        return f"Successfully created directory: {path}"

    def delete_directory(self, path: str) -> str:
        """Deletes a specified directory (must be empty)."""
        node, parent = self._find_node_and_parent(path)

        if not node:
            raise HTTPException(status_code=404, detail=f"Directory not found: {path}")
        if not parent:
            raise HTTPException(status_code=500, detail="Cannot delete root directory.")
        if node.get("type") != "directory":
            raise HTTPException(
                status_code=400, detail="Path is a file, not a directory."
            )
        if node.get("children") and len(node.get("children", [])) > 0:
            raise HTTPException(
                status_code=400,
                detail="Directory is not empty. Please delete all contents first.",
            )

        parent["children"] = [
            child for child in parent["children"] if child["name"] != node["name"]
        ]

        self.state_manager.set("filesystem", self.state_manager.get("filesystem"))
        return f"Successfully deleted directory: {path}"
