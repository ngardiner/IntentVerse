import pytest
from app.state_manager import StateManager
from app.modules.filesystem.tool import FileSystemTool


def test_write_and_read_file():
    """
    Tests that writing a file and then reading it returns the correct content.
    """
    # ARRANGE: Set up the components for the test
    state_manager = StateManager()
    filesystem_tool = FileSystemTool(state_manager)

    test_path = "/documents/report.txt"
    test_content = "This is a test report."

    # ACT: Perform the actions we want to test
    filesystem_tool.write_file(path=test_path, content=test_content)
    read_content = filesystem_tool.read_file(path=test_path)

    # ASSERT: Verify that the outcome is what we expected
    assert read_content == test_content


def test_list_files():
    """

    Tests that listing files in a directory shows the correct file.
    """
    # ARRANGE
    state_manager = StateManager()
    filesystem_tool = FileSystemTool(state_manager)

    filesystem_tool.write_file(path="/hello.txt", content="world")

    # ACT
    file_list = filesystem_tool.list_files(path="/")

    # ASSERT
    assert len(file_list) == 1
    assert file_list[0]["name"] == "hello.txt"
    assert file_list[0]["type"] == "file"


def test_create_directory():
    """
    Tests that creating a directory works correctly.
    """
    # ARRANGE
    state_manager = StateManager()
    filesystem_tool = FileSystemTool(state_manager)

    test_path = "/test_directory"

    # ACT
    result = filesystem_tool.create_directory(path=test_path)
    file_list = filesystem_tool.list_files(path="/")

    # ASSERT
    assert result == "Successfully created directory: /test_directory"
    assert len(file_list) == 1
    assert file_list[0]["name"] == "test_directory"
    assert file_list[0]["type"] == "directory"


def test_create_nested_directory():
    """
    Tests that creating nested directories works correctly.
    """
    # ARRANGE
    state_manager = StateManager()
    filesystem_tool = FileSystemTool(state_manager)

    test_path = "/parent/child/grandchild"

    # ACT
    result = filesystem_tool.create_directory(path=test_path)
    parent_list = filesystem_tool.list_files(path="/parent")
    child_list = filesystem_tool.list_files(path="/parent/child")

    # ASSERT
    assert result == "Successfully created directory: /parent/child/grandchild"
    assert len(parent_list) == 1
    assert parent_list[0]["name"] == "child"
    assert parent_list[0]["type"] == "directory"
    assert len(child_list) == 1
    assert child_list[0]["name"] == "grandchild"
    assert child_list[0]["type"] == "directory"


def test_delete_empty_directory():
    """
    Tests that deleting an empty directory works correctly.
    """
    # ARRANGE
    state_manager = StateManager()
    filesystem_tool = FileSystemTool(state_manager)

    filesystem_tool.create_directory("/test_dir")

    # ACT
    result = filesystem_tool.delete_directory("/test_dir")
    file_list = filesystem_tool.list_files(path="/")

    # ASSERT
    assert result == "Successfully deleted directory: /test_dir"
    assert len(file_list) == 0


def test_delete_non_empty_directory_fails():
    """
    Tests that deleting a non-empty directory fails with appropriate error.
    """
    # ARRANGE
    state_manager = StateManager()
    filesystem_tool = FileSystemTool(state_manager)

    filesystem_tool.create_directory("/test_dir")
    filesystem_tool.write_file("/test_dir/file.txt", "content")

    # ACT & ASSERT
    with pytest.raises(Exception) as exc_info:
        filesystem_tool.delete_directory("/test_dir")

    assert "Directory is not empty" in str(exc_info.value)


def test_create_directory_already_exists():
    """
    Tests that creating a directory that already exists fails appropriately.
    """
    # ARRANGE
    state_manager = StateManager()
    filesystem_tool = FileSystemTool(state_manager)

    filesystem_tool.create_directory("/test_dir")

    # ACT & ASSERT
    with pytest.raises(Exception) as exc_info:
        filesystem_tool.create_directory("/test_dir")

    assert "Directory already exists" in str(exc_info.value)
