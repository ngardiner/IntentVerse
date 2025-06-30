import pytest
from fastapi import HTTPException
from app.state_manager import StateManager
from app.modules.filesystem.tool import FileSystemTool


@pytest.fixture
def filesystem_tool() -> FileSystemTool:
    """Provides a clean FileSystemTool instance for each test."""
    state_manager = StateManager()
    return FileSystemTool(state_manager)


class TestFileSystemInitialization:
    """Tests for filesystem tool initialization."""

    def test_initialization_creates_root_directory(self, filesystem_tool):
        """Tests that initialization creates a proper root directory structure."""
        fs_state = filesystem_tool.state_manager.get("filesystem")
        assert fs_state is not None
        assert fs_state["type"] == "directory"
        assert fs_state["name"] == "/"
        assert fs_state["children"] == []


class TestDirectoryOperations:
    """Tests for directory-related operations."""

    def test_list_files_root_directory(self, filesystem_tool):
        """Tests listing files in the root directory when empty."""
        result = filesystem_tool.list_files("/")
        assert result == []

    def test_list_files_with_content(self, filesystem_tool):
        """Tests listing files when directory has content."""
        # Create some files and directories
        filesystem_tool.write_file("/file1.txt", "content1")
        filesystem_tool.write_file("/subdir/file2.txt", "content2")

        result = filesystem_tool.list_files("/")
        assert len(result) == 2

        # Check file entry
        file_entry = next(item for item in result if item["name"] == "file1.txt")
        assert file_entry["type"] == "file"
        assert file_entry["size_bytes"] == len("content1")

        # Check directory entry
        dir_entry = next(item for item in result if item["name"] == "subdir")
        assert dir_entry["type"] == "directory"
        assert dir_entry["size_bytes"] == 0

    def test_list_files_subdirectory(self, filesystem_tool):
        """Tests listing files in a subdirectory."""
        filesystem_tool.write_file("/subdir/file1.txt", "content1")
        filesystem_tool.write_file("/subdir/file2.txt", "content2")

        result = filesystem_tool.list_files("/subdir")
        assert len(result) == 2
        assert all(item["type"] == "file" for item in result)

    def test_list_files_nonexistent_directory(self, filesystem_tool):
        """Tests listing files in a non-existent directory."""
        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.list_files("/nonexistent")
        assert exc_info.value.status_code == 404
        assert "Directory not found" in exc_info.value.detail

    def test_list_files_on_file_path(self, filesystem_tool):
        """Tests listing files on a file path (should fail)."""
        filesystem_tool.write_file("/test.txt", "content")

        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.list_files("/test.txt")
        assert exc_info.value.status_code == 404
        assert "Directory not found" in exc_info.value.detail


class TestFileOperations:
    """Tests for file-related operations."""

    def test_write_and_read_simple_file(self, filesystem_tool):
        """Tests basic file write and read operations."""
        path = "/test.txt"
        content = "Hello, World!"

        write_result = filesystem_tool.write_file(path, content)
        assert "Successfully wrote to file" in write_result

        read_content = filesystem_tool.read_file(path)
        assert read_content == content

    def test_write_file_with_nested_directories(self, filesystem_tool):
        """Tests writing files that require creating nested directories."""
        path = "/deep/nested/directory/file.txt"
        content = "Deep content"

        filesystem_tool.write_file(path, content)
        read_content = filesystem_tool.read_file(path)
        assert read_content == content

        # Verify directory structure was created
        deep_files = filesystem_tool.list_files("/deep")
        assert len(deep_files) == 1
        assert deep_files[0]["name"] == "nested"
        assert deep_files[0]["type"] == "directory"

    def test_overwrite_existing_file(self, filesystem_tool):
        """Tests overwriting an existing file."""
        path = "/overwrite.txt"
        original_content = "Original content"
        new_content = "New content"

        filesystem_tool.write_file(path, original_content)
        filesystem_tool.write_file(path, new_content)

        read_content = filesystem_tool.read_file(path)
        assert read_content == new_content

    def test_write_empty_file(self, filesystem_tool):
        """Tests writing an empty file."""
        path = "/empty.txt"
        content = ""

        filesystem_tool.write_file(path, content)
        read_content = filesystem_tool.read_file(path)
        assert read_content == ""

    def test_write_large_file(self, filesystem_tool):
        """Tests writing a large file."""
        path = "/large.txt"
        content = "A" * 10000  # 10KB of 'A's

        filesystem_tool.write_file(path, content)
        read_content = filesystem_tool.read_file(path)
        assert read_content == content
        assert len(read_content) == 10000

    def test_read_nonexistent_file(self, filesystem_tool):
        """Tests reading a non-existent file."""
        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.read_file("/nonexistent.txt")
        assert exc_info.value.status_code == 404
        assert "File not found" in exc_info.value.detail

    def test_read_directory_as_file(self, filesystem_tool):
        """Tests attempting to read a directory as a file."""
        filesystem_tool.write_file("/subdir/file.txt", "content")

        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.read_file("/subdir")
        assert exc_info.value.status_code == 404
        assert "File not found" in exc_info.value.detail


