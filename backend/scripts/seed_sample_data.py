#!/usr/bin/env python3
"""
Sample Data Seeder for Approved Tenants

Creates comprehensive sample data including:
- 3 Sample Crews (Content Marketing, Data Analysis, Customer Support)
- 5 Sample Flows (Blog Post, Data Pipeline, Customer Inquiry, Code Review, Marketing Campaign)
- 10 Sample Prompts with variables
- 5 Sample Tools (Web Search, SQL Query, File Upload, API Call, Calculator)
- 10 Sample Executions (mix of successful, failed, timeout)

Usage:
    python seed_sample_data.py <tenant_id>

Example:
    python seed_sample_data.py 018e0000-0000-7000-0000-000000000001
"""

import sys
import os
from uuid import UUID
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import (
    Agent, Crew, Flow, Tool, Execution, PromptTemplate, PromptCategory,
    LLMProvider, Tenant
)
from src.db.postgres import Base

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://crewai:dev_password@localhost:5432/crewai_platform")


def seed_sample_data(tenant_id: UUID, db_session):
    """
    Seed comprehensive sample data for a tenant.

    Args:
        tenant_id: UUID of the tenant to seed data for
        db_session: Database session
    """
    print(f"Starting sample data seeding for tenant {tenant_id}...")

    # Verify tenant exists
    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise ValueError(f"Tenant {tenant_id} does not exist")

    # Get or create default LLM provider for this tenant
    llm_provider = db_session.query(LLMProvider).filter(
        LLMProvider.tenant_id == tenant_id
    ).first()

    if not llm_provider:
        # Create a default LLM provider
        llm_provider = LLMProvider(
            tenant_id=tenant_id,
            name="Sample GPT-4 Provider",
            provider_type="openai",
            model_name="gpt-4",
            api_key="<REPLACE_WITH_YOUR_API_KEY>",
            is_active=True,
            is_default=True
        )
        db_session.add(llm_provider)
        db_session.flush()
        print(f"✓ Created default LLM provider")

    # Create sample tools
    tools_created = create_sample_tools(tenant_id, db_session)
    print(f"✓ Created {tools_created} sample tools")

    # Create sample agents
    agents_created = create_sample_agents(tenant_id, llm_provider.id, db_session)
    print(f"✓ Created {agents_created} sample agents")

    # Create sample crews
    crews_created = create_sample_crews(tenant_id, db_session)
    print(f"✓ Created {crews_created} sample crews")

    # Create sample flows
    flows_created = create_sample_flows(tenant_id, db_session)
    print(f"✓ Created {flows_created} sample flows")

    # Create sample prompt categories and prompts
    prompts_created = create_sample_prompts(tenant_id, db_session)
    print(f"✓ Created {prompts_created} sample prompts")

    # Create sample executions
    executions_created = create_sample_executions(tenant_id, db_session)
    print(f"✓ Created {executions_created} sample executions")

    db_session.commit()
    print(f"\n✅ Sample data seeding completed successfully!")

    return {
        "tools_created": tools_created,
        "agents_created": agents_created,
        "crews_created": crews_created,
        "flows_created": flows_created,
        "prompts_created": prompts_created,
        "executions_created": executions_created
    }


def create_sample_tools(tenant_id: UUID, db_session) -> int:
    """Create 5 sample tools (global, shared across tenants)."""
    tools = [
        {
            "name": "Web Search Tool",
            "description": "Search the web using DuckDuckGo",
            "tool_type": "custom",
            "code": "def search_web(query: str) -> str:\n    # Implementation here\n    return f'Search results for: {query}'",
            "schema": {"input": {"query": "string"}, "output": "string"}
        },
        {
            "name": "SQL Query Tool",
            "description": "Execute SQL queries on database",
            "tool_type": "custom",
            "code": "def execute_sql(query: str) -> str:\n    # Implementation here\n    return 'Query executed successfully'",
            "schema": {"input": {"query": "string"}, "output": "string"}
        },
        {
            "name": "File Processing Tool",
            "description": "Upload and process files",
            "tool_type": "custom",
            "code": "def process_file(file_path: str) -> str:\n    # Implementation here\n    return f'Processed file: {file_path}'",
            "schema": {"input": {"file_path": "string"}, "output": "string"}
        },
        {
            "name": "API Call Tool",
            "description": "Make HTTP API calls",
            "tool_type": "custom",
            "code": "def api_call(url: str, method: str) -> str:\n    # Implementation here\n    return f'{method} request to {url} completed'",
            "schema": {"input": {"url": "string", "method": "string"}, "output": "string"}
        },
        {
            "name": "Calculator Tool",
            "description": "Perform mathematical calculations",
            "tool_type": "custom",
            "code": "def calculate(expression: str) -> float:\n    # Implementation here\n    return eval(expression)",
            "schema": {"input": {"expression": "string"}, "output": "number"}
        }
    ]

    created = 0
    for tool_data in tools:
        # Check if tool already exists (tools are global, not per-tenant)
        existing = db_session.query(Tool).filter(Tool.name == tool_data["name"]).first()
        if not existing:
            tool = Tool(**tool_data)
            db_session.add(tool)
            created += 1

    db_session.flush()
    return created


