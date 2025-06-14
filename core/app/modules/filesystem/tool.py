from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException

class FileSystemTool:
    """
    Implements the logic for a fully functional, in-memory file system.
    This class interacts with the global state managed by the StateManager.
    """

    def __init__(self, state_manager: Any):
        self.state_manager = state_manager
        if 'filesystem' not in self.state_manager.get_full_state():
            root = {'type': 'directory', 'name': '/', 'children': []}
            self.state_manager.set('filesystem', root)

    def _find_node_and_parent(self, path: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        """A helper to find an existing node and its parent given a path."""
        root = self.state_manager.get('filesystem')
        if path == '/':
            return root, None

        parts = [part for part in path.split('/') if part]
        current_node = root
        parent_node = None

        for part in parts:
            if current_node.get('type') != 'directory':
                return None, None

            found_child = None
            for child in current_node.get('children', []):
                if child.get('name') == part:
                    parent_node = current_node
                    current_node = child
                    found_child = True
                    break

            if not found_child:
                return None, parent_node if part == parts[-1] else None

        return current_node, parent_node

    def _create_parent_dirs(self, path: str) -> Dict:
        """Helper to create all necessary parent directories for a given path."""
        root = self.state_manager.get('filesystem')
        parts = [part for part in path.split('/') if part]

        current_node = root
        # Iterate through all parts except the last one (which is the filename)
        for part in parts[:-1]:
            if current_node.get('type') != 'directory':
                raise HTTPException(status_code=400, detail=f"A part of the path '{part}' is a file, not a directory.")

            found_child = None
            for child in current_node.get('children', []):
                if child.get('name') == part:
                    current_node = child
                    found_child = True
                    break

            if not found_child:
                new_dir = {'type': 'directory', 'name': part, 'children': []}
                current_node.get('children', []).append(new_dir)
                current_node = new_dir

        return current_node

    def list_files(self, path: str = '/') -> List[Dict[str, Any]]:
        """Lists files and directories at a given path."""
        node, _ = self._find_node_and_parent(path)
        if not node or node.get('type') != 'directory':
            raise HTTPException(status_code=404, detail=f"Directory not found: {path}")

        return [
            {"name": item.get("name"), "type": item.get("type"), "size_bytes": len(item.get("content", ""))}
            for item in node.get('children', [])
        ]

    def read_file(self, path: str) -> str:
        """Reads the content of a specified file."""
        node, _ = self._find_node_and_parent(path)
        if not node or node.get('type') != 'file':
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        return node.get('content', '')

    def write_file(self, path: str, content: str) -> str:
        """Writes content to a specified file, creating directories as needed."""
        if not path or path == '/':
            raise HTTPException(status_code=400, detail="Invalid file path.")

        parent_node = self._create_parent_dirs(path)
        file_name = path.split('/')[-1]

        # Check if file already exists in the parent directory
        existing_file = None
        for child in parent_node.get('children', []):
            if child.get('name') == file_name:
                existing_file = child
                break

        if existing_file:
            if existing_file.get('type') == 'directory':
                raise HTTPException(status_code=400, detail=f"Cannot write to a directory: {path}")
            existing_file['content'] = content
        else:
            new_file = {
                "type": "file",
                "name": file_name,
                "content": content
            }
            parent_node.get('children', []).append(new_file)

        self.state_manager.set('filesystem', self.state_manager.get('filesystem'))
        return f"Successfully wrote to file: {path}"

    def delete_file(self, path: str) -> str:
        """Deletes a specified file."""
        node, parent = self._find_node_and_parent(path)

        if not node:
            raise HTTPException(status_code=404, detail=f"File not found: {path}")
        if not parent:
            raise HTTPException(status_code=500, detail="Cannot delete root directory.")
        if node.get('type') != 'file':
            raise HTTPException(status_code=400, detail="Path is a directory, not a file.")

        parent['children'] = [child for child in parent['children'] if child['name'] != node['name']]

        self.state_manager.set('filesystem', self.state_manager.get('filesystem'))
        return f"Successfully deleted file: {path}"
