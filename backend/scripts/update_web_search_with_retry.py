#!/usr/bin/env python3
"""Update Web Search tool with retry logic and rate limit handling."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db.postgres import SessionLocal
from src.models.tool import Tool


def update_web_search_tool():
    """Update Web Search tool with retry logic."""
    db = SessionLocal()

    try:
        print("\n🔍 Updating Web Search tool with retry logic...")

        # Find Web Search tool
        web_search = db.query(Tool).filter(Tool.name == "Web Search").first()

        if not web_search:
            print("❌ Web Search tool not found")
            return

        # Update with retry logic and rate limit handling
        web_search.code = """
def search_web(query: str, max_results: int = 5) -> str:
    \"\"\"Search the web using DuckDuckGo with retry logic.

    Args:
        query: Search query
        max_results: Maximum number of results to return (default: 5)

    Returns:
        Formatted search results as string
    \"\"\"
    import time

    try:
        from duckduckgo_search import DDGS

        results = []
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(query, max_results=max_results))

                    for i, result in enumerate(search_results, 1):
                        title = result.get('title', 'No title')
                        body = result.get('body', 'No description')
                        link = result.get('href', 'No link')

                        results.append(f"{i}. {title}\\n   {body}\\n   URL: {link}\\n")

                    break  # Success - exit retry loop

            except Exception as e:
                if 'Ratelimit' in str(e) and attempt < max_retries - 1:
                    # Rate limited - wait and retry
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                elif attempt == max_retries - 1:
                    # Last attempt failed
                    return f"Search failed after {max_retries} attempts. DuckDuckGo may be rate limiting. Please try again in a few minutes.\\n\\nError: {str(e)}"
                else:
                    raise

        if not results:
            return f"No results found for: {query}"

        return f"Search results for '{query}':\\n\\n" + "\\n".join(results)

    except Exception as e:
        return f"Error performing web search: {str(e)}\\n\\nNote: If you're seeing rate limit errors, please wait a few minutes before trying again."
"""

        db.commit()
        print(f"✅ Updated Web Search tool with retry logic (ID: {web_search.id})")

    except Exception as e:
        print(f"\n❌ Update failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    update_web_search_tool()
