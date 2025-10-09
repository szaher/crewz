#!/usr/bin/env python3
"""
Seed script to create example flows and crews for testing.

This script creates:
1. Example LLM providers
2. Example tools
3. Example agents
4. Example crew
5. Example flow with complete workflow
"""

import sys
import os

# Add backend src to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(backend_dir, 'src'))

from src.db import SessionLocal
from src.models import Agent, Crew, Flow, Tool, LLMProvider
from src.models.agent import agent_tools
from src.models.crew import crew_agents, CrewProcess
from src.models.flow import FlowStatus


def create_example_llm_providers(db, tenant_id=1):
    """Create example LLM providers."""
    from src.models.llm_provider import LLMProviderType

    providers = [
        {
            "tenant_id": tenant_id,
            "name": "OpenAI GPT-4",
            "provider_type": LLMProviderType.OPENAI,
            "model_name": "gpt-4",
            "api_key": "sk-example-key-replace-with-real",
            "is_active": True,
        },
        {
            "tenant_id": tenant_id,
            "name": "OpenAI GPT-3.5",
            "provider_type": LLMProviderType.OPENAI,
            "model_name": "gpt-3.5-turbo",
            "api_key": "sk-example-key-replace-with-real",
            "is_active": True,
        },
    ]

    created_providers = []
    for prov_data in providers:
        # Check if exists
        existing = db.query(LLMProvider).filter_by(name=prov_data["name"]).first()
        if existing:
            created_providers.append(existing)
            print(f"✓ LLM Provider already exists: {existing.name}")
        else:
            provider = LLMProvider(**prov_data)
            db.add(provider)
            db.flush()
            created_providers.append(provider)
            print(f"✓ Created LLM Provider: {provider.name}")

    return created_providers


def create_example_tools(db):
    """Create example tools."""
    tools_data = [
        {
            "name": "Web Search",
            "description": "Search the web for information using DuckDuckGo",
            "tool_type": "builtin",
            "function_name": "web_search",
            "parameters": {
                "query": {"type": "string", "description": "Search query"}
            },
        },
        {
            "name": "File Reader",
            "description": "Read contents of a file",
            "tool_type": "builtin",
            "function_name": "read_file",
            "parameters": {
                "file_path": {"type": "string", "description": "Path to file"}
            },
        },
        {
            "name": "Calculator",
            "description": "Perform mathematical calculations",
            "tool_type": "builtin",
            "function_name": "calculator",
            "parameters": {
                "expression": {"type": "string", "description": "Math expression"}
            },
        },
    ]

    created_tools = []
    for tool_data in tools_data:
        existing = db.query(Tool).filter_by(name=tool_data["name"]).first()
        if existing:
            created_tools.append(existing)
            print(f"✓ Tool already exists: {existing.name}")
        else:
            tool = Tool(**tool_data)
            db.add(tool)
            db.flush()
            created_tools.append(tool)
            print(f"✓ Created Tool: {tool.name}")

    return created_tools


def create_example_agents(db, llm_providers, tools):
    """Create example agents."""
    agents_data = [
        {
            "name": "Research Agent",
            "role": "Senior Research Analyst",
            "goal": "Conduct thorough research on given topics and provide comprehensive summaries",
            "backstory": "You are a meticulous researcher with years of experience in gathering and analyzing information from various sources.",
            "llm_provider_id": llm_providers[0].id,
            "temperature": 0.7,
            "allow_delegation": False,
            "verbose": True,
            "tool_ids": [tools[0].id],  # Web Search
        },
        {
            "name": "Writer Agent",
            "role": "Professional Content Writer",
            "goal": "Create engaging and well-structured written content based on research",
            "backstory": "You are a skilled writer who excels at transforming raw information into compelling narratives.",
            "llm_provider_id": llm_providers[1].id,
            "temperature": 0.8,
            "allow_delegation": False,
            "verbose": True,
            "tool_ids": [],
        },
        {
            "name": "Data Analyst Agent",
            "role": "Data Analysis Expert",
            "goal": "Analyze data and extract meaningful insights",
            "backstory": "You are a data scientist with expertise in statistical analysis and pattern recognition.",
            "llm_provider_id": llm_providers[0].id,
            "temperature": 0.5,
            "allow_delegation": False,
            "verbose": True,
            "tool_ids": [tools[2].id],  # Calculator
        },
    ]

    created_agents = []
    for agent_data in agents_data:
        tool_ids = agent_data.pop("tool_ids", [])

        existing = db.query(Agent).filter_by(name=agent_data["name"]).first()
        if existing:
            created_agents.append(existing)
            print(f"✓ Agent already exists: {existing.name}")
        else:
            agent = Agent(**agent_data)
            db.add(agent)
            db.flush()

            # Associate tools
            for tool_id in tool_ids:
                db.execute(
                    agent_tools.insert().values(agent_id=agent.id, tool_id=tool_id)
                )

            created_agents.append(agent)
            print(f"✓ Created Agent: {agent.name}")

    return created_agents


def create_example_crew(db, agents, llm_providers):
    """Create an example crew."""
    crew_data = {
        "name": "Content Creation Crew",
        "description": "A crew that researches topics and creates high-quality content",
        "process": CrewProcess.SEQUENTIAL,
        "verbose": True,
        "memory": True,
        "manager_llm_provider_id": llm_providers[0].id,
    }

    existing = db.query(Crew).filter_by(name=crew_data["name"]).first()
    if existing:
        print(f"✓ Crew already exists: {existing.name}")
        return existing

    crew = Crew(**crew_data)
    db.add(crew)
    db.flush()

    # Add agents to crew
    for idx, agent in enumerate(agents[:2]):  # Research and Writer agents
        db.execute(
            crew_agents.insert().values(
                crew_id=crew.id, agent_id=agent.id, order=idx
            )
        )

    print(f"✓ Created Crew: {crew.name}")
    return crew