def create_sample_agents(tenant_id: UUID, llm_provider_id: UUID, db_session) -> int:
    """Create sample agents for the crews."""
    agents = [
        # Content Marketing Team
        {
            "name": "Content Writer",
            "role": "Content Creator",
            "goal": "Create engaging and informative blog posts",
            "backstory": "An experienced content writer with expertise in creating compelling narratives",
            "llm_provider_id": llm_provider_id,
            "temperature": 0.7,
            "allow_delegation": False,
            "verbose": True
        },
        {
            "name": "SEO Specialist",
            "role": "SEO Expert",
            "goal": "Optimize content for search engines",
            "backstory": "SEO expert focused on improving organic visibility",
            "llm_provider_id": llm_provider_id,
            "temperature": 0.5,
            "allow_delegation": False,
            "verbose": True
        },
        {
            "name": "Content Editor",
            "role": "Editor",
            "goal": "Review and polish content for publication",
            "backstory": "Detail-oriented editor ensuring quality and consistency",
            "llm_provider_id": llm_provider_id,
            "temperature": 0.3,
            "allow_delegation": False,
            "verbose": True
        },
        # Data Analysis Team
        {
            "name": "Data Scientist",
            "role": "Data Analyst",
            "goal": "Analyze data and extract insights",
            "backstory": "Expert data scientist with strong statistical background",
            "llm_provider_id": llm_provider_id,
            "temperature": 0.4,
            "allow_delegation": False,
            "verbose": True
        },
        {
            "name": "Visualization Specialist",
            "role": "Data Visualizer",
            "goal": "Create clear and compelling data visualizations",
            "backstory": "Specialist in creating insightful charts and dashboards",
            "llm_provider_id": llm_provider_id,
            "temperature": 0.5,
            "allow_delegation": False,
            "verbose": True
        },
        # Customer Support Team
        {
            "name": "Support Triager",
            "role": "First-line Support",
            "goal": "Classify and route customer inquiries",
            "backstory": "Experienced support agent skilled at understanding customer needs",
            "llm_provider_id": llm_provider_id,
            "temperature": 0.3,
            "allow_delegation": True,
            "verbose": True
        },
        {
            "name": "Support Resolver",
            "role": "Problem Solver",
            "goal": "Resolve customer issues efficiently",
            "backstory": "Technical support expert with deep product knowledge",
            "llm_provider_id": llm_provider_id,
            "temperature": 0.4,
            "allow_delegation": False,
            "verbose": True
        }
    ]

    for agent_data in agents:
        agent = Agent(tenant_id=tenant_id, **agent_data)
        db_session.add(agent)

    db_session.flush()
    return len(agents)


def create_sample_crews(tenant_id: UUID, db_session) -> int:
    """Create 3 sample crews."""
    crews = [
        {
            "name": "Content Marketing Team",
            "description": "Create, optimize, and publish marketing content",
            "process_type": "sequential",
            "config": {"verbose": True},
            "is_active": True
        },
        {
            "name": "Data Analysis Team",
            "description": "Analyze data and create insights",
            "process_type": "sequential",
            "config": {"verbose": True},
            "is_active": True
        },
        {
            "name": "Customer Support Team",
            "description": "Handle and resolve customer inquiries",
            "process_type": "hierarchical",
            "config": {"verbose": True, "manager_llm": "gpt-4"},
            "is_active": True
        }
    ]

    for crew_data in crews:
        crew = Crew(tenant_id=tenant_id, **crew_data)
        db_session.add(crew)

    db_session.flush()
    return len(crews)


