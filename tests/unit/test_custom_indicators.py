"""
Unit tests for custom indicator builder.

Tests for:
- Formula parsing
- Formula validation
- Formula evaluation
- Custom indicator building
"""
import pytest
import numpy as np
from src.intelligence.custom_indicator_builder import (
    FormulaParser, FormulaValidator, FormulaEvaluator, CustomIndicatorBuilder
)
from src.intelligence.indicator_registry import IndicatorRegistry


class TestFormulaParser:
    """Test formula parsing."""

    def test_parse_simple_number(self):
        """Test parsing a simple number."""
        parser = FormulaParser("42")
        ast = parser.parse()
        assert ast["type"] == "number"
        assert ast["value"] == 42.0

    def test_parse_variable(self):
        """Test parsing a variable."""
        parser = FormulaParser("EMA_20")
        ast = parser.parse()
        assert ast["type"] == "variable"
        assert ast["name"] == "EMA_20"

    def test_parse_binary_operation(self):
        """Test parsing binary operations."""
        parser = FormulaParser("EMA_20 + RSI_14")
        ast = parser.parse()
        assert ast["type"] == "binary_op"
        assert ast["op"] == "+"
        assert ast["left"]["name"] == "EMA_20"
        assert ast["right"]["name"] == "RSI_14"

    def test_parse_function_call(self):
        """Test parsing function calls."""
        parser = FormulaParser("max(EMA_20, RSI_14)")
        ast = parser.parse()
        assert ast["type"] == "function_call"
        assert ast["name"] == "max"
        assert len(ast["args"]) == 2

    def test_parse_if_expression(self):
        """Test parsing IF expressions."""
        parser = FormulaParser("IF RSI_14 > 70 THEN 1 ELSE 0")
        ast = parser.parse()
        assert ast["type"] == "if_expr"
        assert ast["condition"]["type"] == "binary_op"
        assert ast["condition"]["op"] == ">"

    def test_parse_previous_value(self):
        """Test parsing previous value references."""
        parser = FormulaParser("EMA_20[t-1]")
        ast = parser.parse()
        assert ast["type"] == "previous_value"
        assert ast["name"] == "EMA_20"

    def test_parse_complex_formula(self):
        """Test parsing complex formulas."""
        parser = FormulaParser("(EMA_20 - EMA_50) / ATR_14")
        ast = parser.parse()
        assert ast["type"] == "binary_op"
        assert ast["op"] == "/"


class TestFormulaValidator:
    """Test formula validation."""

    def test_validate_simple_formula(self):
        """Test validating simple formulas."""
        registry = IndicatorRegistry()
        validator = FormulaValidator(registry)
        
        parser = FormulaParser("EMA_20 + RSI_14")
        ast = parser.parse()
        
        assert validator.validate(ast)

    def test_validate_unknown_variable(self):
        """Test validation fails for unknown variables."""
        registry = IndicatorRegistry()
        validator = FormulaValidator(registry)
        
        parser = FormulaParser("UNKNOWN_VAR + RSI_14")
        ast = parser.parse()
        
        assert not validator.validate(ast)

    def test_validate_function_call(self):
        """Test validating function calls."""
        registry = IndicatorRegistry()
        validator = FormulaValidator(registry)
        
        parser = FormulaParser("max(EMA_20, RSI_14)")
        ast = parser.parse()
        
        assert validator.validate(ast)

    def test_validate_if_expression(self):
        """Test validating IF expressions."""
        registry = IndicatorRegistry()
        validator = FormulaValidator(registry)
        
        parser = FormulaParser("IF RSI_14 > 70 THEN EMA_20 ELSE EMA_50")
        ast = parser.parse()
        
        assert validator.validate(ast)


