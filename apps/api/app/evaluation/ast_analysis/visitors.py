"""
AST Visitors for Concept Detection in Python Source Code
Each visitor inspects the Python AST to collect structural evidence for evaluation rules.
"""

import ast
from typing import Any, Dict, List, Optional, Set


class BaseConceptVisitor(ast.NodeVisitor):
    """Base class for concept visitors, equipped with source code slice capabilities."""

    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.matches: List[Dict[str, Any]] = []

    def get_snippet(self, node: ast.AST) -> str:
        """Extract source code snippet corresponding to the AST node."""
        if hasattr(node, "lineno"):
            line_idx = node.lineno - 1
            if 0 <= line_idx < len(self.source_lines):
                return self.source_lines[line_idx].strip()
        return ""


class LoopVisitor(BaseConceptVisitor):
    """
    Detects loops (for, while) and analyzes loop nesting and unreachable blocks.
    """

    def __init__(self, source_lines: List[str]):
        super().__init__(source_lines)
        self.loop_stack: List[ast.AST] = []
        self.max_nesting_depth = 0

    def is_inside_obviously_dead_code(self) -> bool:
        """Check if current position is within a known trivial dead branch (e.g. if False:)."""
        # NodeVisitor doesn't track full parents automatically unless we wrap or check
        return False

    def visit_For(self, node: ast.For):
        self.loop_stack.append(node)
        depth = len(self.loop_stack)
        if depth > self.max_nesting_depth:
            self.max_nesting_depth = depth

        target_name = None
        if isinstance(node.target, ast.Name):
            target_name = node.target.id
        elif isinstance(node.target, ast.Tuple):
            target_name = [elt.id for elt in node.target.elts if isinstance(elt, ast.Name)]

        self.matches.append({
            "construct": "for",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "For",
            "nesting_depth": depth,
            "target": target_name,
            "snippet": self.get_snippet(node),
        })

        self.generic_visit(node)
        self.loop_stack.pop()

    def visit_While(self, node: ast.While):
        self.loop_stack.append(node)
        depth = len(self.loop_stack)
        if depth > self.max_nesting_depth:
            self.max_nesting_depth = depth

        self.matches.append({
            "construct": "while",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "While",
            "nesting_depth": depth,
            "snippet": self.get_snippet(node),
        })

        self.generic_visit(node)
        self.loop_stack.pop()


class RecursionVisitor(BaseConceptVisitor):
    """
    Detects function definitions that call themselves (direct recursion)
    and checks for base-case conditional branching.
    """

    def __init__(self, source_lines: List[str]):
        super().__init__(source_lines)
        self.current_function: Optional[str] = None
        self.function_calls: Dict[str, List[ast.Call]] = {}
        self.has_conditional: Dict[str, bool] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self.current_function
        self.current_function = node.name
        self.function_calls[node.name] = []
        self.has_conditional[node.name] = False

        # Scan for conditionals inside function to identify base cases
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.IfExp, getattr(ast, "Match", ()))) and child is not node:
                self.has_conditional[node.name] = True

        self.generic_visit(node)

        # Check if the function made calls to its own name
        recursive_calls = [
            c for c in self.function_calls[node.name]
            if isinstance(c.func, ast.Name) and c.func.id == node.name
        ]

        if recursive_calls:
            self.matches.append({
                "construct": "recursion",
                "function_name": node.name,
                "line": node.lineno,
                "col": node.col_offset,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "end_col": getattr(node, "end_col_offset", node.col_offset),
                "node_type": "FunctionDef",
                "recursive_call_count": len(recursive_calls),
                "has_base_case_conditional": self.has_conditional[node.name],
                "snippet": self.get_snippet(node),
            })

        self.current_function = prev_func

    def visit_Call(self, node: ast.Call):
        if self.current_function:
            self.function_calls[self.current_function].append(node)
        self.generic_visit(node)