class TestFilePathValidation:
    """Tests for file path validation and edge cases."""

    def test_write_file_invalid_empty_path(self, filesystem_tool):
        """Tests writing to an empty path."""
        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.write_file("", "content")
        assert exc_info.value.status_code == 400
        assert "Path must be absolute and not empty" in exc_info.value.detail

    def test_write_file_root_path(self, filesystem_tool):
        """Tests writing to root path (should fail)."""
        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.write_file("/", "content")
        assert exc_info.value.status_code == 400
        assert "Cannot write to the root directory itself" in exc_info.value.detail

    def test_write_file_over_directory(self, filesystem_tool):
        """Tests writing a file over an existing directory."""
        # Create a directory first
        filesystem_tool.write_file("/testdir/file.txt", "content")

        # Try to write a file with the same name as the directory
        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.write_file("/testdir", "content")
        assert exc_info.value.status_code == 400
        assert "A directory already exists at path" in exc_info.value.detail

    def test_create_file_in_file_path(self, filesystem_tool):
        """Tests creating a file where a parent component is a file."""
        filesystem_tool.write_file("/file.txt", "content")

        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.write_file("/file.txt/nested.txt", "content")
        assert exc_info.value.status_code == 400
        assert "is a file, not a directory" in exc_info.value.detail


class TestFileDeletion:
    """Tests for file deletion operations."""

    def test_delete_existing_file(self, filesystem_tool):
        """Tests deleting an existing file."""
        path = "/delete_me.txt"
        filesystem_tool.write_file(path, "content")

        result = filesystem_tool.delete_file(path)
        assert "Successfully deleted file" in result

        # Verify file is gone
        with pytest.raises(HTTPException):
            filesystem_tool.read_file(path)

    def test_delete_nonexistent_file(self, filesystem_tool):
        """Tests deleting a non-existent file."""
        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.delete_file("/nonexistent.txt")
        assert exc_info.value.status_code == 404
        assert "File not found" in exc_info.value.detail

    def test_delete_directory_as_file(self, filesystem_tool):
        """Tests attempting to delete a directory using delete_file."""
        filesystem_tool.write_file("/testdir/file.txt", "content")

        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.delete_file("/testdir")
        assert exc_info.value.status_code == 400
        assert "Path is a directory, not a file" in exc_info.value.detail

    def test_delete_root_directory(self, filesystem_tool):
        """Tests attempting to delete the root directory."""
        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool.delete_file("/")
        assert exc_info.value.status_code == 500
        assert "Cannot delete root directory" in exc_info.value.detail

    def test_delete_file_from_subdirectory(self, filesystem_tool):
        """Tests deleting a file from a subdirectory."""
        filesystem_tool.write_file("/subdir/file1.txt", "content1")
        filesystem_tool.write_file("/subdir/file2.txt", "content2")

        filesystem_tool.delete_file("/subdir/file1.txt")

        # Verify only file1 is deleted
        with pytest.raises(HTTPException):
            filesystem_tool.read_file("/subdir/file1.txt")

        # Verify file2 still exists
        content = filesystem_tool.read_file("/subdir/file2.txt")
        assert content == "content2"

        # Verify directory structure
        files = filesystem_tool.list_files("/subdir")
        assert len(files) == 1
        assert files[0]["name"] == "file2.txt"