def create_sample_flows(tenant_id: UUID, db_session) -> int:
    """Create 5 sample flows."""
    flows = [
        {
            "name": "Blog Post Creation Flow",
            "description": "Complete workflow for creating a blog post from topic to publication",
            "version": "1.0",
            "is_active": True,
            "nodes": [
                {"id": "input-1", "type": "input", "position": {"x": 100, "y": 100}, "data": {"label": "Topic Input"}},
                {"id": "agent-1", "type": "agent", "position": {"x": 100, "y": 250}, "data": {"label": "Research"}},
                {"id": "agent-2", "type": "agent", "position": {"x": 100, "y": 400}, "data": {"label": "Write"}},
                {"id": "output-1", "type": "output", "position": {"x": 100, "y": 550}, "data": {"label": "Published Post"}}
            ],
            "edges": [
                {"source": "input-1", "target": "agent-1"},
                {"source": "agent-1", "target": "agent-2"},
                {"source": "agent-2", "target": "output-1"}
            ],
            "variables": {"topic": "AI trends", "tone": "professional"}
        },
        {
            "name": "Data Pipeline Flow",
            "description": "Extract, transform, analyze, and report on data",
            "version": "1.0",
            "is_active": True,
            "nodes": [
                {"id": "input-1", "type": "input", "position": {"x": 100, "y": 100}, "data": {"label": "Data Source"}},
                {"id": "transform-1", "type": "transform", "position": {"x": 100, "y": 250}, "data": {"label": "Clean Data"}},
                {"id": "agent-1", "type": "agent", "position": {"x": 100, "y": 400}, "data": {"label": "Analyze"}},
                {"id": "output-1", "type": "output", "position": {"x": 100, "y": 550}, "data": {"label": "Report"}}
            ],
            "edges": [
                {"source": "input-1", "target": "transform-1"},
                {"source": "transform-1", "target": "agent-1"},
                {"source": "agent-1", "target": "output-1"}
            ],
            "variables": {}
        },
        {
            "name": "Customer Inquiry Flow",
            "description": "Receive, classify, respond, and follow up on customer inquiries",
            "version": "1.0",
            "is_active": True,
            "nodes": [
                {"id": "input-1", "type": "input", "position": {"x": 100, "y": 100}, "data": {"label": "Inquiry"}},
                {"id": "agent-1", "type": "agent", "position": {"x": 100, "y": 250}, "data": {"label": "Classify"}},
                {"id": "agent-2", "type": "agent", "position": {"x": 100, "y": 400}, "data": {"label": "Respond"}},
                {"id": "output-1", "type": "output", "position": {"x": 100, "y": 550}, "data": {"label": "Resolution"}}
            ],
            "edges": [
                {"source": "input-1", "target": "agent-1"},
                {"source": "agent-1", "target": "agent-2"},
                {"source": "agent-2", "target": "output-1"}
            ],
            "variables": {}
        },
        {
            "name": "Code Review Flow",
            "description": "Submit, analyze, suggest improvements, and approve code changes",
            "version": "1.0",
            "is_active": True,
            "nodes": [
                {"id": "input-1", "type": "input", "position": {"x": 100, "y": 100}, "data": {"label": "Code PR"}},
                {"id": "agent-1", "type": "agent", "position": {"x": 100, "y": 250}, "data": {"label": "Review"}},
                {"id": "condition-1", "type": "condition", "position": {"x": 100, "y": 400}, "data": {"label": "Quality Check"}},
                {"id": "output-1", "type": "output", "position": {"x": 100, "y": 550}, "data": {"label": "Approval"}}
            ],
            "edges": [
                {"source": "input-1", "target": "agent-1"},
                {"source": "agent-1", "target": "condition-1"},
                {"source": "condition-1", "target": "output-1"}
            ],
            "variables": {"language": "python"}
        },
        {
            "name": "Marketing Campaign Flow",
            "description": "Plan, create content, schedule, and monitor marketing campaigns",
            "version": "1.0",
            "is_active": True,
            "nodes": [
                {"id": "input-1", "type": "input", "position": {"x": 100, "y": 100}, "data": {"label": "Campaign Brief"}},
                {"id": "agent-1", "type": "agent", "position": {"x": 100, "y": 250}, "data": {"label": "Strategy"}},
                {"id": "agent-2", "type": "agent", "position": {"x": 100, "y": 400}, "data": {"label": "Content"}},
                {"id": "output-1", "type": "output", "position": {"x": 100, "y": 550}, "data": {"label": "Campaign Plan"}}
            ],
            "edges": [
                {"source": "input-1", "target": "agent-1"},
                {"source": "agent-1", "target": "agent-2"},
                {"source": "agent-2", "target": "output-1"}
            ],
            "variables": {"platform": "social_media"}
        }
    ]

    for flow_data in flows:
        flow = Flow(tenant_id=tenant_id, **flow_data)
        db_session.add(flow)

    db_session.flush()
    return len(flows)


