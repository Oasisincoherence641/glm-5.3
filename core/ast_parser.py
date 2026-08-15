"""
Abstract Syntax Tree (AST) parsing utilities for Python source analysis.
"""

import ast
from typing import List, Optional


class ASTMapExtractor(ast.NodeVisitor):
    """
    Traverses Python AST nodes to extract architectural signatures 
    such as classes, functions, and async methods.
    """

    def __init__(self) -> None:
        self.structure: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Record class declarations and recursively inspect members."""
        self.structure.append(f"Class: {node.name} (Line {node.lineno})")
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Record synchronous function definitions."""
        self.structure.append(f"Function: {node.name}() (Line {node.lineno})")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Record asynchronous function definitions."""
        self.structure.append(f"Async Function: {node.name}() (Line {node.lineno})")
        self.generic_visit(node)


def parse_python_ast(content: str) -> Optional[List[str]]:
    """
    Safely parses Python source string and returns a list of structural elements.
    Returns None if parsing fails due to syntax errors.
    """
    try:
        tree = ast.parse(content)
        visitor = ASTMapExtractor()
        visitor.visit(tree)
        return visitor.structure
    except Exception:
        # Silently fail on invalid syntax or non-python code
        return None
