#!/usr/bin/env python3
"""
Create default examples for CrewAI platform.
Based on CrewAI's trip planner and research examples.
"""

import sys
import os

# Add backend src to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from src.db import SessionLocal
from src.models import Agent, Crew, Flow, Tool, LLMProvider
from src.models.llm_provider import LLMProviderType
from src.models.crew import CrewProcess
from src.models.flow import FlowStatus
from sqlalchemy.exc import IntegrityError

def create_default_llm_provider(db, tenant_id=1):
    """Create default OpenAI provider."""
    print("\n📦 Creating LLM Provider...")

    # Check if already exists
    existing = db.query(LLMProvider).filter_by(tenant_id=tenant_id, name="OpenAI GPT-4").first()
    if existing:
        print(f"✓ LLM Provider already exists: {existing.name}")
        return existing

    provider = LLMProvider(
        tenant_id=tenant_id,
        name="OpenAI GPT-4",
        provider_type=LLMProviderType.OPENAI,
        model_name="gpt-4",
        api_key="sk-placeholder-replace-with-real-key",
        is_active=True,
        is_default=True,
    )
    db.add(provider)
    db.flush()
    print(f"✓ Created LLM Provider: {provider.name}")
    return provider

def create_default_tools(db):
    """Create default tools."""
    print("\n🔧 Creating Tools...")

    tools_data = [
        {
            "name": "Web Search",
            "description": "Search the web for current information using DuckDuckGo",
            "tool_type": "custom",
            "code": """
def search_web(query: str) -> str:
    \"\"\"Search the web for information.\"\"\"
    # Placeholder implementation
    # In production, integrate with a search API like DuckDuckGo, Google, or Serper
    return f"Search results for: {query}\\n[Placeholder - configure search API]"
""",
            "schema": {
                "input": {"query": "string"},
                "output": {"results": "string"}
            }
        },
        {
            "name": "File Reader",
            "description": "Read and analyze file contents",
            "tool_type": "custom",
            "code": """
def read_file(file_path: str) -> str:
    \"\"\"Read file contents.\"\"\"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"
""",
            "schema": {
                "input": {"file_path": "string"},
                "output": {"content": "string"}
            }
        },
        {
            "name": "Calculator",
            "description": "Perform mathematical calculations",
            "tool_type": "custom",
            "code": """
def calculate(expression: str) -> str:
    \"\"\"Safely evaluate a mathematical expression.\"\"\"
    try:
        # Use ast.literal_eval for safety - only allows literals
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
""",
            "schema": {
                "input": {"expression": "string"},
                "output": {"result": "number"}
            }
        },
    ]

    created_tools = []
    for tool_data in tools_data:
        # Check if already exists
        existing = db.query(Tool).filter_by(name=tool_data["name"]).first()
        if existing:
            print(f"✓ Tool already exists: {existing.name}")
            created_tools.append(existing)
        else:
            tool = Tool(**tool_data)
            db.add(tool)
            db.flush()
            created_tools.append(tool)
            print(f"✓ Created Tool: {tool.name}")

    return created_tools

