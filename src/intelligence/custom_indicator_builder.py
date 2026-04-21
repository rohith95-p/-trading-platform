"""
Custom Indicator Builder for creating user-defined indicators.

Supports formula parsing, validation, and evaluation with mathematical operations,
conditional logic, and previous value references.
"""
import logging
import re
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import numpy as np

log = logging.getLogger(__name__)


class TokenType(Enum):
    """Token types for formula parsing."""
    NUMBER = "NUMBER"
    IDENTIFIER = "IDENTIFIER"
    OPERATOR = "OPERATOR"
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    COMMA = "COMMA"
    FUNCTION = "FUNCTION"
    KEYWORD = "KEYWORD"
    EOF = "EOF"


class Token:
    """Represents a token in the formula."""
    
    def __init__(self, type_: TokenType, value: str, position: int = 0):
        self.type = type_
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type.value}, {self.value})"


class FormulaParser:
    """Parses custom indicator formulas into AST."""
    
    OPERATORS = {"+", "-", "*", "/", "==", "!=", "<", ">", "<=", ">=", "AND", "OR", "NOT"}
    FUNCTIONS = {"min", "max", "average", "sum", "abs", "sqrt", "log", "exp"}
    KEYWORDS = {"IF", "THEN", "ELSE", "AND", "OR", "NOT"}
    
    def __init__(self, formula: str):
        self.formula = formula
        self.tokens: List[Token] = []
        self.position = 0
    
    def tokenize(self) -> List[Token]:
        """Tokenize the formula."""
        self.tokens = []
        i = 0
        
        while i < len(self.formula):
            # Skip whitespace
            if self.formula[i].isspace():
                i += 1
                continue
            
            # Numbers
            if self.formula[i].isdigit() or (self.formula[i] == "." and i + 1 < len(self.formula) and self.formula[i + 1].isdigit()):
                j = i
                while j < len(self.formula) and (self.formula[j].isdigit() or self.formula[j] == "."):
                    j += 1
                self.tokens.append(Token(TokenType.NUMBER, self.formula[i:j], i))
                i = j
                continue
            
            # Identifiers and keywords
            if self.formula[i].isalpha() or self.formula[i] == "_":
                j = i
                while j < len(self.formula) and (self.formula[j].isalnum() or self.formula[j] == "_"):
                    j += 1
                word = self.formula[i:j]
                
                if word.upper() in self.KEYWORDS:
                    self.tokens.append(Token(TokenType.KEYWORD, word.upper(), i))
                elif word in self.FUNCTIONS:
                    self.tokens.append(Token(TokenType.FUNCTION, word, i))
                else:
                    self.tokens.append(Token(TokenType.IDENTIFIER, word, i))
                i = j
                continue
            
            # Operators
            if i + 1 < len(self.formula) and self.formula[i:i+2] in {"==", "!=", "<=", ">="}:
                self.tokens.append(Token(TokenType.OPERATOR, self.formula[i:i+2], i))
                i += 2
                continue
            
            if self.formula[i] in {"+", "-", "*", "/", "<", ">"}:
                self.tokens.append(Token(TokenType.OPERATOR, self.formula[i], i))
                i += 1
                continue
            
            # Parentheses
            if self.formula[i] == "(":
                self.tokens.append(Token(TokenType.LPAREN, "(", i))
                i += 1
                continue
            
            if self.formula[i] == ")":
                self.tokens.append(Token(TokenType.RPAREN, ")", i))
                i += 1
                continue
            
            # Brackets
            if self.formula[i] == "[":
                self.tokens.append(Token(TokenType.LBRACKET, "[", i))
                i += 1
                continue
            
            if self.formula[i] == "]":
                self.tokens.append(Token(TokenType.RBRACKET, "]", i))
                i += 1
                continue
            
            # Comma
            if self.formula[i] == ",":
                self.tokens.append(Token(TokenType.COMMA, ",", i))
                i += 1
                continue
            
            # Unknown character
            raise ValueError(f"Unknown character '{self.formula[i]}' at position {i}")
        
        self.tokens.append(Token(TokenType.EOF, "", len(self.formula)))
        return self.tokens
    
    def parse(self) -> Dict[str, Any]:
        """Parse formula into AST."""
        self.tokenize()
        self.position = 0
        ast = self._parse_expression()
        
        if self.position < len(self.tokens) - 1:
            raise ValueError(f"Unexpected token at position {self.position}")
        
        return ast
    
    def _parse_expression(self) -> Dict[str, Any]:
        """Parse an expression."""
        return self._parse_or()
    
    def _parse_or(self) -> Dict[str, Any]:
        """Parse OR expression."""
        left = self._parse_and()
        
        while self.position < len(self.tokens) and self.tokens[self.position].value == "OR":
            self.position += 1
            right = self._parse_and()
            left = {"type": "binary_op", "op": "OR", "left": left, "right": right}
        
        return left
    
    def _parse_and(self) -> Dict[str, Any]:
        """Parse AND expression."""
        left = self._parse_comparison()
        
        while self.position < len(self.tokens) and self.tokens[self.position].value == "AND":
            self.position += 1
            right = self._parse_comparison()
            left = {"type": "binary_op", "op": "AND", "left": left, "right": right}
        
        return left
    
    def _parse_comparison(self) -> Dict[str, Any]:
        """Parse comparison expression."""
        left = self._parse_additive()
        
        if self.position < len(self.tokens) and self.tokens[self.position].type == TokenType.OPERATOR:
            op = self.tokens[self.position].value
            if op in {"==", "!=", "<", ">", "<=", ">="}:
                self.position += 1
                right = self._parse_additive()
                return {"type": "binary_op", "op": op, "left": left, "right": right}
        
        return left
    
    def _parse_additive(self) -> Dict[str, Any]:
        """Parse addition/subtraction."""
        left = self._parse_multiplicative()
        
        while self.position < len(self.tokens) and self.tokens[self.position].value in {"+", "-"}:
            op = self.tokens[self.position].value
            self.position += 1
            right = self._parse_multiplicative()
            left = {"type": "binary_op", "op": op, "left": left, "right": right}
        
        return left
    
    def _parse_multiplicative(self) -> Dict[str, Any]:
        """Parse multiplication/division."""
        left = self._parse_unary()
        
        while self.position < len(self.tokens) and self.tokens[self.position].value in {"*", "/"}:
            op = self.tokens[self.position].value
            self.position += 1
            right = self._parse_unary()
            left = {"type": "binary_op", "op": op, "left": left, "right": right}
        
        return left
    
    def _parse_unary(self) -> Dict[str, Any]:
        """Parse unary expression."""
        if self.position < len(self.tokens) and self.tokens[self.position].value == "NOT":
            self.position += 1
            operand = self._parse_unary()
            return {"type": "unary_op", "op": "NOT", "operand": operand}
        
        return self._parse_primary()
    
    def _parse_primary(self) -> Dict[str, Any]:
        """Parse primary expression."""
        token = self.tokens[self.position]
        
        # Number
        if token.type == TokenType.NUMBER:
            self.position += 1
            return {"type": "number", "value": float(token.value)}
        
        # Identifier (variable or previous value reference)
        if token.type == TokenType.IDENTIFIER:
            name = token.value
            self.position += 1
            
            # Check for previous value reference (e.g., EMA_20[t-1])
            if self.position < len(self.tokens) and self.tokens[self.position].type == TokenType.LBRACKET:
                self.position += 1
                offset = self._parse_expression()
                if self.position < len(self.tokens) and self.tokens[self.position].type == TokenType.RBRACKET:
                    self.position += 1
                    return {"type": "previous_value", "name": name, "offset": offset}
                else:
                    raise ValueError("Expected ]")
            
            return {"type": "variable", "name": name}
        
        # Function call
        if token.type == TokenType.FUNCTION:
            func_name = token.value
            self.position += 1
            
            if self.position < len(self.tokens) and self.tokens[self.position].type == TokenType.LPAREN:
                self.position += 1
                args = []
                
                while self.position < len(self.tokens) and self.tokens[self.position].type != TokenType.RPAREN:
                    args.append(self._parse_expression())
                    
                    if self.position < len(self.tokens) and self.tokens[self.position].type == TokenType.COMMA:
                        self.position += 1
                
                if self.position < len(self.tokens) and self.tokens[self.position].type == TokenType.RPAREN:
                    self.position += 1
                    return {"type": "function_call", "name": func_name, "args": args}
                else:
                    raise ValueError("Expected )")
            else:
                raise ValueError(f"Expected ( after function {func_name}")
        
        # IF expression
        if token.type == TokenType.KEYWORD and token.value == "IF":
            self.position += 1
            condition = self._parse_expression()
            
            if self.position < len(self.tokens) and self.tokens[self.position].value == "THEN":
                self.position += 1
                then_expr = self._parse_expression()
                
                else_expr = None
                if self.position < len(self.tokens) and self.tokens[self.position].value == "ELSE":
                    self.position += 1
                    else_expr = self._parse_expression()
                
                return {"type": "if_expr", "condition": condition, "then": then_expr, "else": else_expr}
            else:
                raise ValueError("Expected THEN after IF condition")
        
        # Parenthesized expression
        if token.type == TokenType.LPAREN:
            self.position += 1
            expr = self._parse_expression()
            
            if self.position < len(self.tokens) and self.tokens[self.position].type == TokenType.RPAREN:
                self.position += 1
                return expr
            else:
                raise ValueError("Expected )")
        
        raise ValueError(f"Unexpected token: {token}")


