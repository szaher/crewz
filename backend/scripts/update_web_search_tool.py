#!/usr/bin/env python3
"""Update Web Search tool with working DuckDuckGo implementation."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.postgres import SessionLocal
from src.models.tool import Tool


def update_web_search_tool():
    """Update Web Search tool with DuckDuckGo implementation."""
    db = SessionLocal()

    try:
        print("\n🔍 Updating Web Search tool...")

        # Find Web Search tool
        web_search = db.query(Tool).filter(Tool.name == "Web Search").first()

        if not web_search:
            print("❌ Web Search tool not found")
            return

        # Update with working DuckDuckGo implementation
        web_search.code = """
def search_web(query: str, max_results: int = 5) -> str:
    \"\"\"Search the web using DuckDuckGo.

    Args:
        query: Search query
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results as string
    \"\"\"
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results))

            for i, result in enumerate(search_results, 1):
                title = result.get('title', 'No title')
                body = result.get('body', 'No description')
                link = result.get('href', 'No link')

                results.append(f"{i}. {title}\\n   {body}\\n   URL: {link}\\n")

        if not results:
            return f"No results found for: {query}"

        return f"Search results for '{query}':\\n\\n" + "\\n".join(results)

    except Exception as e:
        return f"Error performing web search: {str(e)}"
"""

        web_search.description = "Search the web using DuckDuckGo - no API key required"
        web_search.tool_type = "custom"
        web_search.schema = {
            "input": {
                "query": "string (required) - The search query",
                "max_results": "integer (optional) - Maximum results (default: 5)"
            },
            "output": {
                "results": "string - Formatted search results"
            }
        }

        db.commit()
        print(f"✅ Updated Web Search tool (ID: {web_search.id})")
        print(f"   Type: {web_search.tool_type}")
        print(f"   Has code: {bool(web_search.code)}")
        print(f"   Description: {web_search.description}")

    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_web_search_tool()
