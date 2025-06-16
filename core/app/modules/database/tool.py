from typing import Any, Dict, List
from ..base_tool import BaseTool
from fastapi import HTTPException

class DatabaseTool(BaseTool):
    """
    Implements the logic for a mock SQL database.
    NOTE: This is a barebones placeholder.
    """

    def __init__(self, state_manager: Any):
        """
        Initializes the DatabaseTool with a reference to the state manager.
        """
        super().__init__(state_manager)
        if 'database' not in self.state_manager.get_full_state():
            # Initialize with a dummy structure
            self.state_manager.set('database', {
                "tables": ["users", "products"],
                "last_query_result": []
            })

    def query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Executes a read-only SQL query against the mock database.
        For safety, only SELECT statements are allowed.
        """
        if not sql_query.strip().lower().startswith("select"):
            raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")
        
        # In a real implementation, you would parse the SQL and query
        # the in-memory state. For now, we return mock data.
        print(f"DATABASE: Executing query: {sql_query}")
        
        mock_result = [
            {"id": 1, "product_name": "AI Agent Pro", "price": 99.99},
            {"id": 2, "product_name": "IntentVerse Subscription", "price": 29.99},
        ]
        
        db_state = self.state_manager.get('database')
        db_state["last_query_result"] = mock_result
        self.state_manager.set('database', db_state)
        
        return mock_result

    def list_tables(self) -> List[str]:
        """
        Lists all available tables in the mock database.
        """
        return self.state_manager.get('database').get("tables", [])