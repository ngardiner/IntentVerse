"""
Unit tests for the ContentPackManager class.

These tests use mocks and a temporary file system to test the logic of the
ContentPackManager in isolation from the actual modules and file system.
"""

import pytest
import json
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import httpx
import respx
from urllib.parse import urljoin

from app.content_pack_manager import ContentPackManager
from app.state_manager import StateManager
from app.module_loader import ModuleLoader


@pytest.fixture
def state_manager():
    """Provides a mock StateManager."""
    return Mock(spec=StateManager)


@pytest.fixture
def module_loader():
    """Provides a mock ModuleLoader with a mock DatabaseTool."""
    mock_loader = Mock(spec=ModuleLoader)
    # The database tool is a dependency for loading/exporting content packs
    mock_db_tool = Mock()
    mock_db_tool.load_content_pack_database.return_value = None
    mock_db_tool.export_database_content.return_value = ["-- MOCK SQL EXPORT"]
    mock_loader.get_tool.return_value = mock_db_tool
    return mock_loader


@pytest.fixture
def temp_content_packs_dir():
    """Creates a temporary directory to act as the content_packs folder."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def content_pack_manager(state_manager, module_loader, temp_content_packs_dir):
    """Provides a ContentPackManager instance initialized with mocks and a temp directory."""
    manager = ContentPackManager(state_manager, module_loader)
    # Override the default path to use our temporary directory
    manager.content_packs_dir = temp_content_packs_dir
    return manager


class TestLocalContentPacks:
    """Tests for loading, exporting, and managing local content packs."""

    def test_load_content_pack_success(
        self, content_pack_manager, state_manager, module_loader
    ):
        """Tests that a valid content pack is loaded correctly."""
        # ARRANGE: Create a valid content pack file
        pack_data = {
            "metadata": {"name": "Test Pack"},
            "database": ["CREATE TABLE test (id INT);"],
            "state": {"filesystem": {"type": "directory"}},
        }
        pack_path = content_pack_manager.content_packs_dir / "valid_pack.json"
        pack_path.write_text(json.dumps(pack_data))

        # ACT: Load the content pack
        success = content_pack_manager.load_content_pack(pack_path)

        # ASSERT: Check that loading was successful and dependencies were called
        assert success is True
        # Check that the database tool was called with the SQL
        db_tool = module_loader.get_tool("database")
        db_tool.load_content_pack_database.assert_called_once_with(
            pack_data["database"]
        )
        # Check that the state manager was called with the state data
        state_manager.set.assert_called_once_with(
            "filesystem", pack_data["state"]["filesystem"]
        )
        # Check that the loaded pack is tracked
        assert len(content_pack_manager.loaded_packs) == 1
        assert content_pack_manager.loaded_packs[0]["metadata"]["name"] == "Test Pack"

    def test_load_nonexistent_pack_fails(self, content_pack_manager):
        """Tests that trying to load a non-existent pack fails gracefully."""
        success = content_pack_manager.load_content_pack_by_filename("nonexistent.json")
        assert success is False

    def test_load_invalid_json_fails(self, content_pack_manager):
        """Tests that loading a file with invalid JSON fails."""
        pack_path = content_pack_manager.content_packs_dir / "invalid.json"
        pack_path.write_text("{ not valid json }")

        success = content_pack_manager.load_content_pack(pack_path)
        assert success is False

    def test_export_content_pack(
        self, content_pack_manager, state_manager, module_loader
    ):
        """Tests that exporting the current state creates a valid content pack."""
        # ARRANGE: Set up some mock state to be exported
        state_manager.get_full_state.return_value = {
            "filesystem": {"name": "/", "type": "directory"},
            "database": {},  # This should be ignored in the state section
        }

        output_path = content_pack_manager.content_packs_dir / "exported.json"
        metadata = {"name": "Exported Test"}

        # ACT: Export the content pack
        success = content_pack_manager.export_content_pack(output_path, metadata)

        # ASSERT: Check that the export was successful and the file is correct
        assert success is True
        assert output_path.exists()

        # Verify the content of the exported file
        with open(output_path, "r") as f:
            exported_data = json.load(f)

        assert exported_data["metadata"]["name"] == "Exported Test"
        # Check that the mock database export was included
        assert exported_data["database"] == ["-- MOCK SQL EXPORT"]
        # Check that the state was correctly exported
        assert "filesystem" in exported_data["state"]
        # Check that the 'database' key was excluded from the state section
        assert "database" not in exported_data["state"]

    def test_list_available_content_packs(self, content_pack_manager):
        """Tests listing available content packs from the directory."""
        # ARRANGE: Create some dummy pack files
        pack1_data = {"metadata": {"name": "Pack 1"}}
        (content_pack_manager.content_packs_dir / "pack1.json").write_text(
            json.dumps(pack1_data)
        )
        pack2_data = {"metadata": {"name": "Pack 2"}}
        (content_pack_manager.content_packs_dir / "pack2.json").write_text(
            json.dumps(pack2_data)
        )
        # Create a non-json file that should be ignored
        (content_pack_manager.content_packs_dir / "notes.txt").write_text("ignore me")

        # ACT: List the packs
        available_packs = content_pack_manager.list_available_content_packs()

        # ASSERT: Check that the correct packs are listed
        assert len(available_packs) == 2
        pack_names = sorted([p["metadata"]["name"] for p in available_packs])
        assert pack_names == ["Pack 1", "Pack 2"]


class TestRemoteContentPacks:
    """Tests for interacting with remote content pack repositories."""

    @respx.mock
    def test_fetch_remote_manifest_success(self, content_pack_manager):
        """Tests successfully fetching and parsing the remote manifest."""
        # ARRANGE: Mock the HTTP GET request to the manifest URL
        mock_manifest = {
            "manifest_version": "1.0",
            "content_packs": [{"name": "Remote Pack"}],
        }
        respx.get(content_pack_manager.manifest_url).mock(
            return_value=httpx.Response(200, json=mock_manifest)
        )

        # ACT: Fetch the manifest
        manifest = content_pack_manager.fetch_remote_manifest()

        # ASSERT: Check that the manifest was fetched and parsed correctly
        assert manifest is not None
        assert manifest["manifest_version"] == "1.0"
        assert len(manifest["content_packs"]) == 1
        assert manifest["content_packs"][0]["name"] == "Remote Pack"

    @respx.mock
    def test_fetch_remote_manifest_caching(self, content_pack_manager):
        """Tests that the remote manifest is cached to avoid repeated requests."""
        # ARRANGE: Mock the manifest URL
        route = respx.get(content_pack_manager.manifest_url).mock(
            return_value=httpx.Response(200, json={})
        )

        # ACT: Fetch twice
        content_pack_manager.fetch_remote_manifest()
        content_pack_manager.fetch_remote_manifest()

        # ASSERT: The HTTP request should only have been made once
        assert route.call_count == 1

        # ACT: Force a refresh
        content_pack_manager.fetch_remote_manifest(force_refresh=True)

        # ASSERT: The request count should now be 2
        assert route.call_count == 2

    @respx.mock
    def test_download_remote_pack_success(self, content_pack_manager):
        """Tests downloading a remote pack to the local cache."""
        # ARRANGE: Mock both the manifest and the specific pack download URL
        pack_filename = "cool_pack.json"
        pack_content = {"metadata": {"name": "Cool Pack"}}
        mock_manifest = {"content_packs": [{"filename": pack_filename}]}

        respx.get(content_pack_manager.manifest_url).mock(
            return_value=httpx.Response(200, json=mock_manifest)
        )
        # Construct the download URL exactly as the application does to ensure the mock matches.
        download_url = urljoin(
            content_pack_manager.remote_repo_url, f"content-packs/{pack_filename}"
        )
        respx.get(download_url).mock(
            return_value=httpx.Response(200, json=pack_content)
        )

        # ACT: Download the pack
        cache_path = content_pack_manager.download_remote_content_pack(pack_filename)

        # ASSERT: Check that the file was created in the cache with the correct content
        assert cache_path is not None
        assert cache_path.exists()
        assert cache_path.name == pack_filename
        with open(cache_path, "r") as f:
            data = json.load(f)
        assert data["metadata"]["name"] == "Cool Pack"