def create_default_agents(db, llm_provider, tools):
    """Create default agents based on CrewAI examples."""
    print("\n🤖 Creating Agents...")

    # Map tool names to IDs
    web_search_tool = next((t for t in tools if t.name == "Web Search"), None)

    agents_data = [
        {
            "name": "Research Analyst",
            "role": "Senior Research Analyst",
            "goal": "Uncover cutting-edge developments and provide comprehensive research on given topics",
            "backstory": """You work at a leading tech think tank.
Your expertise lies in identifying emerging trends and technologies.
You have a knack for dissecting complex data and presenting actionable insights.""",
            "llm_provider_id": llm_provider.id,
            "temperature": 0.7,
            "allow_delegation": False,
            "verbose": True,
            "max_iter": 15,
        },
        {
            "name": "Content Writer",
            "role": "Tech Content Strategist",
            "goal": "Craft compelling content on tech advancements that engages and educates readers",
            "backstory": """You are a renowned Content Strategist, known for your insightful
and engaging articles. You transform complex concepts into compelling narratives
that resonate with a wide audience.""",
            "llm_provider_id": llm_provider.id,
            "temperature": 0.8,
            "allow_delegation": False,
            "verbose": True,
            "max_iter": 15,
        },
        {
            "name": "Travel Expert",
            "role": "Amazing Travel Concierge",
            "goal": "Create the most amazing travel itineraries with budget and packing suggestions",
            "backstory": """Specialist in travel planning and logistics with
decades of experience. You have traveled to every corner of the world
and know the best places to visit, eat, and stay.""",
            "llm_provider_id": llm_provider.id,
            "temperature": 0.7,
            "allow_delegation": True,
            "verbose": True,
            "max_iter": 15,
        },
    ]

    created_agents = []
    for agent_data in agents_data:
        # Check if already exists
        existing = db.query(Agent).filter_by(name=agent_data["name"]).first()
        if existing:
            print(f"✓ Agent already exists: {existing.name}")
            created_agents.append(existing)
        else:
            agent = Agent(**agent_data)
            db.add(agent)
            db.flush()

            # Add web search tool to research analyst
            if agent.name == "Research Analyst" and web_search_tool:
                agent.tools.append(web_search_tool)

            created_agents.append(agent)
            print(f"✓ Created Agent: {agent.name}")

    return created_agents

def create_default_crew(db, agents, llm_provider):
    """Create default research crew."""
    print("\n👥 Creating Crew...")

    # Check if already exists
    existing = db.query(Crew).filter_by(name="Research Team").first()
    if existing:
        print(f"✓ Crew already exists: {existing.name}")
        return existing

    # Get research and writer agents
    research_agent = next((a for a in agents if a.name == "Research Analyst"), None)
    writer_agent = next((a for a in agents if a.name == "Content Writer"), None)

    if not research_agent or not writer_agent:
        print("❌ Required agents not found")
        return None

    crew = Crew(
        name="Research Team",
        description="A crew that researches topics and creates comprehensive content",
        process=CrewProcess.SEQUENTIAL,
        verbose=True,
        memory=True,
        manager_llm_provider_id=llm_provider.id,
    )
    db.add(crew)
    db.flush()

    # Add agents to crew in order
    crew.agents.append(research_agent)
    crew.agents.append(writer_agent)

    print(f"✓ Created Crew: {crew.name} with {len(crew.agents)} agents")
    return crew

