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
