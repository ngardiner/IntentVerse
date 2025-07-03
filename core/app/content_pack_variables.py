"""
CRUD operations for content pack variables.

This module provides functions to manage user-specific variable overrides
for content packs, including creating, reading, updating, and deleting
variable values.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlmodel import Session, select
from datetime import datetime

from .models import ContentPackVariable, User
from .database_compat import get_session


class ContentPackVariableManager:
    """
    Manages content pack variables with CRUD operations.
    """

    def __init__(self, session: Session):
        self.session = session

    def get_pack_variables(
        self, content_pack_name: str, user_id: int
    ) -> Dict[str, str]:
        """
        Get all variable overrides for a specific content pack and user.

        Args:
            content_pack_name: Name of the content pack
            user_id: ID of the user

        Returns:
            Dictionary mapping variable names to their values
        """
        try:
            statement = select(ContentPackVariable).where(
                ContentPackVariable.content_pack_name == content_pack_name,
                ContentPackVariable.user_id == user_id,
            )
            variables = self.session.exec(statement).all()

            return {var.variable_name: var.variable_value for var in variables}

        except Exception as e:
            logging.error(
                f"Error getting variables for pack '{content_pack_name}' and user {user_id}: {e}"
            )
            return {}

    def get_variable_value(
        self, content_pack_name: str, variable_name: str, user_id: int
    ) -> Optional[str]:
        """
        Get a specific variable value for a content pack and user.

        Args:
            content_pack_name: Name of the content pack
            variable_name: Name of the variable
            user_id: ID of the user

        Returns:
            Variable value if found, None otherwise
        """
        try:
            statement = select(ContentPackVariable).where(
                ContentPackVariable.content_pack_name == content_pack_name,
                ContentPackVariable.variable_name == variable_name,
                ContentPackVariable.user_id == user_id,
            )
            variable = self.session.exec(statement).first()

            return variable.variable_value if variable else None

        except Exception as e:
            logging.error(
                f"Error getting variable '{variable_name}' for pack '{content_pack_name}' and user {user_id}: {e}"
            )
            return None

    def set_variable_value(
        self, content_pack_name: str, variable_name: str, variable_value: str, user_id: int
    ) -> bool:
        """
        Set a variable value for a content pack and user.
        Creates a new record or updates an existing one.

        Args:
            content_pack_name: Name of the content pack
            variable_name: Name of the variable
            variable_value: Value to set
            user_id: ID of the user

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if variable already exists
            statement = select(ContentPackVariable).where(
                ContentPackVariable.content_pack_name == content_pack_name,
                ContentPackVariable.variable_name == variable_name,
                ContentPackVariable.user_id == user_id,
            )
            existing_variable = self.session.exec(statement).first()

            if existing_variable:
                # Update existing variable
                existing_variable.variable_value = variable_value
                existing_variable.updated_at = datetime.utcnow()
                logging.info(
                    f"Updated variable '{variable_name}' for pack '{content_pack_name}' and user {user_id}"
                )
            else:
                # Create new variable
                new_variable = ContentPackVariable(
                    content_pack_name=content_pack_name,
                    variable_name=variable_name,
                    variable_value=variable_value,
                    user_id=user_id,
                )
                self.session.add(new_variable)
                logging.info(
                    f"Created variable '{variable_name}' for pack '{content_pack_name}' and user {user_id}"
                )

            self.session.commit()
            return True

        except Exception as e:
            logging.error(
                f"Error setting variable '{variable_name}' for pack '{content_pack_name}' and user {user_id}: {e}"
            )
            self.session.rollback()
            return False

    def delete_variable(
        self, content_pack_name: str, variable_name: str, user_id: int
    ) -> bool:
        """
        Delete a specific variable override for a content pack and user.

        Args:
            content_pack_name: Name of the content pack
            variable_name: Name of the variable
            user_id: ID of the user

        Returns:
            True if successful, False otherwise
        """
        try:
            statement = select(ContentPackVariable).where(
                ContentPackVariable.content_pack_name == content_pack_name,
                ContentPackVariable.variable_name == variable_name,
                ContentPackVariable.user_id == user_id,
            )
            variable = self.session.exec(statement).first()

            if variable:
                self.session.delete(variable)
                self.session.commit()
                logging.info(
                    f"Deleted variable '{variable_name}' for pack '{content_pack_name}' and user {user_id}"
                )
                return True
            else:
                logging.warning(
                    f"Variable '{variable_name}' not found for pack '{content_pack_name}' and user {user_id}"
                )
                return False

        except Exception as e:
            logging.error(
                f"Error deleting variable '{variable_name}' for pack '{content_pack_name}' and user {user_id}: {e}"
            )
            self.session.rollback()
            return False

    def reset_pack_variables(self, content_pack_name: str, user_id: int) -> bool:
        """
        Delete all variable overrides for a specific content pack and user.

        Args:
            content_pack_name: Name of the content pack
            user_id: ID of the user

        Returns:
            True if successful, False otherwise
        """
        try:
            statement = select(ContentPackVariable).where(
                ContentPackVariable.content_pack_name == content_pack_name,
                ContentPackVariable.user_id == user_id,
            )
            variables = self.session.exec(statement).all()

            for variable in variables:
                self.session.delete(variable)

            self.session.commit()
            logging.info(
                f"Reset all variables for pack '{content_pack_name}' and user {user_id} ({len(variables)} variables deleted)"
            )
            return True

        except Exception as e:
            logging.error(
                f"Error resetting variables for pack '{content_pack_name}' and user {user_id}: {e}"
            )
            self.session.rollback()
            return False

    def get_all_user_variables(self, user_id: int) -> Dict[str, Dict[str, str]]:
        """
        Get all variable overrides for a specific user across all content packs.

        Args:
            user_id: ID of the user

        Returns:
            Dictionary mapping content pack names to their variable dictionaries
        """
        try:
            statement = select(ContentPackVariable).where(
                ContentPackVariable.user_id == user_id
            )
            variables = self.session.exec(statement).all()

            result = {}
            for var in variables:
                if var.content_pack_name not in result:
                    result[var.content_pack_name] = {}
                result[var.content_pack_name][var.variable_name] = var.variable_value

            return result

        except Exception as e:
            logging.error(f"Error getting all variables for user {user_id}: {e}")
            return {}

    def get_variable_usage_stats(self) -> Dict[str, Any]:
        """
        Get statistics about variable usage across all content packs and users.

        Returns:
            Dictionary with usage statistics
        """
        try:
            statement = select(ContentPackVariable)
            all_variables = self.session.exec(statement).all()

            stats = {
                "total_variables": len(all_variables),
                "unique_packs": len(set(var.content_pack_name for var in all_variables)),
                "unique_users": len(set(var.user_id for var in all_variables)),
                "pack_breakdown": {},
                "variable_breakdown": {},
            }

            # Count variables per pack
            for var in all_variables:
                pack_name = var.content_pack_name
                if pack_name not in stats["pack_breakdown"]:
                    stats["pack_breakdown"][pack_name] = 0
                stats["pack_breakdown"][pack_name] += 1

            # Count usage per variable name
            for var in all_variables:
                var_name = var.variable_name
                if var_name not in stats["variable_breakdown"]:
                    stats["variable_breakdown"][var_name] = 0
                stats["variable_breakdown"][var_name] += 1

            return stats

        except Exception as e:
            logging.error(f"Error getting variable usage stats: {e}")
            return {
                "total_variables": 0,
                "unique_packs": 0,
                "unique_users": 0,
                "pack_breakdown": {},
                "variable_breakdown": {},
            }


def get_variable_manager(session: Session) -> ContentPackVariableManager:
    """
    Factory function to create a ContentPackVariableManager instance.

    Args:
        session: Database session

    Returns:
        ContentPackVariableManager instance
    """
    return ContentPackVariableManager(session)


# Convenience functions for standalone usage
def get_pack_variables_standalone(
    content_pack_name: str, user_id: int
) -> Dict[str, str]:
    """
    Standalone function to get pack variables without requiring a session.

    Args:
        content_pack_name: Name of the content pack
        user_id: ID of the user

    Returns:
        Dictionary mapping variable names to their values
    """
    for session in get_session():
        manager = get_variable_manager(session)
        return manager.get_pack_variables(content_pack_name, user_id)


def set_variable_value_standalone(
    content_pack_name: str, variable_name: str, variable_value: str, user_id: int
) -> bool:
    """
    Standalone function to set a variable value without requiring a session.

    Args:
        content_pack_name: Name of the content pack
        variable_name: Name of the variable
        variable_value: Value to set
        user_id: ID of the user

    Returns:
        True if successful, False otherwise
    """
    for session in get_session():
        manager = get_variable_manager(session)
        return manager.set_variable_value(
            content_pack_name, variable_name, variable_value, user_id
        )