def create_default_flow(db, agents):
    """Create default research flow."""
    print("\n🔄 Creating Flow...")

    # Check if already exists
    existing = db.query(Flow).filter_by(name="Research to Article Workflow").first()
    if existing:
        print(f"✓ Flow already exists: {existing.name}")
        return existing

    # Get agents
    research_agent = next((a for a in agents if a.name == "Research Analyst"), None)
    writer_agent = next((a for a in agents if a.name == "Content Writer"), None)

    if not research_agent or not writer_agent:
        print("❌ Required agents not found")
        return None

    flow = Flow(
        name="Research to Article Workflow",
        description="A complete workflow that researches a topic and creates a comprehensive article",
        status=FlowStatus.ACTIVE,
        version=1,
        tags=["research", "content", "example", "default"],
        nodes=[
            # Input Node
            {
                "id": "input-1",
                "type": "input",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Research Topic",
                    "description": "Enter the topic you want to research",
                    "inputs": [
                        {"name": "topic", "type": "string", "required": True},
                        {"name": "depth", "type": "string", "required": False, "default": "comprehensive"},
                    ],
                    "width": 300,
                },
            },
            # Research Agent Node
            {
                "id": "agent-1",
                "type": "agent",
                "position": {"x": 100, "y": 300},
                "data": {
                    "label": "Research Phase",
                    "agent_id": research_agent.id,
                    "agent_name": research_agent.name,
                    "task": "Conduct comprehensive research on {topic}. Focus on the latest developments, key players, and future trends. Depth: {depth}",
                    "expected_output": "A detailed research report with citations, statistics, and actionable insights",
                    "context": "You are researching for a tech blog that publishes cutting-edge content",
                    "width": 320,
                },
            },
            # Quality Check Condition
            {
                "id": "condition-1",
                "type": "condition",
                "position": {"x": 100, "y": 500},
                "data": {
                    "label": "Quality Gate",
                    "condition": "word_count >= 500 && citations >= 3",
                    "description": "Ensure research meets minimum quality standards",
                    "width": 280,
                },
            },
            # Writer Agent Node
            {
                "id": "agent-2",
                "type": "agent",
                "position": {"x": 450, "y": 500},
                "data": {
                    "label": "Content Writing",
                    "agent_id": writer_agent.id,
                    "agent_name": writer_agent.name,
                    "task": "Using the research provided, write an engaging and informative article about {topic}. Make it accessible yet authoritative.",
                    "expected_output": "A well-structured article (800-1200 words) with introduction, body sections, and conclusion",
                    "context": "You are writing for a tech-savvy audience that values both depth and readability",
                    "width": 320,
                },
            },
            # Output Node
            {
                "id": "output-1",
                "type": "output",
                "position": {"x": 450, "y": 700},
                "data": {
                    "label": "Final Article",
                    "description": "The completed research article ready for publication",
                    "outputs": [
                        {"name": "article", "type": "string"},
                        {"name": "word_count", "type": "number"},
                        {"name": "citations", "type": "array"},
                        {"name": "metadata", "type": "object"},
                    ],
                    "width": 300,
                },
            },
        ],
        edges=[
            {"id": "edge-1", "source": "input-1", "target": "agent-1", "type": "default"},
            {"id": "edge-2", "source": "agent-1", "target": "condition-1", "type": "default"},
            {"id": "edge-3", "source": "condition-1", "target": "agent-2", "type": "default"},
            {"id": "edge-4", "source": "agent-2", "target": "output-1", "type": "default"},
        ],
    )

    db.add(flow)
    db.flush()
    print(f"✓ Created Flow: {flow.name}")
    print(f"  - Nodes: {len(flow.nodes)}")
    print(f"  - Edges: {len(flow.edges)}")
    return flow

def main():
    """Main function to create all defaults."""
    print("\n" + "="*60)
    print("Creating Default Examples for CrewAI Platform")
    print("="*60)

    db = SessionLocal()

    try:
        # Create LLM provider
        llm_provider = create_default_llm_provider(db)

        # Create tools
        tools = create_default_tools(db)

        # Create agents
        agents = create_default_agents(db, llm_provider, tools)

        # Create crew
        crew = create_default_crew(db, agents, llm_provider)

        # Create flow
        flow = create_default_flow(db, agents)

        # Commit all changes
        db.commit()

        print("\n" + "="*60)
        print("✅ Successfully created all default examples!")
        print("="*60)
        print("\n📊 Summary:")
        print(f"  - 1 LLM Provider: {llm_provider.name}")
        print(f"  - {len(tools)} Tools")
        print(f"  - {len(agents)} Agents:")
        for agent in agents:
            print(f"    • {agent.name} ({agent.role})")
        if crew:
            print(f"  - 1 Crew: {crew.name}")
        if flow:
            print(f"  - 1 Flow: {flow.name}")

        print("\n🎯 Next Steps:")
        print("  1. Update LLM provider API key in the UI (Settings > LLM Providers)")
        print(f"  2. View the flow: http://localhost:3001/flows/{flow.id if flow else 'N/A'}")
        print(f"  3. View the crew: http://localhost:3001/crews/{crew.id if crew else 'N/A'}")
        print("  4. Execute the flow with input: {'topic': 'AI Safety', 'depth': 'comprehensive'}")
        print()

    except IntegrityError as e:
        db.rollback()
        print(f"\n❌ Database integrity error: {e}")
        print("Some defaults may already exist. This is normal.")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Error creating defaults: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
