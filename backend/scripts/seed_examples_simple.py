#!/usr/bin/env python3
"""Simple seed script for example flow via API."""

import requests
import json

# Backend API URL
API_BASE = "http://localhost:8000/api/v1"

def create_example_flow():
    """Create an example flow via API."""

    flow_data = {
        "name": "Research to Report Workflow",
        "description": "A complete workflow demonstrating input → processing → output flow",
        "status": "active",
        "version": 1,
        "tags": ["example", "research", "demo"],
        "nodes": [
            # Input Node
            {
                "id": "input-1",
                "type": "input",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Research Topic",
                    "description": "Enter the research topic and parameters",
                    "inputs": [
                        {"name": "topic", "type": "string", "required": True},
                        {"name": "depth", "type": "string", "required": False},
                    ],
                    "width": 300,
                },
            },
            # Agent Node 1
            {
                "id": "agent-1",
                "type": "agent",
                "position": {"x": 100, "y": 280},
                "data": {
                    "label": "Research Phase",
                    "task": "Research the topic: {topic}",
                    "expected_output": "Comprehensive research summary",
                    "width": 280,
                },
            },
            # Condition Node
            {
                "id": "condition-1",
                "type": "condition",
                "position": {"x": 100, "y": 460},
                "data": {
                    "label": "Quality Gate",
                    "condition": "word_count >= 100",
                    "description": "Verify research quality",
                    "width": 260,
                },
            },
            # Agent Node 2
            {
                "id": "agent-2",
                "type": "agent",
                "position": {"x": 400, "y": 460},
                "data": {
                    "label": "Report Writing",
                    "task": "Create a comprehensive report",
                    "expected_output": "Well-formatted report",
                    "width": 280,
                },
            },
            # Output Node
            {
                "id": "output-1",
                "type": "output",
                "position": {"x": 400, "y": 640},
                "data": {
                    "label": "Final Report",
                    "description": "The completed report output",
                    "outputs": [
                        {"name": "report", "type": "string"},
                        {"name": "word_count", "type": "number"},
                    ],
                    "width": 280,
                },
            },
        ],
        "edges": [
            {"id": "edge-1", "source": "input-1", "target": "agent-1", "type": "default"},
            {"id": "edge-2", "source": "agent-1", "target": "condition-1", "type": "default"},
            {"id": "edge-3", "source": "condition-1", "target": "agent-2", "type": "default"},
            {"id": "edge-4", "source": "agent-2", "target": "output-1", "type": "default"},
        ],
    }

    try:
        response = requests.post(f"{API_BASE}/flows", json=flow_data)
        response.raise_for_status()
        flow = response.json()
        print(f"✅ Created example flow: {flow['name']} (ID: {flow['id']})")
        print(f"\n📍 View in UI: http://localhost:3001/flows/{flow['id']}")
        return flow
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating flow: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return None


def main():
    print("\n" + "="*60)
    print("Creating Example Flow")
    print("="*60 + "\n")

    flow = create_example_flow()

    if flow:
        print("\n" + "="*60)
        print("✅ Success!")
        print("="*60)
        print("\nNext steps:")
        print(f"1. Open http://localhost:3001/flows/{flow['id']}")
        print("2. Click 'Execute' to test the flow")
        print("3. Provide input: {'topic': 'AI Safety', 'depth': 'detailed'}")
        print()


if __name__ == "__main__":
    main()