class TestComplexScenarios:
    """Tests for complex filesystem scenarios."""

    def test_multiple_nested_operations(self, filesystem_tool):
        """Tests multiple operations on nested directory structure."""
        # Create a complex directory structure
        files_to_create = [
            "/project/src/main.py",
            "/project/src/utils/helper.py",
            "/project/tests/test_main.py",
            "/project/README.md",
            "/project/docs/api.md",
        ]

        for file_path in files_to_create:
            filesystem_tool.write_file(file_path, f"Content of {file_path}")

        # Verify all files exist
        for file_path in files_to_create:
            content = filesystem_tool.read_file(file_path)
            assert content == f"Content of {file_path}"

        # Test directory listings
        project_files = filesystem_tool.list_files("/project")
        assert len(project_files) == 4  # src, tests, README.md, docs

        src_files = filesystem_tool.list_files("/project/src")
        assert len(src_files) == 2  # main.py, utils

        utils_files = filesystem_tool.list_files("/project/src/utils")
        assert len(utils_files) == 1  # helper.py

    def test_file_operations_with_special_characters(self, filesystem_tool):
        """Tests file operations with special characters in names and content."""
        special_filename = "/special-file_name.txt"
        special_content = "Content with special chars: !@#$%^&*()[]{}|;:,.<>?"

        filesystem_tool.write_file(special_filename, special_content)
        read_content = filesystem_tool.read_file(special_filename)
        assert read_content == special_content

    def test_unicode_content(self, filesystem_tool):
        """Tests handling of Unicode content."""
        unicode_content = "Hello 世界! 🌍 Café résumé naïve"
        filesystem_tool.write_file("/unicode.txt", unicode_content)

        read_content = filesystem_tool.read_file("/unicode.txt")
        assert read_content == unicode_content

    def test_state_persistence_across_operations(self, filesystem_tool):
        """Tests that filesystem state persists correctly across operations."""
        # Create initial structure
        filesystem_tool.write_file("/persistent/file1.txt", "content1")
        filesystem_tool.write_file("/persistent/file2.txt", "content2")

        # Perform various operations
        filesystem_tool.delete_file("/persistent/file1.txt")
        filesystem_tool.write_file("/persistent/file3.txt", "content3")
        filesystem_tool.write_file("/persistent/file2.txt", "updated content2")

        # Verify final state
        files = filesystem_tool.list_files("/persistent")
        assert len(files) == 2

        file_names = [f["name"] for f in files]
        assert "file2.txt" in file_names
        assert "file3.txt" in file_names
        assert "file1.txt" not in file_names

        # Verify content
        assert filesystem_tool.read_file("/persistent/file2.txt") == "updated content2"
        assert filesystem_tool.read_file("/persistent/file3.txt") == "content3"


class TestHelperMethods:
    """Tests for internal helper methods."""

    def test_find_node_and_parent_root(self, filesystem_tool):
        """Tests _find_node_and_parent for root directory."""
        node, parent = filesystem_tool._find_node_and_parent("/")
        assert node is not None
        assert node["type"] == "directory"
        assert node["name"] == "/"
        assert parent is None

    def test_find_node_and_parent_existing_file(self, filesystem_tool):
        """Tests _find_node_and_parent for an existing file."""
        filesystem_tool.write_file("/test.txt", "content")

        node, parent = filesystem_tool._find_node_and_parent("/test.txt")
        assert node is not None
        assert node["type"] == "file"
        assert node["name"] == "test.txt"
        assert parent is not None
        assert parent["type"] == "directory"

    def test_find_node_and_parent_nonexistent(self, filesystem_tool):
        """Tests _find_node_and_parent for non-existent path."""
        node, parent = filesystem_tool._find_node_and_parent("/nonexistent.txt")
        assert node is None
        assert parent is not None  # Should return root as potential parent

    def test_create_parent_dirs_nested(self, filesystem_tool):
        """Tests _create_parent_dirs for nested directory creation."""
        parent_node = filesystem_tool._create_parent_dirs("/deep/nested/file.txt")

        assert parent_node["type"] == "directory"
        assert parent_node["name"] == "nested"

        # Verify the full structure was created
        deep_files = filesystem_tool.list_files("/deep")
        assert len(deep_files) == 1
        assert deep_files[0]["name"] == "nested"
        assert deep_files[0]["type"] == "directory"

    def test_create_parent_dirs_file_in_path(self, filesystem_tool):
        """Tests _create_parent_dirs when a file exists in the path."""
        filesystem_tool.write_file("/file.txt", "content")

        with pytest.raises(HTTPException) as exc_info:
            filesystem_tool._create_parent_dirs("/file.txt/nested/file.txt")
        assert exc_info.value.status_code == 400
        assert "is a file, not a directory" in exc_info.value.detail