class FormulaValidator:
    """Validates custom indicator formulas."""
    
    def __init__(self, indicator_registry):
        self.registry = indicator_registry
    
    def validate(self, ast: Dict[str, Any], available_variables: Optional[List[str]] = None) -> bool:
        """Validate AST.
        
        Args:
            ast: Abstract syntax tree
            available_variables: List of available variable names
        
        Returns:
            True if valid
        """
        if available_variables is None:
            available_variables = self.registry.get_available_indicators()
        
        return self._validate_node(ast, available_variables)
    
    def _validate_node(self, node: Dict[str, Any], available_variables: List[str]) -> bool:
        """Validate a single AST node."""
        node_type = node.get("type")
        
        if node_type == "number":
            return True
        
        elif node_type == "variable":
            name = node.get("name")
            return name in available_variables
        
        elif node_type == "previous_value":
            name = node.get("name")
            return name in available_variables
        
        elif node_type == "binary_op":
            left = self._validate_node(node.get("left"), available_variables)
            right = self._validate_node(node.get("right"), available_variables)
            return left and right
        
        elif node_type == "unary_op":
            operand = self._validate_node(node.get("operand"), available_variables)
            return operand
        
        elif node_type == "function_call":
            func_name = node.get("name")
            if func_name not in {"min", "max", "average", "sum", "abs", "sqrt", "log", "exp"}:
                return False
            
            args = node.get("args", [])
            return all(self._validate_node(arg, available_variables) for arg in args)
        
        elif node_type == "if_expr":
            condition = self._validate_node(node.get("condition"), available_variables)
            then_expr = self._validate_node(node.get("then"), available_variables)
            else_expr = node.get("else")
            
            if else_expr:
                return condition and then_expr and self._validate_node(else_expr, available_variables)
            else:
                return condition and then_expr
        
        return False


