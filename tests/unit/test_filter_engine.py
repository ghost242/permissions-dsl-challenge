"""Unit tests for Filter Engine.

Tests all filter operators and property resolution logic.
"""

import pytest
from src.components.filter_engine import FilterEngine
from src.models.common import Filter, FilterOperator


class TestFilterOperators:
    """Test all filter operators."""

    def setup_method(self):
        """Setup test instance."""
        self.engine = FilterEngine()

    # Equality operators
    def test_operator_eq_matching_values(self):
        """Test == operator with matching values."""
        filter_cond = Filter(prop="user.id", op=FilterOperator.EQ, value="user123")
        context = {"user": {"id": "user123"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

    def test_operator_eq_different_values(self):
        """Test == operator with different values."""
        filter_cond = Filter(prop="user.id", op=FilterOperator.EQ, value="user123")
        context = {"user": {"id": "user456"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_ne_matching_values(self):
        """Test != operator with matching values."""
        filter_cond = Filter(prop="user.id", op=FilterOperator.NE, value="user123")
        context = {"user": {"id": "user123"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_ne_different_values(self):
        """Test != operator with different values."""
        filter_cond = Filter(prop="user.id", op=FilterOperator.NE, value="user123")
        context = {"user": {"id": "user456"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

    # Comparison operators
    def test_operator_gt_with_numbers(self):
        """Test > operator with numbers."""
        filter_cond = Filter(prop="user.age", op=FilterOperator.GT, value=18)
        context = {"user": {"age": 25}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

        context = {"user": {"age": 15}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_gte_with_numbers(self):
        """Test >= operator with numbers."""
        filter_cond = Filter(prop="user.age", op=FilterOperator.GTE, value=18)
        context = {"user": {"age": 18}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

        context = {"user": {"age": 17}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_lt_with_numbers(self):
        """Test < operator with numbers."""
        filter_cond = Filter(prop="user.age", op=FilterOperator.LT, value=18)
        context = {"user": {"age": 15}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

        context = {"user": {"age": 25}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_lte_with_numbers(self):
        """Test <= operator with numbers."""
        filter_cond = Filter(prop="user.age", op=FilterOperator.LTE, value=18)
        context = {"user": {"age": 18}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

        context = {"user": {"age": 19}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    # Null checks
    def test_operator_ne_null_with_non_null_value(self):
        """Test <> (not null) operator with non-null value."""
        filter_cond = Filter(
            prop="document.deletedAt", op=FilterOperator.NE_NULL, value=None
        )
        context = {"document": {"deletedAt": "2025-01-01"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

    def test_operator_ne_null_with_null_value(self):
        """Test <> (not null) operator with null value."""
        filter_cond = Filter(
            prop="document.deletedAt", op=FilterOperator.NE_NULL, value=None
        )
        context = {"document": {"deletedAt": None}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    # List operators
    def test_operator_in_with_value_in_list(self):
        """Test 'in' operator with value in list."""
        filter_cond = Filter(
            prop="user.role", op=FilterOperator.IN, value=["admin", "editor"]
        )
        context = {"user": {"role": "admin"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

    def test_operator_in_with_value_not_in_list(self):
        """Test 'in' operator with value not in list."""
        filter_cond = Filter(
            prop="user.role", op=FilterOperator.IN, value=["admin", "editor"]
        )
        context = {"user": {"role": "viewer"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_not_in_with_value_in_list(self):
        """Test 'not in' operator with value in list."""
        filter_cond = Filter(
            prop="user.role", op=FilterOperator.NOT_IN, value=["admin", "editor"]
        )
        context = {"user": {"role": "admin"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_not_in_with_value_not_in_list(self):
        """Test 'not in' operator with value not in list."""
        filter_cond = Filter(
            prop="user.role", op=FilterOperator.NOT_IN, value=["admin", "editor"]
        )
        context = {"user": {"role": "viewer"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

    # String operators
    def test_operator_has_substring_match(self):
        """Test 'has' operator with substring match."""
        filter_cond = Filter(prop="document.title", op=FilterOperator.HAS, value="test")
        context = {"document": {"title": "This is a test document"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

    def test_operator_has_substring_no_match(self):
        """Test 'has' operator with no substring match."""
        filter_cond = Filter(prop="document.title", op=FilterOperator.HAS, value="xyz")
        context = {"document": {"title": "This is a test document"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_has_not_substring_match(self):
        """Test 'has not' operator with substring match."""
        filter_cond = Filter(
            prop="document.title", op=FilterOperator.HAS_NOT, value="test"
        )
        context = {"document": {"title": "This is a test document"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_operator_has_not_substring_no_match(self):
        """Test 'has not' operator with no substring match."""
        filter_cond = Filter(
            prop="document.title", op=FilterOperator.HAS_NOT, value="xyz"
        )
        context = {"document": {"title": "This is a test document"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True


class TestPropertyResolution:
    """Test property path resolution."""

    def setup_method(self):
        """Setup test instance."""
        self.engine = FilterEngine()

    def test_resolve_property_simple_path(self):
        """Test resolving simple property path."""
        context = {"user": {"id": "user123"}}
        result = self.engine._resolve_property("user.id", context)
        assert result == "user123"

    def test_resolve_property_nested_path(self):
        """Test resolving nested property path."""
        context = {"user": {"profile": {"email": "test@example.com"}}}
        result = self.engine._resolve_property("user.profile.email", context)
        assert result == "test@example.com"

    def test_resolve_property_missing_path(self):
        """Test resolving missing property path."""
        context = {"user": {"id": "user123"}}
        result = self.engine._resolve_property("user.missing", context)
        assert result is None

    def test_resolve_property_from_model(self):
        """Test resolving property from Pydantic model."""
        from src.models.entities import User

        user = User(id="user1", email="test@example.com", name="Test")
        context = {"user": user}
        result = self.engine._resolve_property("user.email", context)
        assert result == "test@example.com"


class TestValueResolution:
    """Test value resolution (literal vs reference)."""

    def setup_method(self):
        """Setup test instance."""
        self.engine = FilterEngine()

    def test_resolve_value_literal_string(self):
        """Test resolving literal string value."""
        result = self.engine._resolve_value("user123", {"user": {"id": "user123"}})
        assert result == "user123"

    def test_resolve_value_literal_number(self):
        """Test resolving literal number value."""
        result = self.engine._resolve_value(42, {"user": {"age": 30}})
        assert result == 42

    def test_resolve_value_property_reference(self):
        """Test resolving property reference value."""
        context = {"user": {"id": "user123"}, "document": {"creatorId": "user123"}}
        result = self.engine._resolve_value("user.id", context)
        assert result == "user123"

    def test_resolve_value_with_context(self):
        """Test value resolution with full context."""
        context = {"user": {"id": "user1"}, "document": {"creatorId": "user1"}}
        # Should resolve user.id from context
        result = self.engine._resolve_value("user.id", context)
        assert result == "user1"


class TestFilterEvaluation:
    """Test filter evaluation logic."""

    def setup_method(self):
        """Setup test instance."""
        self.engine = FilterEngine()

    def test_evaluate_single_filter_pass(self):
        """Test evaluating single filter that passes."""
        filter_cond = Filter(
            prop="document.creatorId", op=FilterOperator.EQ, value="user.id"
        )
        context = {"user": {"id": "user1"}, "document": {"creatorId": "user1"}}
        assert self.engine.evaluate_filter(filter_cond, context) is True

    def test_evaluate_single_filter_fail(self):
        """Test evaluating single filter that fails."""
        filter_cond = Filter(
            prop="document.creatorId", op=FilterOperator.EQ, value="user.id"
        )
        context = {"user": {"id": "user1"}, "document": {"creatorId": "user2"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_evaluate_multiple_filters_all_pass(self):
        """Test evaluating multiple filters (AND logic) - all pass."""
        filters = [
            Filter(prop="user.role", op=FilterOperator.EQ, value="admin"),
            Filter(prop="user.age", op=FilterOperator.GTE, value=18),
        ]
        context = {"user": {"role": "admin", "age": 25}}
        assert self.engine.evaluate_filters(filters, context) is True

    def test_evaluate_multiple_filters_one_fails(self):
        """Test evaluating multiple filters (AND logic) - one fails."""
        filters = [
            Filter(prop="user.role", op=FilterOperator.EQ, value="admin"),
            Filter(prop="user.age", op=FilterOperator.GTE, value=18),
        ]
        context = {"user": {"role": "admin", "age": 15}}
        assert self.engine.evaluate_filters(filters, context) is False

    def test_evaluate_empty_filters_list(self):
        """Test evaluating empty filters list (should return True)."""
        assert self.engine.evaluate_filters([], {"user": {}}) is True


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Setup test instance."""
        self.engine = FilterEngine()

    def test_null_left_operand(self):
        """Test comparison with null left operand."""
        filter_cond = Filter(prop="user.missing", op=FilterOperator.EQ, value="test")
        context = {"user": {"id": "user1"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_type_mismatch_in_comparison(self):
        """Test comparison with type mismatch."""
        filter_cond = Filter(
            prop="user.age", op=FilterOperator.GT, value="not a number"
        )
        context = {"user": {"age": 25}}
        # Should handle gracefully and return False
        assert self.engine.evaluate_filter(filter_cond, context) is False

    def test_invalid_property_path(self):
        """Test with invalid property path."""
        filter_cond = Filter(prop="", op=FilterOperator.EQ, value="test")
        context = {"user": {"id": "user1"}}
        assert self.engine.evaluate_filter(filter_cond, context) is False
