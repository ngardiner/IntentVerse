"""
Variable resolution system for content packs.

This module provides functionality to parse and resolve variable tokens in content pack data,
replacing {{variable_name}} tokens with actual values from pack defaults and user overrides.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

from .content_pack_variables import ContentPackVariableManager


@dataclass
class VariableToken:
    """
    Represents a parsed variable token from content.
    """
    full_match: str  # The complete token including braces: {{variable_name}}
    variable_name: str  # Just the variable name: variable_name
    start_pos: int  # Starting position in the original string
    end_pos: int  # Ending position in the original string


class VariableParseError(Exception):
    """
    Exception raised when variable token parsing fails.
    """
    pass


class VariableResolutionError(Exception):
    """
    Exception raised when variable resolution fails.
    """
    pass


class VariableResolver:
    """
    Handles parsing and resolution of variable tokens in content pack data.
    
    Supports the {{variable_name}} syntax for simple variable replacement.
    Variables are resolved in the following order:
    1. User overrides (from database)
    2. Pack defaults (from content pack JSON)
    3. Error if not found
    """

    # Regex pattern for variable tokens: {{variable_name}}
    # Variable names must start with letter or underscore, followed by letters, numbers, or underscores
    VARIABLE_TOKEN_PATTERN = re.compile(r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}')

    def __init__(self, variable_manager: Optional[ContentPackVariableManager] = None):
        """
        Initialize the variable resolver.

        Args:
            variable_manager: ContentPackVariableManager instance for user overrides
        """
        self.variable_manager = variable_manager
        self.logger = logging.getLogger(__name__)

    def parse_tokens(self, text: str) -> List[VariableToken]:
        """
        Parse variable tokens from a text string.

        Args:
            text: Text to parse for variable tokens

        Returns:
            List of VariableToken objects found in the text

        Raises:
            VariableParseError: If token parsing fails
        """
        try:
            tokens = []
            for match in self.VARIABLE_TOKEN_PATTERN.finditer(text):
                token = VariableToken(
                    full_match=match.group(0),
                    variable_name=match.group(1),
                    start_pos=match.start(),
                    end_pos=match.end()
                )
                tokens.append(token)
            
            return tokens

        except Exception as e:
            raise VariableParseError(f"Failed to parse variable tokens: {e}")

    def validate_variable_name(self, variable_name: str) -> bool:
        """
        Validate that a variable name follows the correct syntax.

        Args:
            variable_name: Variable name to validate

        Returns:
            True if valid, False otherwise
        """
        # Must start with letter or underscore, followed by letters, numbers, or underscores
        pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
        return bool(pattern.match(variable_name))

    def get_variable_value(
        self, 
        variable_name: str, 
        pack_defaults: Dict[str, str], 
        content_pack_name: str, 
        user_id: Optional[int] = None
    ) -> str:
        """
        Get the value for a variable, checking user overrides first, then pack defaults.

        Args:
            variable_name: Name of the variable
            pack_defaults: Default values from the content pack
            content_pack_name: Name of the content pack
            user_id: User ID for checking overrides

        Returns:
            Variable value

        Raises:
            VariableResolutionError: If variable cannot be resolved
        """
        try:
            # Check user override first (if user_id and variable_manager provided)
            if user_id is not None and self.variable_manager is not None:
                user_value = self.variable_manager.get_variable_value(
                    content_pack_name, variable_name, user_id
                )
                if user_value is not None:
                    self.logger.debug(
                        f"Resolved variable '{variable_name}' from user override: {user_value}"
                    )
                    return user_value

            # Check pack defaults
            if variable_name in pack_defaults:
                default_value = pack_defaults[variable_name]
                self.logger.debug(
                    f"Resolved variable '{variable_name}' from pack defaults: {default_value}"
                )
                return default_value

            # Variable not found
            raise VariableResolutionError(
                f"Variable '{variable_name}' not found in user overrides or pack defaults"
            )

        except VariableResolutionError:
            raise
        except Exception as e:
            raise VariableResolutionError(
                f"Failed to resolve variable '{variable_name}': {e}"
            )

    def resolve_string(
        self, 
        text: str, 
        pack_defaults: Dict[str, str], 
        content_pack_name: str, 
        user_id: Optional[int] = None,
        strict: bool = True
    ) -> str:
        """
        Resolve all variable tokens in a string.

        Args:
            text: Text containing variable tokens
            pack_defaults: Default values from the content pack
            content_pack_name: Name of the content pack
            user_id: User ID for checking overrides
            strict: If True, raise error for unresolved variables. If False, leave tokens unchanged.

        Returns:
            Text with variable tokens replaced

        Raises:
            VariableResolutionError: If strict=True and any variable cannot be resolved
        """
        if not isinstance(text, str):
            return text

        try:
            # Parse tokens
            tokens = self.parse_tokens(text)
            
            if not tokens:
                return text  # No tokens to resolve

            # Sort tokens by position (reverse order for replacement)
            tokens.sort(key=lambda t: t.start_pos, reverse=True)

            # Replace tokens from end to start to maintain positions
            result = text
            unresolved_variables = []

            for token in tokens:
                try:
                    value = self.get_variable_value(
                        token.variable_name, pack_defaults, content_pack_name, user_id
                    )
                    # Replace the token with its value
                    result = result[:token.start_pos] + value + result[token.end_pos:]
                    
                except VariableResolutionError as e:
                    if strict:
                        raise
                    else:
                        # In non-strict mode, keep the original token
                        unresolved_variables.append(token.variable_name)
                        self.logger.warning(f"Could not resolve variable '{token.variable_name}': {e}")

            if unresolved_variables and not strict:
                self.logger.info(
                    f"Left {len(unresolved_variables)} variables unresolved: {unresolved_variables}"
                )

            return result

        except VariableParseError:
            raise
        except VariableResolutionError:
            raise
        except Exception as e:
            raise VariableResolutionError(f"Failed to resolve string: {e}")

    def resolve_data_structure(
        self, 
        data: Any, 
        pack_defaults: Dict[str, str], 
        content_pack_name: str, 
        user_id: Optional[int] = None,
        strict: bool = True
    ) -> Any:
        """
        Recursively resolve variable tokens in a data structure (dict, list, or string).

        Args:
            data: Data structure to process
            pack_defaults: Default values from the content pack
            content_pack_name: Name of the content pack
            user_id: User ID for checking overrides
            strict: If True, raise error for unresolved variables

        Returns:
            Data structure with variable tokens replaced

        Raises:
            VariableResolutionError: If strict=True and any variable cannot be resolved
        """
        try:
            if isinstance(data, str):
                return self.resolve_string(data, pack_defaults, content_pack_name, user_id, strict)
            
            elif isinstance(data, dict):
                resolved_dict = {}
                for key, value in data.items():
                    # Resolve both keys and values
                    resolved_key = self.resolve_string(key, pack_defaults, content_pack_name, user_id, strict)
                    resolved_value = self.resolve_data_structure(value, pack_defaults, content_pack_name, user_id, strict)
                    resolved_dict[resolved_key] = resolved_value
                return resolved_dict
            
            elif isinstance(data, list):
                return [
                    self.resolve_data_structure(item, pack_defaults, content_pack_name, user_id, strict)
                    for item in data
                ]
            
            else:
                # For other types (int, float, bool, None), return as-is
                return data

        except (VariableParseError, VariableResolutionError):
            raise
        except Exception as e:
            raise VariableResolutionError(f"Failed to resolve data structure: {e}")

    def get_variables_in_text(self, text: str) -> List[str]:
        """
        Get a list of all variable names used in a text string.

        Args:
            text: Text to analyze

        Returns:
            List of unique variable names found in the text
        """
        if not isinstance(text, str):
            return []

        try:
            tokens = self.parse_tokens(text)
            return list(set(token.variable_name for token in tokens))
        except VariableParseError:
            return []

    def get_variables_in_data_structure(self, data: Any) -> List[str]:
        """
        Get a list of all variable names used in a data structure.

        Args:
            data: Data structure to analyze

        Returns:
            List of unique variable names found in the data structure
        """
        variables = set()

        try:
            if isinstance(data, str):
                variables.update(self.get_variables_in_text(data))
            
            elif isinstance(data, dict):
                for key, value in data.items():
                    variables.update(self.get_variables_in_text(key))
                    variables.update(self.get_variables_in_data_structure(value))
            
            elif isinstance(data, list):
                for item in data:
                    variables.update(self.get_variables_in_data_structure(item))

            return list(variables)

        except Exception as e:
            self.logger.error(f"Error analyzing data structure for variables: {e}")
            return []

    def validate_content_pack_variables(
        self, 
        content_pack_data: Dict[str, Any], 
        pack_defaults: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Validate that all variables used in a content pack are defined in pack defaults.

        Args:
            content_pack_data: Complete content pack data
            pack_defaults: Default variable values

        Returns:
            Dictionary with validation results
        """
        try:
            # Get all variables used in the content pack
            used_variables = self.get_variables_in_data_structure(content_pack_data)
            
            # Check which variables are defined
            defined_variables = set(pack_defaults.keys())
            used_variables_set = set(used_variables)
            
            # Find undefined variables
            undefined_variables = used_variables_set - defined_variables
            
            # Find unused defined variables
            unused_variables = defined_variables - used_variables_set

            return {
                "valid": len(undefined_variables) == 0,
                "used_variables": sorted(used_variables),
                "defined_variables": sorted(defined_variables),
                "undefined_variables": sorted(undefined_variables),
                "unused_variables": sorted(unused_variables),
                "total_used": len(used_variables),
                "total_defined": len(defined_variables),
            }

        except Exception as e:
            self.logger.error(f"Error validating content pack variables: {e}")
            return {
                "valid": False,
                "error": str(e),
                "used_variables": [],
                "defined_variables": [],
                "undefined_variables": [],
                "unused_variables": [],
                "total_used": 0,
                "total_defined": 0,
            }


def create_variable_resolver(variable_manager: Optional[ContentPackVariableManager] = None) -> VariableResolver:
    """
    Factory function to create a VariableResolver instance.

    Args:
        variable_manager: ContentPackVariableManager instance for user overrides

    Returns:
        VariableResolver instance
    """
    return VariableResolver(variable_manager)


# Convenience functions for standalone usage
def resolve_string_standalone(
    text: str, 
    pack_defaults: Dict[str, str], 
    content_pack_name: str = "unknown",
    strict: bool = True
) -> str:
    """
    Standalone function to resolve variables in a string without user overrides.

    Args:
        text: Text containing variable tokens
        pack_defaults: Default values from the content pack
        content_pack_name: Name of the content pack
        strict: If True, raise error for unresolved variables

    Returns:
        Text with variable tokens replaced
    """
    resolver = create_variable_resolver()
    return resolver.resolve_string(text, pack_defaults, content_pack_name, None, strict)


def get_variables_in_text_standalone(text: str) -> List[str]:
    """
    Standalone function to get variable names from text.

    Args:
        text: Text to analyze

    Returns:
        List of unique variable names found in the text
    """
    resolver = create_variable_resolver()
    return resolver.get_variables_in_text(text)