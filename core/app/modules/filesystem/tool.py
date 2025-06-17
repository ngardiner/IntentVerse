from ..base_tool import BaseTool
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException

class FileSystemTool(BaseTool):
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
    """
    Writes content to a file at the specified path, creating directories if necessary.
    """
    # Get a direct reference to the entire filesystem state
    fs_state = self.state_manager.get('filesystem')
    if not fs_state:
        return "Error: Filesystem state is not initialized."

    parts = [part for part in path.split('/') if part]
    if not parts:
        return "Error: Cannot write to the root directory itself."

    filename = parts.pop()
    current_node = fs_state

    # Traverse the path and create directories if they don't exist
    for part in parts:
        found_node = None
        for child in current_node.get('children', []):
            if child.get('name') == part and child.get('type') == 'directory':
                found_node = child
                break
        
        if not found_node:
            new_dir = {'type': 'directory', 'name': part, 'children': []}
            current_node.get('children', []).append(new_dir)
            current_node = new_dir
        else:
            current_node = found_node

    # Check if a file with the same name already exists and remove it
    children = current_node.get('children', [])
    for i, child in enumerate(children):
        if child.get('name') == filename and child.get('type') == 'file':
            children.pop(i)
            break

    # Add the new file
    new_file = {'type': 'file', 'name': filename, 'content': content}
    children.append(new_file)

    # Explicitly set the modified filesystem state back into the manager
    self.state_manager.set('filesystem', fs_state)
    
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
