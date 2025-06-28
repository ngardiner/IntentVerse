"""
Updated unit tests for the DatabaseTool that work with the current implementation.
These tests use real DatabaseTool instances instead of mocks.
"""
import pytest
from fastapi import HTTPException

from app.modules.database.tool import DatabaseTool
from app.state_manager import StateManager


class TestDatabaseTool:
    """Test the DatabaseTool class with real instances."""
    
    @pytest.fixture
    def state_manager(self):
        """Create a real state manager for testing."""
        return StateManager()
    
    @pytest.fixture
    def database_tool(self, state_manager):
        """Create a DatabaseTool instance for testing."""
        return DatabaseTool(state_manager)
    
    @pytest.fixture
    def database_tool_with_data(self, state_manager):
        """Create a DatabaseTool instance with sample data for testing."""
        tool = DatabaseTool(state_manager)
        
        # Create tables and insert test data
        tool.execute_sql("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                price REAL NOT NULL
            )
        """)
        
        tool.execute_sql("""
            INSERT INTO products (id, product_name, price) VALUES 
            (1, 'AI Agent Pro', 99.99),
            (2, 'IntentVerse Subscription', 29.99)
        """)
        
        tool.execute_sql("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                email TEXT NOT NULL
            )
        """)
        
        tool.execute_sql("""
            INSERT INTO users (id, username, email) VALUES 
            (1, 'alice', 'alice@example.com'),
            (2, 'bob', 'bob@example.com')
        """)
        
        return tool
    
    def test_initialization_new_state(self, state_manager):
        """Test DatabaseTool initialization when no state exists."""
        # Ensure no database state exists initially
        assert 'database' not in state_manager.get_full_state()
        
        tool = DatabaseTool(state_manager)
        
        # Check that state was initialized
        db_state = state_manager.get('database')
        assert db_state is not None
        
        # Check required keys exist
        required_keys = ['tables', 'last_query', 'last_query_result', 'query_history', 'connection_info']
        for key in required_keys:
            assert key in db_state, f"Missing key: {key}"
        
        # Check initial values
        assert db_state['tables'] == {}
        assert db_state['last_query'] == ""
        assert db_state['last_query_result'] == {"columns": [], "rows": []}
        assert db_state['query_history'] == []
        
        # Check connection info
        conn_info = db_state['connection_info']
        assert conn_info['type'] == 'SQLite'
        assert conn_info['location'] == 'in-memory'
    
    def test_initialization_existing_state(self, state_manager):
        """Test DatabaseTool initialization when state already exists."""
        # Pre-populate state
        existing_state = {
            'tables': {'existing_table': {'columns': [], 'row_count': 0}},
            'last_query': 'SELECT 1',
            'last_query_result': {"columns": [], "rows": []},
            'query_history': [],
            'connection_info': {'type': 'SQLite', 'location': 'in-memory', 'created_at': None}
        }
        state_manager.set('database', existing_state)
        
        tool = DatabaseTool(state_manager)
        
        # State should remain unchanged
        db_state = state_manager.get('database')
        assert db_state['last_query'] == 'SELECT 1'
        assert 'existing_table' in db_state['tables']
    
    def test_query_valid_select_statement(self, database_tool_with_data, state_manager):
        """Test executing a valid SELECT query."""
        query = "SELECT * FROM products ORDER BY id"
        
        result = database_tool_with_data.query(query)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["product_name"] == "AI Agent Pro"
        assert result[0]["price"] == 99.99
        assert result[1]["id"] == 2
        assert result[1]["product_name"] == "IntentVerse Subscription"
        assert result[1]["price"] == 29.99
        
        # Verify state was updated
        db_state = state_manager.get('database')
        assert db_state["last_query"] == query
        
        # Convert result to expected structured format
        expected_result = {
            "columns": list(result[0].keys()) if result else [],
            "rows": [[row.get(col) for col in result[0].keys()] for row in result] if result else []
        }
        assert db_state["last_query_result"] == expected_result
    
    def test_query_case_insensitive_select(self, database_tool_with_data):
        """Test that SELECT queries are case-insensitive."""
        queries = [
            "select * from products ORDER BY id",
            "SELECT * FROM products ORDER BY id",
            "Select * From products ORDER BY id",
            "sElEcT * fRoM products ORDER BY id"
        ]
        
        for query in queries:
            result = database_tool_with_data.query(query)
            assert isinstance(result, list)
            assert len(result) == 2
    
    def test_query_select_with_whitespace(self, database_tool_with_data):
        """Test SELECT queries with leading/trailing whitespace."""
        queries = [
            "  SELECT * FROM products ORDER BY id  ",
            "\t\nSELECT * FROM products ORDER BY id\n\t",
            "   select * from products ORDER BY id   "
        ]
        
        for query in queries:
            result = database_tool_with_data.query(query)
            assert isinstance(result, list)
            assert len(result) == 2
    
    def test_query_non_select_statement_insert(self, database_tool):
        """Test that INSERT statements are rejected by query method."""
        query = "INSERT INTO products (product_name, price) VALUES ('New Product', 50.00)"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "only supports SELECT queries" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_update(self, database_tool):
        """Test that UPDATE statements are rejected by query method."""
        query = "UPDATE products SET price = 100.00 WHERE id = 1"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "only supports SELECT queries" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_delete(self, database_tool):
        """Test that DELETE statements are rejected by query method."""
        query = "DELETE FROM products WHERE id = 1"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "only supports SELECT queries" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_drop(self, database_tool):
        """Test that DROP statements are rejected by query method."""
        query = "DROP TABLE products"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "only supports SELECT queries" in str(exc_info.value.detail)
    
    def test_query_non_select_statement_create(self, database_tool):
        """Test that CREATE statements are rejected by query method."""
        query = "CREATE TABLE new_table (id INT, name VARCHAR(50))"
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "only supports SELECT queries" in str(exc_info.value.detail)
    
    def test_query_empty_string(self, database_tool):
        """Test that empty query strings are rejected."""
        query = ""
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "only supports SELECT queries" in str(exc_info.value.detail)
    
    def test_query_whitespace_only(self, database_tool):
        """Test that whitespace-only query strings are rejected."""
        query = "   \t\n   "
        
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query(query)
        
        assert exc_info.value.status_code == 400
        assert "only supports SELECT queries" in str(exc_info.value.detail)
    
    def test_execute_sql_create_table(self, database_tool):
        """Test creating tables with execute_sql."""
        sql = "CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)"
        
        result = database_tool.execute_sql(sql)
        assert result == []  # CREATE returns empty list
        
        # Verify table was created
        tables = database_tool.list_tables()
        assert "test_table" in tables
    
    def test_execute_sql_insert_data(self, database_tool):
        """Test inserting data with execute_sql."""
        # Create table first
        database_tool.execute_sql("CREATE TABLE test_insert (id INTEGER, value TEXT)")
        
        # Insert data
        result = database_tool.execute_sql("INSERT INTO test_insert VALUES (1, 'test')")
        assert result == []  # INSERT returns empty list
        
        # Verify data was inserted
        data = database_tool.query("SELECT * FROM test_insert")
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["value"] == "test"
    
    def test_execute_sql_with_parameters(self, database_tool):
        """Test execute_sql with parameters."""
        # Create table
        database_tool.execute_sql("CREATE TABLE param_test (id INTEGER, name TEXT)")
        
        # Insert with parameters
        database_tool.execute_sql("INSERT INTO param_test VALUES (?, ?)", (1, "Alice"))
        
        # Verify
        data = database_tool.query("SELECT * FROM param_test")
        assert len(data) == 1
        assert data[0]["name"] == "Alice"
    
    def test_list_tables(self, database_tool_with_data):
        """Test listing available tables."""
        result = database_tool_with_data.list_tables()
        
        assert isinstance(result, list)
        assert "products" in result
        assert "users" in result
        assert len(result) == 2
    
    def test_list_tables_empty_database(self, database_tool):
        """Test listing tables when database is empty."""
        result = database_tool.list_tables()
        
        assert isinstance(result, list)
        assert result == []
    
    def test_create_table_method(self, database_tool):
        """Test the create_table convenience method."""
        columns = [
            {"name": "id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
            {"name": "name", "type": "TEXT", "constraints": "NOT NULL"},
            {"name": "email", "type": "TEXT"}
        ]
        
        result = database_tool.create_table("test_users", columns)
        assert "created successfully" in result
        
        # Verify table exists
        tables = database_tool.list_tables()
        assert "test_users" in tables
        
        # Verify structure
        columns_info = database_tool.describe_table("test_users")
        assert len(columns_info) == 3
        
        # Check column details
        id_col = next(col for col in columns_info if col["name"] == "id")
        assert id_col["primary_key"] == True
        
        name_col = next(col for col in columns_info if col["name"] == "name")
        assert name_col["not_null"] == True
    
    def test_insert_data_method(self, database_tool):
        """Test the insert_data convenience method."""
        # Create table first
        database_tool.execute_sql("CREATE TABLE insert_test (id INTEGER, name TEXT, age INTEGER)")
        
        # Insert data
        data = {"id": 1, "name": "John", "age": 30}
        result = database_tool.insert_data("insert_test", data)
        assert "inserted" in result
        
        # Verify data
        rows = database_tool.query("SELECT * FROM insert_test")
        assert len(rows) == 1
        assert rows[0]["name"] == "John"
        assert rows[0]["age"] == 30
    
    def test_update_data_method(self, database_tool):
        """Test the update_data convenience method."""
        # Setup
        database_tool.execute_sql("CREATE TABLE update_test (id INTEGER, status TEXT)")
        database_tool.execute_sql("INSERT INTO update_test VALUES (1, 'pending')")
        
        # Update
        result = database_tool.update_data("update_test", {"status": "completed"}, "id = ?", (1,))
        assert "updated successfully" in result
        
        # Verify
        rows = database_tool.query("SELECT * FROM update_test WHERE id = 1")
        assert rows[0]["status"] == "completed"
    
    def test_delete_data_method(self, database_tool):
        """Test the delete_data convenience method."""
        # Setup
        database_tool.execute_sql("CREATE TABLE delete_test (id INTEGER, name TEXT)")
        database_tool.execute_sql("INSERT INTO delete_test VALUES (1, 'Alice')")
        database_tool.execute_sql("INSERT INTO delete_test VALUES (2, 'Bob')")
        
        # Delete
        result = database_tool.delete_data("delete_test", "id = ?", (1,))
        assert "deleted" in result
        
        # Verify
        rows = database_tool.query("SELECT * FROM delete_test")
        assert len(rows) == 1
        assert rows[0]["name"] == "Bob"
    
    def test_describe_table(self, database_tool_with_data):
        """Test describing table structure."""
        columns = database_tool_with_data.describe_table("products")
        
        assert len(columns) == 3
        
        # Check id column
        id_col = next(col for col in columns if col["name"] == "id")
        assert id_col["type"] == "INTEGER"
        assert id_col["primary_key"] == True
        
        # Check product_name column
        name_col = next(col for col in columns if col["name"] == "product_name")
        assert name_col["type"] == "TEXT"
        assert name_col["not_null"] == True
        
        # Check price column
        price_col = next(col for col in columns if col["name"] == "price")
        assert price_col["type"] == "REAL"
        assert price_col["not_null"] == True
    
    def test_describe_nonexistent_table(self, database_tool):
        """Test describing a table that doesn't exist."""
        with pytest.raises(HTTPException) as exc_info:
            database_tool.describe_table("nonexistent_table")
        
        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)
    
    def test_load_content_pack_database(self, database_tool, state_manager):
        """Test loading database content from content pack."""
        database_content = [
            "CREATE TABLE content_users (id INTEGER PRIMARY KEY, username TEXT, email TEXT)",
            "INSERT INTO content_users (id, username, email) VALUES (1, 'alice', 'alice@example.com')",
            "INSERT INTO content_users (id, username, email) VALUES (2, 'bob', 'bob@example.com')"
        ]
        
        database_tool.load_content_pack_database(database_content)
        
        # Verify table was created
        tables = database_tool.list_tables()
        assert "content_users" in tables
        
        # Verify data was inserted
        users = database_tool.query("SELECT * FROM content_users ORDER BY id")
        assert len(users) == 2
        assert users[0]["username"] == "alice"
        assert users[1]["username"] == "bob"
        
        # Verify state was updated
        db_state = state_manager.get('database')
        assert "content_users" in db_state["tables"]
        assert db_state["tables"]["content_users"]["row_count"] == 2
    
    def test_export_database_content(self, database_tool_with_data):
        """Test exporting database content for content packs."""
        exported_sql = database_tool_with_data.export_database_content()
        
        assert len(exported_sql) > 0
        
        # Should have CREATE statements
        create_statements = [sql for sql in exported_sql if sql.upper().startswith('CREATE')]
        assert len(create_statements) >= 2  # products and users tables
        
        # Should have INSERT statements
        insert_statements = [sql for sql in exported_sql if sql.upper().startswith('INSERT')]
        assert len(insert_statements) >= 4  # 2 products + 2 users
        
        # Verify we can recreate the database from export
        new_state_manager = StateManager()
        new_db_tool = DatabaseTool(new_state_manager)
        new_db_tool.load_content_pack_database(exported_sql)
        
        # Verify recreated data
        products = new_db_tool.query("SELECT * FROM products ORDER BY id")
        assert len(products) == 2
        assert products[0]["product_name"] == "AI Agent Pro"
    
    def test_query_history_tracking(self, database_tool, state_manager):
        """Test that query history is properly tracked."""
        # Execute some queries
        database_tool.execute_sql("CREATE TABLE history_test (id INTEGER)")
        database_tool.execute_sql("INSERT INTO history_test VALUES (1)")
        database_tool.query("SELECT * FROM history_test")
        
        # Check query history
        history = database_tool.get_query_history()
        assert len(history) >= 3
        
        # Check history entries have required fields
        for entry in history:
            assert "timestamp" in entry
            assert "query" in entry
            assert "result_count" in entry
            assert "query_type" in entry
        
        # Check specific query types
        query_types = [entry["query_type"] for entry in history]
        assert "CREATE" in query_types
        assert "INSERT" in query_types
        assert "SELECT" in query_types
    
    def test_state_updates_correctly(self, database_tool, state_manager):
        """Test that database operations correctly update the state."""
        # Execute operations
        database_tool.execute_sql("CREATE TABLE state_test (id INTEGER, name TEXT)")
        database_tool.execute_sql("INSERT INTO state_test VALUES (1, 'test')")
        result = database_tool.query("SELECT * FROM state_test")
        
        # Check state was updated
        db_state = state_manager.get('database')
        
        # Check last query tracking
        assert db_state["last_query"] == "SELECT * FROM state_test"
        
        # Convert result to expected structured format
        expected_result = {
            "columns": list(result[0].keys()) if result else [],
            "rows": [[row.get(col) for col in result[0].keys()] for row in result] if result else []
        }
        assert db_state["last_query_result"] == expected_result
        
        # Check table info was updated
        assert "state_test" in db_state["tables"]
        table_info = db_state["tables"]["state_test"]
        assert table_info["row_count"] == 1
        assert len(table_info["columns"]) == 2
        
        # Check column details
        columns = table_info["columns"]
        id_col = next(col for col in columns if col["name"] == "id")
        assert id_col["type"] == "INTEGER"
        
        name_col = next(col for col in columns if col["name"] == "name")
        assert name_col["type"] == "TEXT"
    
    def test_multiple_queries_update_state(self, database_tool_with_data, state_manager):
        """Test that multiple queries properly update the state."""
        # First query
        result1 = database_tool_with_data.query("SELECT * FROM products")
        
        # Check state after first query
        db_state = state_manager.get('database')
        expected_result1 = {
            "columns": list(result1[0].keys()) if result1 else [],
            "rows": [[row.get(col) for col in result1[0].keys()] for row in result1] if result1 else []
        }
        assert db_state["last_query_result"] == expected_result1
        
        # Second query
        result2 = database_tool_with_data.query("SELECT id FROM products")
        
        # Check state after second query
        db_state = state_manager.get('database')
        expected_result2 = {
            "columns": list(result2[0].keys()) if result2 else [],
            "rows": [[row.get(col) for col in result2[0].keys()] for row in result2] if result2 else []
        }
        assert db_state["last_query_result"] == expected_result2
        
        # Check query history contains both
        history = database_tool_with_data.get_query_history()
        recent_queries = [entry["query"] for entry in history[-2:]]
        assert "SELECT * FROM products" in recent_queries
        assert "SELECT id FROM products" in recent_queries
    
    def test_error_handling_invalid_sql(self, database_tool):
        """Test error handling for invalid SQL."""
        with pytest.raises(HTTPException) as exc_info:
            database_tool.execute_sql("INVALID SQL STATEMENT")
        
        assert exc_info.value.status_code == 400
        assert "SQL Error" in str(exc_info.value.detail)
    
    def test_error_handling_empty_sql(self, database_tool):
        """Test error handling for empty SQL."""
        with pytest.raises(HTTPException) as exc_info:
            database_tool.execute_sql("")
        
        assert exc_info.value.status_code == 400
        assert "cannot be empty" in str(exc_info.value.detail)
    
    def test_error_handling_missing_table(self, database_tool):
        """Test error handling when querying missing table."""
        with pytest.raises(HTTPException) as exc_info:
            database_tool.query("SELECT * FROM nonexistent_table")
        
        assert exc_info.value.status_code == 400
        assert "SQL Error" in str(exc_info.value.detail)