"""
Unit tests for ContentPackVariable model and CRUD operations.
"""

import pytest
from sqlmodel import Session, select
from unittest.mock import Mock

from app.models import ContentPackVariable, User
from app.content_pack_variables import ContentPackVariableManager
from app.security import get_password_hash


class TestContentPackVariableModel:
    """Tests for the ContentPackVariable model."""

    def test_content_pack_variable_creation(self, session):
        """Test creating a ContentPackVariable instance."""
        # Create a test user first
        user = User(
            username="testuser",
            hashed_password=get_password_hash("testpass"),
            full_name="Test User",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # Create a content pack variable
        variable = ContentPackVariable(
            content_pack_name="test_pack",
            variable_name="email_domain",
            variable_value="example.com",
            user_id=user.id,
        )

        session.add(variable)
        session.commit()
        session.refresh(variable)

        # Verify the variable was created correctly
        assert variable.id is not None
        assert variable.content_pack_name == "test_pack"
        assert variable.variable_name == "email_domain"
        assert variable.variable_value == "example.com"
        assert variable.user_id == user.id
        assert variable.created_at is not None
        assert variable.updated_at is not None

    def test_unique_constraint(self, session):
        """Test that the unique constraint works correctly."""
        # Create a test user
        user = User(
            username="testuser2",
            hashed_password=get_password_hash("testpass"),
            full_name="Test User 2",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # Create first variable
        variable1 = ContentPackVariable(
            content_pack_name="test_pack",
            variable_name="email_domain",
            variable_value="example.com",
            user_id=user.id,
        )
        session.add(variable1)
        session.commit()

        # Try to create a duplicate variable (should fail)
        variable2 = ContentPackVariable(
            content_pack_name="test_pack",
            variable_name="email_domain",
            variable_value="different.com",
            user_id=user.id,
        )
        session.add(variable2)

        # Should raise an integrity error due to unique constraint
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            session.commit()


class TestContentPackVariableManager:
    """Tests for the ContentPackVariableManager class."""

    @pytest.fixture
    def test_user(self, session):
        """Create a test user for variable operations."""
        import uuid
        username = f"vartest_{uuid.uuid4().hex[:8]}"
        user = User(
            username=username,
            hashed_password=get_password_hash("testpass"),
            full_name="Variable Test User",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @pytest.fixture
    def variable_manager(self, session):
        """Create a ContentPackVariableManager instance."""
        return ContentPackVariableManager(session)

    def test_set_and_get_variable(self, variable_manager, test_user):
        """Test setting and getting a variable value."""
        # Set a variable
        success = variable_manager.set_variable_value(
            "test_pack", "email_domain", "example.com", test_user.id
        )
        assert success is True

        # Get the variable
        value = variable_manager.get_variable_value(
            "test_pack", "email_domain", test_user.id
        )
        assert value == "example.com"

    def test_update_existing_variable(self, variable_manager, test_user):
        """Test updating an existing variable value."""
        # Set initial value
        variable_manager.set_variable_value(
            "test_pack", "company_name", "ACME Corp", test_user.id
        )

        # Update the value
        success = variable_manager.set_variable_value(
            "test_pack", "company_name", "New Corp", test_user.id
        )
        assert success is True

        # Verify the updated value
        value = variable_manager.get_variable_value(
            "test_pack", "company_name", test_user.id
        )
        assert value == "New Corp"

    def test_get_pack_variables(self, variable_manager, test_user):
        """Test getting all variables for a content pack."""
        # Set multiple variables
        variable_manager.set_variable_value(
            "test_pack", "email_domain", "example.com", test_user.id
        )
        variable_manager.set_variable_value(
            "test_pack", "company_name", "ACME Corp", test_user.id
        )

        # Get all variables for the pack
        variables = variable_manager.get_pack_variables("test_pack", test_user.id)

        assert len(variables) == 2
        assert variables["email_domain"] == "example.com"
        assert variables["company_name"] == "ACME Corp"

    def test_delete_variable(self, variable_manager, test_user):
        """Test deleting a variable."""
        # Set a variable
        variable_manager.set_variable_value(
            "test_pack", "temp_var", "temp_value", test_user.id
        )

        # Verify it exists
        value = variable_manager.get_variable_value(
            "test_pack", "temp_var", test_user.id
        )
        assert value == "temp_value"

        # Delete the variable
        success = variable_manager.delete_variable(
            "test_pack", "temp_var", test_user.id
        )
        assert success is True

        # Verify it's gone
        value = variable_manager.get_variable_value(
            "test_pack", "temp_var", test_user.id
        )
        assert value is None

    def test_reset_pack_variables(self, variable_manager, test_user):
        """Test resetting all variables for a content pack."""
        # Set multiple variables
        variable_manager.set_variable_value(
            "reset_pack", "var1", "value1", test_user.id
        )
        variable_manager.set_variable_value(
            "reset_pack", "var2", "value2", test_user.id
        )

        # Verify they exist
        variables = variable_manager.get_pack_variables("reset_pack", test_user.id)
        assert len(variables) == 2

        # Reset all variables
        success = variable_manager.reset_pack_variables("reset_pack", test_user.id)
        assert success is True

        # Verify they're all gone
        variables = variable_manager.get_pack_variables("reset_pack", test_user.id)
        assert len(variables) == 0

    def test_get_all_user_variables(self, variable_manager, test_user):
        """Test getting all variables for a user across multiple packs."""
        # Set variables in different packs
        variable_manager.set_variable_value(
            "pack1", "var1", "value1", test_user.id
        )
        variable_manager.set_variable_value(
            "pack2", "var2", "value2", test_user.id
        )

        # Get all user variables
        all_variables = variable_manager.get_all_user_variables(test_user.id)

        assert len(all_variables) == 2
        assert "pack1" in all_variables
        assert "pack2" in all_variables
        assert all_variables["pack1"]["var1"] == "value1"
        assert all_variables["pack2"]["var2"] == "value2"

    def test_get_variable_usage_stats(self, variable_manager, test_user):
        """Test getting variable usage statistics."""
        # Set some variables
        variable_manager.set_variable_value(
            "stats_pack", "email_domain", "example.com", test_user.id
        )
        variable_manager.set_variable_value(
            "stats_pack", "company_name", "ACME Corp", test_user.id
        )

        # Get stats
        stats = variable_manager.get_variable_usage_stats()

        assert stats["total_variables"] >= 2
        assert stats["unique_packs"] >= 1
        assert stats["unique_users"] >= 1
        assert "stats_pack" in stats["pack_breakdown"]
        assert "email_domain" in stats["variable_breakdown"]
        assert "company_name" in stats["variable_breakdown"]

    def test_nonexistent_variable(self, variable_manager, test_user):
        """Test getting a variable that doesn't exist."""
        value = variable_manager.get_variable_value(
            "nonexistent_pack", "nonexistent_var", test_user.id
        )
        assert value is None

    def test_delete_nonexistent_variable(self, variable_manager, test_user):
        """Test deleting a variable that doesn't exist."""
        success = variable_manager.delete_variable(
            "nonexistent_pack", "nonexistent_var", test_user.id
        )
        assert success is False