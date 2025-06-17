"""
Unit tests for the DatabaseTool.
"""
import pytest
from unittest.mock import Mock
from fastapi import HTTPException

from core.app.modules.database.tool import DatabaseTool
from core.app.state_manager import StateManager


class TestDatabaseTool:
    """Test the DatabaseTool class."""
    
    @pytest.fixture
    def state_manager(self):
        """Create a mock state manager."""
        mock_sm = Mock(spec=StateManager)
        mock_sm.get_full_state.return_value = {}
        mock_sm.get.return_value = {
            "tables": ["users", "products"],
            "last_query_result": []
        }
        return mock_sm
    
    @pytest.fixture
    def database_tool(self, state_manager):
        """Create a DatabaseTool instance for testing."""
        return DatabaseTool(state_manager)
    
    def test_initialization_new_state(self, state_manager):
        """Test DatabaseTool initialization when no state exists."""
        state_manager.get_full_state.return_value = {}
        
        tool = DatabaseTool(state_manager)
        
        assert tool.state_manager == state_manager
        state_manager.set.assert_called_once_with('database', {
            "tables": ["users", "products"],
            "last_query_result": []
        })
    
    def test_initialization_existing_state(self, state_manager):
        """Test DatabaseTool initialization when state already exists."""
        state_manager.get_full_state.return_value = {'database': {'existing': 'data'}}
        
        tool = DatabaseTool(state_manager)
        
        assert tool.state_manager == state_manager
        # set should not be called when state already exists
        state_manager.set.assert_not_called()
    
    def test_query_valid_select_statement(self, database_tool, state_manager):
        """Test executing a valid SELECT query."""
        query = "SELECT * FROM products"
        
        result = database_tool.query(query)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["product_name"] == "AI Agent Pro"
        assert result[0]["price"] == 99.99
        assert result[1]["id"] == 2
        assert result[1]["product_name"] == "IntentVerse Subscription"
        assert result[1]["price"] == 29.99
        
        # Verify state was updated
        state_manager.set.assert_called()
        call_args = state_manager.set.call_args
        assert call_args[0][0] == 'database'
        assert call_args[0][1]["last_query_result"] == result
    
    def test_query_case_insensitive_select(self, database_tool):
        """Test that SELECT queries are case-insensitive."""
        queries = [
            "select * from products",
            "SELECT * FROM products",
            "Select * From products",
            "sElEcT * fRoM products"
        ]
        
        for query in queries:
            result = database_tool.query(query)
            assert isinstance(result, list)
            assert len(result) == 2
    
    def test_query_select_with_whitespace(self, database_tool):
        """Test SELECT queries with leading/trailing whitespace."""
        queries = [
            "  SELECT * FROM products  ",
            "\t\nSELECT * FROM products\n\t",
            "   select * from products   "
        ]
        
        for query in queries:
            result = database_tool.query(query)
            assert isinstance(result, list)
            assert len(result) == 2
    
    def test_query_non_select_statement_insert(self, database_tool):
        """Test that INSERT statements are rejected."""
        query = "INSERT INTO products (name, price) VALUES ('New Product', 50.00)"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "Only SELECT queries are allowed" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_update(self, database_tool):
        """Test that UPDATE statements are rejected."""
        query = "UPDATE products SET price = 100.00 WHERE id = 1"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "Only SELECT queries are allowed" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_delete(self, database_tool):
        """Test that DELETE statements are rejected."""
        query = "DELETE FROM products WHERE id = 1"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "Only SELECT queries are allowed" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_drop(self, database_tool):
        """Test that DROP statements are rejected."""
        query = "DROP TABLE products"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "Only SELECT queries are allowed" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_create(self, database_tool):
        """Test that CREATE statements are rejected."""
        query = "CREATE TABLE new_table (id INT, name VARCHAR(50))"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "Only SELECT queries are allowed" in str(exc_info.value.detail)
    
    def test_query_empty_string(self, database_tool):
        """Test that empty query strings are rejected."""
        query = ""
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "Only SELECT queries are allowed" in str(exc_info.value.detail)
    
    def test_query_whitespace_only(self, database_tool):
        """Test that whitespace-only query strings are rejected."""
        query = "   \t\n   "
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "Only SELECT queries are allowed" in str(exc_info.value.detail)
    
    def test_list_tables(self, database_tool, state_manager):
        """Test listing available tables."""
        result = database_tool.list_tables()
        
        assert isinstance(result, list)
        assert result == ["users", "products"]
        state_manager.get.assert_called_once_with('database')
    
    def test_list_tables_empty_state(self, database_tool, state_manager):
        """Test listing tables when state has no tables."""
        state_manager.get.return_value = {}
        
        result = database_tool.list_tables()
        
        assert isinstance(result, list)
        assert result == []
    
    def test_list_tables_none_state(self, database_tool, state_manager):
        """Test listing tables when state returns None."""
        state_manager.get.return_value = None
        
        with pytest.raises(AttributeError):
            database_tool.list_tables()
    
    def test_query_updates_state_correctly(self, database_tool, state_manager):
        """Test that query method correctly updates the state."""
        initial_state = {
            "tables": ["users", "products"],
            "last_query_result": []
        }
        state_manager.get.return_value = initial_state
        
        query = "SELECT * FROM products"
        result = database_tool.query(query)
        
        # Verify that set was called with updated state
        state_manager.set.assert_called()
        call_args = state_manager.set.call_args
        assert call_args[0][0] == 'database'
        updated_state = call_args[0][1]
        assert updated_state["tables"] == ["users", "products"]
        assert updated_state["last_query_result"] == result
        assert len(updated_state["last_query_result"]) == 2
    
    def test_multiple_queries_update_state(self, database_tool, state_manager):
        """Test that multiple queries properly update the state."""
        initial_state = {
            "tables": ["users", "products"],
            "last_query_result": []
        }
        state_manager.get.return_value = initial_state
        
        # First query
        result1 = database_tool.query("SELECT * FROM products")
        
        # Update the mock to return the new state for the second query
        updated_state = {
            "tables": ["users", "products"],
            "last_query_result": result1
        }
        state_manager.get.return_value = updated_state
        
        # Second query
        result2 = database_tool.query("SELECT id FROM products")
        
        # Verify both queries were executed and state was updated twice
        assert state_manager.set.call_count == 2
        
        # Check the final state update
        final_call_args = state_manager.set.call_args
        assert final_call_args[0][0] == 'database'
        final_state = final_call_args[0][1]
        assert final_state["last_query_result"] == result2