import pytest
from app.modules.web_search.tool import WebSearchTool
from app.state_manager import StateManager

class TestWebSearchTool:
    """Test suite for the WebSearchTool class."""
    
    @pytest.fixture
    def state_manager(self):
        """Create a fresh state manager for each test."""
        return StateManager()
    
    @pytest.fixture
    def web_search_tool(self, state_manager):
        """Create a WebSearchTool instance with a clean state manager."""
        return WebSearchTool(state_manager)
    
    def test_initialization(self, web_search_tool, state_manager):
        """Test that the WebSearchTool initializes correctly."""
        assert 'web_search' in state_manager.get_full_state()
        assert 'search_history' in state_manager.get('web_search')
        assert 'last_search_results' in state_manager.get('web_search')
    
    def test_search(self, web_search_tool):
        """Test the search functionality."""
        results = web_search_tool.search("python programming")
        
        # Check that we got results
        assert len(results) >= 3
        assert all(isinstance(result, dict) for result in results)
        assert all('title' in result for result in results)
        assert all('url' in result for result in results)
        assert all('snippet' in result for result in results)
        
        # Check that the state was updated
        web_search_state = web_search_tool.state_manager.get('web_search')
        assert len(web_search_state['search_history']) == 1
        assert web_search_state['search_history'][0]['query'] == "python programming"
        assert len(web_search_state['last_search_results']) >= 3
    
    def test_get_search_history(self, web_search_tool):
        """Test retrieving search history."""
        # Perform multiple searches
        web_search_tool.search("python")
        web_search_tool.search("javascript")
        web_search_tool.search("machine learning")
        
        # Get history
        history = web_search_tool.get_search_history()
        
        # Check that history is returned in reverse chronological order
        assert len(history) == 3
        assert history[0]['query'] == "machine learning"
        assert history[1]['query'] == "javascript"
        assert history[2]['query'] == "python"
        
        # Test with limit
        limited_history = web_search_tool.get_search_history(limit=2)
        assert len(limited_history) == 2
        assert limited_history[0]['query'] == "machine learning"
        assert limited_history[1]['query'] == "javascript"
    
    def test_clear_search_history(self, web_search_tool):
        """Test clearing search history."""
        # Perform searches
        web_search_tool.search("test query")
        
        # Verify history exists
        assert len(web_search_tool.get_search_history()) == 1
        
        # Clear history
        result = web_search_tool.clear_search_history()
        
        # Check result
        assert result['status'] == "success"
        
        # Verify history is cleared
        assert len(web_search_tool.get_search_history()) == 0
    
    def test_get_last_search_results(self, web_search_tool):
        """Test retrieving last search results."""
        # Perform a search
        original_results = web_search_tool.search("artificial intelligence")
        
        # Get last results
        last_results = web_search_tool.get_last_search_results()
        
        # Check that they match
        assert len(last_results) == len(original_results)
        assert all(r1 == r2 for r1, r2 in zip(last_results, original_results))
        
        # Perform another search
        new_results = web_search_tool.search("neural networks")
        
        # Check that last results updated
        updated_last_results = web_search_tool.get_last_search_results()
        assert len(updated_last_results) == len(new_results)
        assert all(r1 == r2 for r1, r2 in zip(updated_last_results, new_results))
        assert updated_last_results != last_results