class TestFormulaEvaluator:
    """Test formula evaluation."""

    def test_evaluate_number(self):
        """Test evaluating numbers."""
        evaluator = FormulaEvaluator({})
        ast = {"type": "number", "value": 42.0}
        result = evaluator.evaluate(ast)
        assert result == 42.0

    def test_evaluate_variable(self):
        """Test evaluating variables."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        evaluator = FormulaEvaluator({"X": data})
        ast = {"type": "variable", "name": "X"}
        result = evaluator.evaluate(ast)
        assert np.array_equal(result, data)

    def test_evaluate_addition(self):
        """Test evaluating addition."""
        data1 = np.array([1.0, 2.0, 3.0])
        data2 = np.array([4.0, 5.0, 6.0])
        evaluator = FormulaEvaluator({"X": data1, "Y": data2})
        
        ast = {
            "type": "binary_op",
            "op": "+",
            "left": {"type": "variable", "name": "X"},
            "right": {"type": "variable", "name": "Y"},
        }
        
        result = evaluator.evaluate(ast)
        expected = np.array([5.0, 7.0, 9.0])
        assert np.array_equal(result, expected)

    def test_evaluate_function(self):
        """Test evaluating functions."""
        data1 = np.array([1.0, 5.0, 3.0])
        data2 = np.array([4.0, 2.0, 6.0])
        evaluator = FormulaEvaluator({"X": data1, "Y": data2})
        
        ast = {
            "type": "function_call",
            "name": "max",
            "args": [
                {"type": "variable", "name": "X"},
                {"type": "variable", "name": "Y"},
            ],
        }
        
        result = evaluator.evaluate(ast)
        expected = np.array([4.0, 5.0, 6.0])
        assert np.array_equal(result, expected)

    def test_evaluate_if_expression(self):
        """Test evaluating IF expressions."""
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        evaluator = FormulaEvaluator({"X": data})
        
        ast = {
            "type": "if_expr",
            "condition": {
                "type": "binary_op",
                "op": ">",
                "left": {"type": "variable", "name": "X"},
                "right": {"type": "number", "value": 2.5},
            },
            "then": {"type": "number", "value": 1.0},
            "else": {"type": "number", "value": 0.0},
        }
        
        result = evaluator.evaluate(ast)
        expected = np.array([0.0, 0.0, 1.0, 1.0, 1.0])
        assert np.array_equal(result, expected)


class TestCustomIndicatorBuilder:
    """Test custom indicator builder."""

    def test_builder_initialization(self):
        """Test builder initialization."""
        registry = IndicatorRegistry()
        builder = CustomIndicatorBuilder(registry)
        assert builder.registry is not None

    def test_build_simple_indicator(self):
        """Test building a simple custom indicator."""
        registry = IndicatorRegistry()
        builder = CustomIndicatorBuilder(registry)
        
        # Create sample data
        ema_20 = np.array([100.0, 101.0, 102.0, 103.0, 104.0])
        rsi_14 = np.array([50.0, 55.0, 60.0, 65.0, 70.0])
        
        indicators = {"EMA_20": ema_20, "RSI_14": rsi_14}
        
        # Build custom indicator
        result = builder.build("EMA_20 + RSI_14", indicators)
        
        expected = np.array([150.0, 156.0, 162.0, 168.0, 174.0])
        assert np.array_equal(result, expected)

    def test_build_with_function(self):
        """Test building indicator with functions."""
        registry = IndicatorRegistry()
        builder = CustomIndicatorBuilder(registry)
        
        ema_20 = np.array([100.0, 101.0, 102.0])
        rsi_14 = np.array([50.0, 55.0, 60.0])
        
        indicators = {"EMA_20": ema_20, "RSI_14": rsi_14}
        
        result = builder.build("max(EMA_20, RSI_14)", indicators)
        
        expected = np.array([100.0, 101.0, 102.0])
        assert np.array_equal(result, expected)

    def test_build_with_if_expression(self):
        """Test building indicator with IF expressions."""
        registry = IndicatorRegistry()
        builder = CustomIndicatorBuilder(registry)
        
        rsi_14 = np.array([30.0, 50.0, 70.0, 80.0, 90.0])
        
        indicators = {"RSI_14": rsi_14}
        
        result = builder.build("IF RSI_14 > 70 THEN 1 ELSE 0", indicators)
        
        expected = np.array([0.0, 0.0, 1.0, 1.0, 1.0])
        assert np.array_equal(result, expected)

    def test_save_and_load_template(self):
        """Test saving and loading templates."""
        registry = IndicatorRegistry()
        builder = CustomIndicatorBuilder(registry)
        
        formula = "EMA_20 + RSI_14"
        builder.save_template("my_indicator", formula)
        
        loaded = builder.load_template("my_indicator")
        assert loaded == formula

    def test_list_templates(self):
        """Test listing templates."""
        registry = IndicatorRegistry()
        builder = CustomIndicatorBuilder(registry)
        
        builder.save_template("template1", "EMA_20 + RSI_14")
        builder.save_template("template2", "max(EMA_20, RSI_14)")
        
        templates = builder.list_templates()
        assert "template1" in templates
        assert "template2" in templates
        assert len(templates) == 2

    def test_invalid_formula(self):
        """Test that invalid formulas raise errors."""
        registry = IndicatorRegistry()
        builder = CustomIndicatorBuilder(registry)
        
        ema_20 = np.array([100.0, 101.0, 102.0])
        indicators = {"EMA_20": ema_20}
        
        with pytest.raises(ValueError):
            builder.build("UNKNOWN_VAR + EMA_20", indicators)