class FormulaEvaluator:
    """Evaluates custom indicator formulas."""
    
    def __init__(self, variables: Dict[str, np.ndarray]):
        """Initialize evaluator.
        
        Args:
            variables: Dict mapping variable names to numpy arrays
        """
        self.variables = variables
    
    def evaluate(self, ast: Dict[str, Any]) -> np.ndarray:
        """Evaluate AST and return result array.
        
        Args:
            ast: Abstract syntax tree
        
        Returns:
            Numpy array of computed values
        """
        return self._evaluate_node(ast)
    
    def _evaluate_node(self, node: Dict[str, Any]) -> Union[np.ndarray, float, bool]:
        """Evaluate a single AST node."""
        node_type = node.get("type")
        
        if node_type == "number":
            return node.get("value")
        
        elif node_type == "variable":
            name = node.get("name")
            if name not in self.variables:
                raise ValueError(f"Unknown variable: {name}")
            return self.variables[name]
        
        elif node_type == "previous_value":
            name = node.get("name")
            offset_node = node.get("offset")
            offset = self._evaluate_node(offset_node)
            
            if name not in self.variables:
                raise ValueError(f"Unknown variable: {name}")
            
            array = self.variables[name]
            
            # Handle offset (e.g., t-1)
            if isinstance(offset, (int, float)):
                offset = int(offset)
                if offset == 0:
                    return array
                elif offset < 0:
                    # Shift array forward
                    result = np.full_like(array, np.nan)
                    result[-offset:] = array[:offset]
                    return result
                else:
                    # Shift array backward
                    result = np.full_like(array, np.nan)
                    result[:-offset] = array[offset:]
                    return result
            else:
                raise ValueError(f"Invalid offset: {offset}")
        
        elif node_type == "binary_op":
            left = self._evaluate_node(node.get("left"))
            right = self._evaluate_node(node.get("right"))
            op = node.get("op")
            
            if op == "+":
                return left + right
            elif op == "-":
                return left - right
            elif op == "*":
                return left * right
            elif op == "/":
                return np.divide(left, right, where=right != 0, out=np.full_like(left, np.nan))
            elif op == "==":
                return left == right
            elif op == "!=":
                return left != right
            elif op == "<":
                return left < right
            elif op == ">":
                return left > right
            elif op == "<=":
                return left <= right
            elif op == ">=":
                return left >= right
            elif op == "AND":
                return left & right
            elif op == "OR":
                return left | right
            else:
                raise ValueError(f"Unknown operator: {op}")
        
        elif node_type == "unary_op":
            operand = self._evaluate_node(node.get("operand"))
            op = node.get("op")
            
            if op == "NOT":
                return ~operand
            else:
                raise ValueError(f"Unknown unary operator: {op}")
        
        elif node_type == "function_call":
            func_name = node.get("name")
            args = [self._evaluate_node(arg) for arg in node.get("args", [])]
            
            if func_name == "min":
                return np.minimum.reduce(args)
            elif func_name == "max":
                return np.maximum.reduce(args)
            elif func_name == "average":
                return np.mean(args, axis=0)
            elif func_name == "sum":
                return np.sum(args, axis=0)
            elif func_name == "abs":
                return np.abs(args[0])
            elif func_name == "sqrt":
                return np.sqrt(args[0])
            elif func_name == "log":
                return np.log(args[0])
            elif func_name == "exp":
                return np.exp(args[0])
            else:
                raise ValueError(f"Unknown function: {func_name}")
        
        elif node_type == "if_expr":
            condition = self._evaluate_node(node.get("condition"))
            then_expr = self._evaluate_node(node.get("then"))
            else_expr = node.get("else")
            
            if else_expr:
                else_result = self._evaluate_node(else_expr)
                return np.where(condition, then_expr, else_result)
            else:
                return np.where(condition, then_expr, np.nan)
        
        raise ValueError(f"Unknown node type: {node_type}")


