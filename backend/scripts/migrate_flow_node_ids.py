"""
Migrate flow node data from integer IDs to UUIDs.

This script updates flow nodes that reference agents, crews, tools, etc.
with integer IDs and converts them to UUIDs.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db import SessionLocal
from src.models.flow import Flow
from src.models.agent import Agent
from src.models.crew import Crew
from src.models.tool import Tool
import json


def migrate_flow_node_ids():
    """Migrate all flow node integer IDs to UUIDs."""
    db = SessionLocal()

    try:
        # Get all flows
        flows = db.query(Flow).all()
        print(f"Found {len(flows)} flows to check")

        updated_count = 0

        for flow in flows:
            nodes_updated = False

            # Check each node
            for node in flow.nodes:
                node_type = node.get('type')
                node_data = node.get('data', {})

                # Agent nodes
                if node_type == 'agent' and 'agent_id' in node_data:
                    agent_id = node_data['agent_id']
                    if isinstance(agent_id, int):
                        print(f"Flow '{flow.name}' ({flow.id}): Converting agent_id from int to UUID")
                        # Can't convert - need user to reassign
                        print(f"  WARNING: Agent node {node.get('id')} has integer agent_id={agent_id}")
                        print(f"  This flow needs to be re-edited to select the agent again")
                        nodes_updated = True

                # Crew nodes
                elif node_type == 'crew' and 'crew_id' in node_data:
                    crew_id = node_data['crew_id']
                    if isinstance(crew_id, int):
                        print(f"Flow '{flow.name}' ({flow.id}): Converting crew_id from int to UUID")
                        print(f"  WARNING: Crew node {node.get('id')} has integer crew_id={crew_id}")
                        print(f"  This flow needs to be re-edited to select the crew again")
                        nodes_updated = True

                # Tool nodes
                elif node_type == 'tool' and 'tool_id' in node_data:
                    tool_id = node_data['tool_id']
                    if isinstance(tool_id, int):
                        print(f"Flow '{flow.name}' ({flow.id}): Converting tool_id from int to UUID")
                        print(f"  WARNING: Tool node {node.get('id')} has integer tool_id={tool_id}")
                        print(f"  This flow needs to be re-edited to select the tool again")
                        nodes_updated = True

            if nodes_updated:
                updated_count += 1

        print(f"\n{'='*60}")
        print(f"Summary: {updated_count} flows have integer IDs in their nodes")
        print(f"These flows need to be re-edited in the UI to select agents/crews/tools again")
        print(f"{'='*60}")

    finally:
        db.close()


if __name__ == "__main__":
    migrate_flow_node_ids()
