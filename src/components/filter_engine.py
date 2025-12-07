"""Filter Engine for evaluating filter conditions in policies.

This module provides the core filter evaluation logic that supports all operators
defined in the permissions DSL.
"""

from typing import Any, Dict

from src.models.common import Filter, FilterOperator


class FilterEngine:
    """Engine for evaluating filter conditions against context objects."""

    def evaluate_filter(
        self, filter_condition: Filter, context: Dict[str, Any]
    ) -> bool:
        """Evaluate a single filter condition against the provided context.

        Args:
            filter_condition: The filter condition to evaluate
            context: Dictionary containing user, document, and other context data

        Returns:
            bool: True if the filter condition is satisfied, False otherwise

        Example:
            context = {
                "user": {"id": "user1", "email": "user1@example.com"},
                "document": {"creatorId": "user1", "projectId": "proj1"}
            }
            filter_condition = Filter(prop="document.creatorId", op="==", value="user.id")
            result = engine.evaluate_filter(filter_condition, context)
        """
        # Resolve the property value from context
        prop_value = self._resolve_property(filter_condition.prop, context)

        # Resolve the comparison value (might be a reference like "user.id")
        comparison_value = self._resolve_value(filter_condition.value, context)

        # Evaluate based on operator
        return self._apply_operator(prop_value, filter_condition.op, comparison_value)

    def evaluate_filters(self, filters: list[Filter], context: Dict[str, Any]) -> bool:
        """Evaluate multiple filter conditions (AND logic).

        All filters must be satisfied for this to return True.

        Args:
            filters: List of filter conditions
            context: Dictionary containing user, document, and other context data

        Returns:
            bool: True if all filters are satisfied, False otherwise
        """
        if not filters:
            return True  # No filters means no restrictions

        return all(self.evaluate_filter(f, context) for f in filters)

    def _resolve_property(self, prop_path: str, context: Dict[str, Any]) -> Any:
        """Resolve a property path from the context.

        Args:
            prop_path: Dot-separated property path (e.g., "user.id", "document.creatorId")
            context: Context dictionary

        Returns:
            The resolved value, or None if not found
        """
        parts = prop_path.split(".")
        current = context

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return None
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    def _resolve_value(self, value: Any, context: Dict[str, Any]) -> Any:
        """Resolve a value which might be a reference or a literal.

        If value is a string starting with a context key (user., document., etc.),
        treat it as a property reference. Otherwise, return as-is.

        Args:
            value: The value to resolve (could be literal or reference)
            context: Context dictionary

        Returns:
            The resolved value
        """
        if not isinstance(value, str):
            return value

        # Check if this looks like a property reference
        if "." in value and any(value.startswith(f"{key}.") for key in context.keys()):
            return self._resolve_property(value, context)

        return value

    def _apply_operator(self, left: Any, operator: FilterOperator, right: Any) -> bool:
        """Apply a comparison operator to two values.

        Args:
            left: Left operand
            operator: Comparison operator
            right: Right operand

        Returns:
            bool: Result of the comparison
        """
        # Handle null checks first
        if operator == FilterOperator.NE_NULL:  # "<>" means not null
            return left is not None

        # If left is None for other operators, return False
        if left is None:
            return False

        # Apply operator
        if operator == FilterOperator.EQ:  # "=="
            return left == right

        elif operator == FilterOperator.NE:  # "!="
            return left != right

        elif operator == FilterOperator.GT:  # ">"
            try:
                return left > right
            except TypeError:
                return False

        elif operator == FilterOperator.GTE:  # ">="
            try:
                return left >= right
            except TypeError:
                return False

        elif operator == FilterOperator.LT:  # "<"
            try:
                return left < right
            except TypeError:
                return False

        elif operator == FilterOperator.LTE:  # "<="
            try:
                return left <= right
            except TypeError:
                return False

        elif operator == FilterOperator.IN:  # "in"
            if not isinstance(right, (list, tuple, set)):
                return False
            return left in right

        elif operator == FilterOperator.NOT_IN:  # "not in"
            if not isinstance(right, (list, tuple, set)):
                return True
            return left not in right

        elif operator == FilterOperator.HAS:  # "has" - substring/contains check
            if isinstance(left, str) and isinstance(right, str):
                return right in left
            elif isinstance(left, (list, tuple, set)):
                return right in left
            return False

        elif operator == FilterOperator.HAS_NOT:  # "has not"
            if isinstance(left, str) and isinstance(right, str):
                return right not in left
            elif isinstance(left, (list, tuple, set)):
                return right not in left
            return True

        # Unknown operator
        return False
