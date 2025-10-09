#!/usr/bin/env python3
"""Migrate builtin tools to custom tools with implementations."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.postgres import SessionLocal
from src.models.tool import Tool


def migrate_tools():
    """Migrate builtin tools to custom tools."""
    db = SessionLocal()

    try:
        print("\n🔄 Migrating builtin tools to custom tools...")

        # Tool implementations
        tool_implementations = {
            "Web Search": """
def search_web(query: str) -> str:
    \"\"\"Search the web for information.\"\"\"
    # Placeholder implementation
    # In production, integrate with a search API like DuckDuckGo, Google, or Serper
    return f"Search results for: {query}\\n[Placeholder - configure search API]"
""",
            "File Reader": """
def read_file(file_path: str) -> str:
    \"\"\"Read file contents.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
""",
            "Calculator": """
def calculate(expression: str) -> str:
    \"\"\"Safely evaluate a mathematical expression.\"\"\"
    try:
        import ast
        import operator

        # Define safe operations
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }

        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](eval_expr(node.operand))
            else:
                raise TypeError(node)

        result = eval_expr(ast.parse(expression, mode='eval').body)
        return str(result)
    except Exception as e:
        return f"Error calculating: {str(e)}"
"""
        }

        # Find all builtin tools
        builtin_tools = db.query(Tool).filter(Tool.tool_type == "builtin").all()

        if not builtin_tools:
            print("✅ No builtin tools found - nothing to migrate")
            return

        print(f"Found {len(builtin_tools)} builtin tools to migrate:")

        migrated = 0
        for tool in builtin_tools:
            print(f"  - {tool.name} (ID: {tool.id})")

            # Update to custom type
            tool.tool_type = "custom"

            # Add implementation code if available
            if tool.name in tool_implementations:
                tool.code = tool_implementations[tool.name]
                print(f"    ✓ Added implementation code")
            else:
                # Generic placeholder
                tool.code = f"""
def {tool.name.lower().replace(' ', '_')}(input_data: str) -> str:
    \"\"\"Placeholder implementation for {tool.name}.\"\"\"
    return f"{{tool.name}} executed with input: {{input_data}}"
"""
                print(f"    ⚠ Added placeholder code (implement actual logic)")

            migrated += 1

        db.commit()
        print(f"\n✅ Successfully migrated {migrated} tools from builtin to custom")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_tools()