class CustomIndicatorBuilder:
    """Builds custom indicators from formulas."""
    
    def __init__(self, indicator_registry):
        self.registry = indicator_registry
        self.parser = FormulaParser("")
        self.validator = FormulaValidator(indicator_registry)
        self.templates: Dict[str, str] = {}
    
    def build(self, formula: str, indicators: Dict[str, np.ndarray]) -> np.ndarray:
        """Build custom indicator from formula.
        
        Args:
            formula: Formula string (e.g., "EMA_20 + RSI_14")
            indicators: Dict mapping indicator names to numpy arrays
        
        Returns:
            Computed indicator values
        """
        # Parse formula
        parser = FormulaParser(formula)
        ast = parser.parse()
        
        # Validate
        available_vars = list(indicators.keys())
        if not self.validator.validate(ast, available_vars):
            raise ValueError(f"Invalid formula: {formula}")
        
        # Evaluate
        evaluator = FormulaEvaluator(indicators)
        result = evaluator.evaluate(ast)
        
        if isinstance(result, np.ndarray):
            return result
        else:
            return np.full(len(next(iter(indicators.values()))), result)
    
    def save_template(self, name: str, formula: str) -> None:
        """Save custom indicator as template.
        
        Args:
            name: Template name
            formula: Formula string
        """
        self.templates[name] = formula
        log.info(f"Saved template: {name}")
    
    def load_template(self, name: str) -> str:
        """Load custom indicator template.
        
        Args:
            name: Template name
        
        Returns:
            Formula string
        """
        if name not in self.templates:
            raise ValueError(f"Unknown template: {name}")
        return self.templates[name]
    
    def list_templates(self) -> List[str]:
        """List all saved templates."""
        return list(self.templates.keys())