def create_example_flow(db, agents):
    """Create an example flow with complete workflow."""
    flow_data = {
        "name": "Research to Report Flow",
        "description": "A workflow that takes a research topic, conducts research, analyzes data, and generates a comprehensive report",
        "status": FlowStatus.ACTIVE,
        "version": 1,
        "tags": ["research", "reporting", "example"],
        "nodes": [
            # Input Node
            {
                "id": "input-1",
                "type": "input",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Research Topic Input",
                    "description": "Specify the research topic and requirements",
                    "inputs": [
                        {"name": "topic", "type": "string", "required": True},
                        {"name": "depth", "type": "string", "required": False},
                    ],
                    "width": 300,
                },
            },
            # Research Agent Node
            {
                "id": "agent-1",
                "type": "agent",
                "position": {"x": 100, "y": 250},
                "data": {
                    "label": "Research Agent",
                    "agent_id": agents[0].id,
                    "agent_name": agents[0].name,
                    "task": "Research the topic: {topic} with depth: {depth}",
                    "expected_output": "Comprehensive research summary with key findings",
                    "width": 280,
                },
            },
            # Data Analysis Agent Node
            {
                "id": "agent-2",
                "type": "agent",
                "position": {"x": 100, "y": 400},
                "data": {
                    "label": "Data Analyst",
                    "agent_id": agents[2].id,
                    "agent_name": agents[2].name,
                    "task": "Analyze the research findings and identify key patterns",
                    "expected_output": "Statistical analysis and key insights",
                    "width": 280,
                },
            },
            # Condition Node
            {
                "id": "condition-1",
                "type": "condition",
                "position": {"x": 100, "y": 550},
                "data": {
                    "label": "Quality Check",
                    "condition": "research_quality >= 'high'",
                    "description": "Check if research meets quality standards",
                    "width": 260,
                },
            },
            # Writer Agent Node
            {
                "id": "agent-3",
                "type": "agent",
                "position": {"x": 400, "y": 550},
                "data": {
                    "label": "Content Writer",
                    "agent_id": agents[1].id,
                    "agent_name": agents[1].name,
                    "task": "Create a comprehensive report based on the analysis",
                    "expected_output": "Well-structured written report",
                    "width": 280,
                },
            },
            # Output Node
            {
                "id": "output-1",
                "type": "output",
                "position": {"x": 400, "y": 700},
                "data": {
                    "label": "Final Report",
                    "description": "The completed research report",
                    "outputs": [
                        {"name": "report", "type": "string"},
                        {"name": "metadata", "type": "object"},
                    ],
                    "width": 280,
                },
            },
        ],
        "edges": [
            # Input -> Research Agent
            {
                "id": "edge-1",
                "source": "input-1",
                "target": "agent-1",
                "type": "default",
            },
            # Research Agent -> Data Analyst
            {
                "id": "edge-2",
                "source": "agent-1",
                "target": "agent-2",
                "type": "default",
            },
            # Data Analyst -> Quality Check
            {
                "id": "edge-3",
                "source": "agent-2",
                "target": "condition-1",
                "type": "default",
            },
            # Quality Check -> Writer (true branch)
            {
                "id": "edge-4",
                "source": "condition-1",
                "target": "agent-3",
                "type": "default",
                "data": {"condition": "true"},
            },
            # Writer -> Output
            {
                "id": "edge-5",
                "source": "agent-3",
                "target": "output-1",
                "type": "default",
            },
        ],
    }

    existing = db.query(Flow).filter_by(name=flow_data["name"]).first()
    if existing:
        print(f"✓ Flow already exists: {existing.name}")
        return existing

    flow = Flow(**flow_data)
    db.add(flow)
    db.flush()
    print(f"✓ Created Flow: {flow.name}")
    return flow


def main():
    """Main function to seed example data."""
    print("\n" + "="*60)
    print("Seeding Example Data")
    print("="*60 + "\n")

    db = SessionLocal()

    try:
        # Create examples
        print("\n📦 Creating LLM Providers...")
        llm_providers = create_example_llm_providers(db)

        print("\n🔧 Creating Tools...")
        tools = create_example_tools(db)

        print("\n🤖 Creating Agents...")
        agents = create_example_agents(db, llm_providers, tools)

        print("\n👥 Creating Crew...")
        crew = create_example_crew(db, agents, llm_providers)

        print("\n🔄 Creating Flow...")
        flow = create_example_flow(db, agents)

        # Commit all changes
        db.commit()

        print("\n" + "="*60)
        print("✅ Successfully seeded example data!")
        print("="*60)
        print(f"\nCreated:")
        print(f"  - {len(llm_providers)} LLM Providers")
        print(f"  - {len(tools)} Tools")
        print(f"  - {len(agents)} Agents")
        print(f"  - 1 Crew: {crew.name}")
        print(f"  - 1 Flow: {flow.name}")
        print(f"\nYou can now:")
        print(f"  1. View the flow in the UI at: /flows/{flow.id}")
        print(f"  2. Execute the flow with input: {{ 'topic': 'AI Safety' }}")
        print(f"  3. View the crew in the UI at: /crews/{crew.id}")
        print()

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
