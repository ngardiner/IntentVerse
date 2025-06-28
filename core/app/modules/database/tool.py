import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import logging
from typing import Any, Dict, List, Optional, Tuple
from ..base_tool import BaseTool
from fastapi import HTTPException

class DatabaseTool(BaseTool):
    """
    Implements a fully functional in-memory SQLite database tool.
    This provides a safe, observable environment for AI agents to interact with databases.
    """
    
    def get_ui_schema(self) -> Dict[str, Any]:
        """Returns the UI schema for the database module."""
        from .schema import UI_SCHEMA
        return UI_SCHEMA

    def __init__(self, state_manager: Any):
        """
        Initializes the DatabaseTool with an in-memory SQLite database.
        """
        super().__init__(state_manager)
        
        # Create in-memory SQLite connection
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.connection.row_factory = sqlite3.Row  # Enable dict-like access to rows
        
        # Initialize state if it doesn't exist
        if 'database' not in self.state_manager.get_full_state():
            self._initialize_database_state()

    def _initialize_database_state(self):
        """Initialize the database state in the state manager."""
        import datetime
        
        initial_state = {
            "tables": {},
            "last_query": "",
            "last_query_result": [],
            "query_history": [],
            "connection_info": {
                "type": "SQLite",
                "location": "in-memory",
                "created_at": datetime.datetime.now().isoformat()
            }
        }
        self.state_manager.set('database', initial_state)

    def load_content_pack_database(self, database_content: List[str]):
        """
        Load database content from a content pack.
        
        Args:
            database_content: List of SQL statements (CREATE/INSERT) to execute
        """
        try:
            for sql_statement in database_content:
                if sql_statement.strip():  # Skip empty statements
                    self.execute_sql(sql_statement)
            
            # Update the state with current table information
            self._update_table_info()
            
            logging.info(f"Successfully loaded {len(database_content)} SQL statements from content pack")
            
        except Exception as e:
            logging.error(f"Error loading content pack database content: {e}")
            raise

    def export_database_content(self) -> List[str]:
        """
        Export current database content as SQL statements for content packs.
        
        Returns:
            List of SQL CREATE and INSERT statements
        """
        try:
            cursor = self.connection.cursor()
            sql_statements = []
            
            # Get all table names (excluding sqlite internal tables)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            for table_name in table_names:
                # Get CREATE TABLE statement
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                create_sql = cursor.fetchone()
                if create_sql and create_sql[0]:
                    sql_statements.append(f"{create_sql[0]};")
                
                # Get INSERT statements for data
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                if rows:
                    # Get column names
                    column_names = [description[0] for description in cursor.description]
                    
                    for row in rows:
                        values = []
                        for value in row:
                            if value is None:
                                values.append("NULL")
                            elif isinstance(value, str):
                                # Escape single quotes in strings
                                escaped_value = value.replace("'", "''")
                                values.append(f"'{escaped_value}'")
                            else:
                                values.append(str(value))
                        
                        insert_sql = f"INSERT OR IGNORE INTO {table_name} ({', '.join(column_names)}) VALUES ({', '.join(values)});"
                        sql_statements.append(insert_sql)
            
            return sql_statements
            
        except Exception as e:
            logging.error(f"Error exporting database content: {e}")
            return []

    def _update_table_info(self):
        """Update the state manager with current table information."""
        try:
            cursor = self.connection.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            tables_info = {}
            for table_name in table_names:
                # Get column information for each table
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = []
                for col_info in cursor.fetchall():
                    columns.append({
                        "name": col_info[1],
                        "type": col_info[2],
                        "not_null": bool(col_info[3]),
                        "default_value": col_info[4],
                        "primary_key": bool(col_info[5])
                    })
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                tables_info[table_name] = {
                    "columns": columns,
                    "row_count": row_count
                }
            
            # Update state
            db_state = self.state_manager.get('database')
            db_state["tables"] = tables_info
            self.state_manager.set('database', db_state)
            
        except Exception as e:
            logging.error(f"Error updating table info: {e}")

    def execute_sql(self, sql_query: str, parameters: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute any SQL statement (CREATE, INSERT, UPDATE, DELETE, SELECT).
        Returns results for SELECT queries, empty list for others.
        """
        if not sql_query or not sql_query.strip():
            raise HTTPException(status_code=400, detail="SQL query cannot be empty")
        
        try:
            cursor = self.connection.cursor()
            
            if parameters:
                cursor.execute(sql_query, parameters)
            else:
                cursor.execute(sql_query)
            
            # Commit the transaction
            self.connection.commit()
            
            # Get results for SELECT queries
            results = []
            if sql_query.strip().lower().startswith('select'):
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
            
            # Update state with query information
            self._record_query(sql_query, results)
            
            # Update table info if it was a DDL or DML statement
            if any(sql_query.strip().lower().startswith(cmd) for cmd in ['create', 'drop', 'alter', 'insert', 'update', 'delete']):
                self._update_table_info()
            
            return results
            
        except sqlite3.Error as e:
            raise HTTPException(status_code=400, detail=f"SQL Error: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")

    def query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query. This method is kept for backward compatibility.
        """
        if not sql_query.strip().lower().startswith("select"):
            raise HTTPException(status_code=400, detail="This method only supports SELECT queries. Use execute_sql for other operations.")
        
        return self.execute_sql(sql_query)

    def create_table(self, table_name: str, columns: List[Dict[str, str]]) -> str:
        """
        Create a new table with specified columns.
        
        Args:
            table_name: Name of the table to create
            columns: List of column definitions, each with 'name', 'type', and optional 'constraints'
        """
        if not table_name or not columns:
            raise HTTPException(status_code=400, detail="Table name and columns are required")
        
        # Build CREATE TABLE statement
        column_defs = []
        for col in columns:
            if 'name' not in col or 'type' not in col:
                raise HTTPException(status_code=400, detail="Each column must have 'name' and 'type'")
            
            col_def = f"{col['name']} {col['type']}"
            if 'constraints' in col:
                col_def += f" {col['constraints']}"
            column_defs.append(col_def)
        
        sql = f"CREATE TABLE {table_name} ({', '.join(column_defs)})"
        self.execute_sql(sql)
        
        return f"Table '{table_name}' created successfully"

    def insert_data(self, table_name: str, data: Dict[str, Any]) -> str:
        """
        Insert data into a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column_name: value pairs
        """
        if not table_name or not data:
            raise HTTPException(status_code=400, detail="Table name and data are required")
        
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['?' for _ in values])
        
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        self.execute_sql(sql, tuple(values))
        
        return f"Data inserted into '{table_name}' successfully"

    def update_data(self, table_name: str, data: Dict[str, Any], where_clause: str, where_params: Optional[Tuple] = None) -> str:
        """
        Update data in a table.
        
        Args:
            table_name: Name of the table
            data: Dictionary of column_name: new_value pairs
            where_clause: WHERE clause (without the WHERE keyword)
            where_params: Parameters for the WHERE clause
        """
        if not table_name or not data or not where_clause:
            raise HTTPException(status_code=400, detail="Table name, data, and where clause are required")
        
        set_clauses = [f"{col} = ?" for col in data.keys()]
        values = list(data.values())
        
        if where_params:
            values.extend(where_params)
        
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {where_clause}"
        self.execute_sql(sql, tuple(values))
        
        return f"Data in '{table_name}' updated successfully"

    def delete_data(self, table_name: str, where_clause: str, where_params: Optional[Tuple] = None) -> str:
        """
        Delete data from a table.
        
        Args:
            table_name: Name of the table
            where_clause: WHERE clause (without the WHERE keyword)
            where_params: Parameters for the WHERE clause
        """
        if not table_name or not where_clause:
            raise HTTPException(status_code=400, detail="Table name and where clause are required")
        
        sql = f"DELETE FROM {table_name} WHERE {where_clause}"
        params = where_params if where_params else ()
        self.execute_sql(sql, params)
        
        return f"Data deleted from '{table_name}' successfully"

    def list_tables(self) -> List[str]:
        """
        List all tables in the database.
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error listing tables: {str(e)}")

    def describe_table(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get detailed information about a table's structure.
        """
        if not table_name:
            raise HTTPException(status_code=400, detail="Table name is required")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for col_info in cursor.fetchall():
                columns.append({
                    "column_id": col_info[0],
                    "name": col_info[1],
                    "type": col_info[2],
                    "not_null": bool(col_info[3]),
                    "default_value": col_info[4],
                    "primary_key": bool(col_info[5])
                })
            
            if not columns:
                raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
            
            return columns
        except sqlite3.Error as e:
            raise HTTPException(status_code=400, detail=f"SQL Error: {str(e)}")

    def get_query_history(self) -> List[Dict[str, Any]]:
        """
        Get the history of executed queries.
        """
        db_state = self.state_manager.get('database')
        return db_state.get("query_history", [])

    def _record_query(self, sql_query: str, results: List[Dict[str, Any]]):
        """
        Record the executed query in the state for observability.
        """
        import datetime
        
        db_state = self.state_manager.get('database')
        
        # Update last query info
        db_state["last_query"] = sql_query
        db_state["last_query_result"] = results
        
        # Add to query history (keep last 50 queries)
        query_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "query": sql_query,
            "result_count": len(results),
            "query_type": sql_query.strip().split()[0].upper() if sql_query.strip() else "UNKNOWN"
        }
        
        if "query_history" not in db_state:
            db_state["query_history"] = []
        
        db_state["query_history"].append(query_record)
        
        # Keep only the last 50 queries
        if len(db_state["query_history"]) > 50:
            db_state["query_history"] = db_state["query_history"][-50:]
        
        self.state_manager.set('database', db_state)