class ConditionalVisitor(BaseConceptVisitor):
    """Detects if statements, ternary expressions, and match cases."""

    def visit_If(self, node: ast.If):
        self.matches.append({
            "construct": "if",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "If",
            "has_else": bool(node.orelse),
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp):
        self.matches.append({
            "construct": "ternary",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "IfExp",
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)

    def visit_Match(self, node: Any):
        self.matches.append({
            "construct": "match",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "Match",
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)


class ComprehensionVisitor(BaseConceptVisitor):
    """Detects list, dict, set comprehensions and generator expressions."""

    def visit_ListComp(self, node: ast.ListComp):
        self.matches.append({
            "construct": "list_comprehension",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "ListComp",
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp):
        self.matches.append({
            "construct": "dict_comprehension",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "DictComp",
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp):
        self.matches.append({
            "construct": "set_comprehension",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "SetComp",
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        self.matches.append({
            "construct": "generator_expression",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "GeneratorExp",
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)


class FunctionDefVisitor(BaseConceptVisitor):
    """Detects function definitions and their signatures."""

    def visit_FunctionDef(self, node: ast.FunctionDef):
        arg_names = [arg.arg for arg in node.args.args]
        self.matches.append({
            "construct": "function_def",
            "function_name": node.name,
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "FunctionDef",
            "args": arg_names,
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)


class ExceptionHandlingVisitor(BaseConceptVisitor):
    """Detects try/except blocks and specific exception handling."""

    def visit_Try(self, node: ast.Try):
        handlers = []
        for h in node.handlers:
            exc_name = None
            if isinstance(h.type, ast.Name):
                exc_name = h.type.id
            elif isinstance(h.type, ast.Attribute):
                exc_name = f"{getattr(h.type.value, 'id', '')}.{h.type.attr}"
            handlers.append({
                "exception_type": exc_name,
                "name": h.name,
                "line": h.lineno,
            })

        self.matches.append({
            "construct": "try_except",
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "Try",
            "handlers": handlers,
            "has_finally": bool(node.finalbody),
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)


class ClassDefVisitor(BaseConceptVisitor):
    """Detects class definitions and OOP structure."""

    def visit_ClassDef(self, node: ast.ClassDef):
        bases = []
        for b in node.bases:
            if isinstance(b, ast.Name):
                bases.append(b.id)
            elif isinstance(b, ast.Attribute):
                bases.append(f"{getattr(b.value, 'id', '')}.{b.attr}")

        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]

        self.matches.append({
            "construct": "class_def",
            "class_name": node.name,
            "line": node.lineno,
            "col": node.col_offset,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "end_col": getattr(node, "end_col_offset", node.col_offset),
            "node_type": "ClassDef",
            "bases": bases,
            "methods": methods,
            "has_init": "__init__" in methods,
            "snippet": self.get_snippet(node),
        })
        self.generic_visit(node)


class ProhibitedConstructVisitor(BaseConceptVisitor):
    """
    Checks for forbidden built-ins (e.g. eval, exec), forbidden modules (e.g. os, sys),
    or forbidden constructs (e.g. loops, recursion) according to problem rules.
    """

    def __init__(self, source_lines: List[str], forbidden_targets: Set[str], construct_type: str):
        super().__init__(source_lines)
        self.forbidden_targets = {t.lower() for t in forbidden_targets}
        self.construct_type = construct_type

    def visit_Call(self, node: ast.Call):
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = f"{getattr(node.func.value, 'id', '')}.{node.func.attr}"

        if callee_name and (callee_name.lower() in self.forbidden_targets or "*" in self.forbidden_targets):
            self.matches.append({
                "construct": "prohibited_call",
                "target": callee_name,
                "line": node.lineno,
                "col": node.col_offset,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "end_col": getattr(node, "end_col_offset", node.col_offset),
                "node_type": "Call",
                "snippet": self.get_snippet(node),
            })
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            if alias.name.lower() in self.forbidden_targets or "*" in self.forbidden_targets:
                self.matches.append({
                    "construct": "prohibited_import",
                    "target": alias.name,
                    "line": node.lineno,
                    "col": node.col_offset,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "end_col": getattr(node, "end_col_offset", node.col_offset),
                    "node_type": "Import",
                    "snippet": self.get_snippet(node),
                })
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        mod = node.module or ""
        if mod.lower() in self.forbidden_targets or "*" in self.forbidden_targets:
            self.matches.append({
                "construct": "prohibited_import_from",
                "target": mod,
                "line": node.lineno,
                "col": node.col_offset,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "end_col": getattr(node, "end_col_offset", node.col_offset),
                "node_type": "ImportFrom",
                "snippet": self.get_snippet(node),
            })
        self.generic_visit(node)