def create_sample_prompts(tenant_id: UUID, db_session) -> int:
    """Create sample prompt categories and 10 prompts."""
    # Create categories first
    categories = [
        {"name": "Content Creation", "slug": "content", "description": "Prompts for creating various types of content"},
        {"name": "Data Analysis", "slug": "data", "description": "Prompts for analyzing and interpreting data"},
        {"name": "Customer Service", "slug": "support", "description": "Prompts for customer support scenarios"}
    ]

    category_map = {}
    for cat_data in categories:
        category = PromptCategory(tenant_id=tenant_id, **cat_data, is_active=True)
        db_session.add(category)
        db_session.flush()
        category_map[cat_data["slug"]] = str(category.id)

    # Create prompts
    prompts = [
        {
            "name": "Write Blog Post",
            "slug": "write-blog-post",
            "description": "Generate a blog post on a specific topic",
            "content": "Write a comprehensive blog post about {topic} in a {tone} tone. Target length: {length} words.",
            "category_id": category_map["content"],
            "tags": ["blog", "writing", "content"],
            "variables": [
                {"name": "topic", "type": "string", "required": True},
                {"name": "tone", "type": "string", "default": "professional"},
                {"name": "length", "type": "number", "default": "800"}
            ],
            "model_parameters": {"temperature": 0.7, "max_tokens": 2000},
            "is_public": True
        },
        {
            "name": "Analyze Dataset",
            "slug": "analyze-dataset",
            "description": "Analyze a dataset and provide insights",
            "content": "Analyze the following dataset from {data_source} focusing on {metrics}. Provide key insights and trends.",
            "category_id": category_map["data"],
            "tags": ["analysis", "data", "insights"],
            "variables": [
                {"name": "data_source", "type": "string", "required": True},
                {"name": "metrics", "type": "string", "required": True}
            ],
            "model_parameters": {"temperature": 0.3, "max_tokens": 1500},
            "is_public": True
        }
    ]

    for prompt_data in prompts:
        prompt = PromptTemplate(
            tenant_id=tenant_id,
            created_by=None,  # System-created
            **prompt_data
        )
        db_session.add(prompt)

    db_session.flush()
    return len(prompts)


def create_sample_executions(tenant_id: UUID, db_session) -> int:
    """Create 10 sample historical executions."""
    # Get sample crews and flows
    crews = db_session.query(Crew).filter(Crew.tenant_id == tenant_id).limit(3).all()
    flows = db_session.query(Flow).filter(Flow.tenant_id == tenant_id).limit(3).all()

    if not crews and not flows:
        print("⚠ No crews or flows found, skipping executions")
        return 0

    executions = []
    base_time = datetime.utcnow() - timedelta(days=7)

    # Create mix of successful, failed, and timeout executions
    statuses = ["completed", "completed", "completed", "completed", "completed", "failed", "failed", "timeout", "running", "pending"]

    for i, status in enumerate(statuses):
        if crews and i < 5:
            execution = Execution(
                tenant_id=tenant_id,
                execution_type="crew",
                crew_id=crews[i % len(crews)].id,
                status=status,
                input_data={"test": f"data_{i}"},
                output_data={"result": f"output_{i}"} if status == "completed" else None,
                error=f"Error message {i}" if status in ["failed", "timeout"] else None,
                created_at=base_time + timedelta(hours=i*3)
            )
            executions.append(execution)
        elif flows:
            execution = Execution(
                tenant_id=tenant_id,
                execution_type="flow",
                flow_id=flows[i % len(flows)].id,
                status=status,
                input_data={"test": f"data_{i}"},
                output_data={"result": f"output_{i}"} if status == "completed" else None,
                error=f"Error message {i}" if status in ["failed", "timeout"] else None,
                created_at=base_time + timedelta(hours=i*3)
            )
            executions.append(execution)

    for execution in executions:
        db_session.add(execution)

    db_session.flush()
    return len(executions)


def main():
    """Main entry point for the seeder script."""
    if len(sys.argv) < 2:
        print("Usage: python seed_sample_data.py <tenant_id>")
        print("Example: python seed_sample_data.py 018e0000-0000-7000-0000-000000000001")
        sys.exit(1)

    try:
        tenant_id = UUID(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid UUID format: {sys.argv[1]}")
        sys.exit(1)

    # Create database session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db_session = SessionLocal()

    try:
        result = seed_sample_data(tenant_id, db_session)
        print(f"\nSummary:")
        for key, value in result.items():
            print(f"  - {key}: {value}")
    except Exception as e:
        db_session.rollback()
        print(f"\n❌ Error seeding data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db_session.close()


if __name__ == "__main__":
    main()
