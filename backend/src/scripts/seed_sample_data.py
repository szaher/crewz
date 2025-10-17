"""
Sample data seeding script for quickstart scenario validation.

Creates:
- Sample crew with 2 agents
- Sample flow with 3 nodes
- Sample tasks and tools
- Sample LLM providers

This data is used for:
1. Quickstart testing (T064)
2. Demo purposes
3. Development/testing environments
"""

import os
import sys
from uuid import UUID
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.src.db import SessionLocal
from backend.src.models import (
    Tenant, User, Crew, Agent, Task, Tool, Flow,
    LLMProvider, TenantStatus
)
from backend.src.models.flow import FlowDefinition


def seed_sample_crew(db: Session, tenant_id: UUID, user_id: UUID):
    """
    Create a sample crew with 2 agents and 3 tasks.

    Sample: "Content Creation Crew"
    - Research Agent (searches web for information)
    - Writer Agent (writes blog posts)
    - Editor Agent (reviews and edits content)
    """
    print("Creating sample crew...")

    # Create crew
    crew = Crew(
        tenant_id=tenant_id,
        name="Content Creation Crew",
        description="Automated content creation crew that researches, writes, and edits blog posts",
        config={
            "process": "sequential",
            "verbose": True
        },
        created_by=user_id
    )
    db.add(crew)
    db.flush()

    # Create research agent
    research_agent = Agent(
        tenant_id=tenant_id,
        name="Research Agent",
        role="Content Researcher",
        goal="Find accurate and relevant information for content creation",
        backstory="You are an expert researcher with access to various information sources. You excel at finding credible data and statistics.",
        llm_provider_id=None,  # Will use default
        tools=[],
        config={
            "verbose": True,
            "allow_delegation": False
        },
        created_by=user_id
    )
    db.add(research_agent)
    db.flush()

    # Create writer agent
    writer_agent = Agent(
        tenant_id=tenant_id,
        name="Writer Agent",
        role="Content Writer",
        goal="Create engaging and well-structured blog posts",
        backstory="You are a professional writer with experience in creating engaging content for various audiences.",
        llm_provider_id=None,
        tools=[],
        config={
            "verbose": True,
            "allow_delegation": False
        },
        created_by=user_id
    )
    db.add(writer_agent)
    db.flush()

    # Create tasks
    research_task = Task(
        tenant_id=tenant_id,
        name="Research Topic",
        description="Research the given topic and gather relevant information, statistics, and sources",
        expected_output="A comprehensive research report with key findings and sources",
        agent_id=research_agent.id,
        tools=[],
        config={
            "async_execution": False
        },
        created_by=user_id
    )
    db.add(research_task)

    writing_task = Task(
        tenant_id=tenant_id,
        name="Write Blog Post",
        description="Write an engaging blog post based on the research findings",
        expected_output="A well-structured blog post (800-1200 words) with introduction, body, and conclusion",
        agent_id=writer_agent.id,
        tools=[],
        config={
            "async_execution": False,
            "context": ["research_task"]
        },
        created_by=user_id
    )
    db.add(writing_task)
    db.flush()

    # Associate tasks with crew
    crew.config["tasks"] = [str(research_task.id), str(writing_task.id)]
    crew.config["agents"] = [str(research_agent.id), str(writer_agent.id)]

    db.commit()
    print(f"✓ Created crew: {crew.name} (ID: {crew.id})")
    return crew


def seed_sample_flow(db: Session, tenant_id: UUID, user_id: UUID):
    """
    Create a sample flow with multiple nodes.

    Sample: "Customer Onboarding Flow"
    - Start node
    - Validate email node
    - Send welcome email node
    - Create account node
    - End node
    """
    print("Creating sample flow...")

    # Create flow definition
    flow_definition = {
        "nodes": [
            {
                "id": "start-1",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "data": {
                    "label": "Start Onboarding"
                }
            },
            {
                "id": "validate-2",
                "type": "task",
                "position": {"x": 300, "y": 100},
                "data": {
                    "label": "Validate Email",
                    "task_type": "validation",
                    "config": {
                        "validation_type": "email",
                        "required": True
                    }
                }
            },
            {
                "id": "welcome-3",
                "type": "task",
                "position": {"x": 500, "y": 100},
                "data": {
                    "label": "Send Welcome Email",
                    "task_type": "notification",
                    "config": {
                        "template": "welcome_email",
                        "channel": "email"
                    }
                }
            },
            {
                "id": "end-4",
                "type": "end",
                "position": {"x": 700, "y": 100},
                "data": {
                    "label": "Onboarding Complete"
                }
            }
        ],
        "edges": [
            {
                "id": "e1-2",
                "source": "start-1",
                "target": "validate-2"
            },
            {
                "id": "e2-3",
                "source": "validate-2",
                "target": "welcome-3"
            },
            {
                "id": "e3-4",
                "source": "welcome-3",
                "target": "end-4"
            }
        ]
    }

    flow = Flow(
        tenant_id=tenant_id,
        name="Customer Onboarding Flow",
        description="Automated customer onboarding workflow with email validation and welcome messages",
        definition=flow_definition,
        variables={
            "customer_email": {
                "type": "string",
                "required": True,
                "description": "Customer email address"
            },
            "customer_name": {
                "type": "string",
                "required": True,
                "description": "Customer full name"
            }
        },
        created_by=user_id
    )
    db.add(flow)
    db.commit()

    print(f"✓ Created flow: {flow.name} (ID: {flow.id})")
    return flow


def seed_sample_tools(db: Session, tenant_id: UUID, user_id: UUID):
    """
    Create sample tools for agents to use.
    """
    print("Creating sample tools...")

    tools = [
        {
            "name": "Web Search",
            "description": "Search the web for information using a search engine API",
            "tool_type": "api",
            "config": {
                "api_endpoint": "https://api.search.example.com",
                "requires_auth": True
            }
        },
        {
            "name": "File Reader",
            "description": "Read and parse various file formats (PDF, DOCX, TXT)",
            "tool_type": "file_processing",
            "config": {
                "supported_formats": ["pdf", "docx", "txt", "md"]
            }
        },
        {
            "name": "Calculator",
            "description": "Perform mathematical calculations",
            "tool_type": "utility",
            "config": {
                "operations": ["add", "subtract", "multiply", "divide", "power", "sqrt"]
            }
        }
    ]

    created_tools = []
    for tool_data in tools:
        tool = Tool(
            tenant_id=tenant_id,
            name=tool_data["name"],
            description=tool_data["description"],
            tool_type=tool_data["tool_type"],
            config=tool_data["config"],
            created_by=user_id
        )
        db.add(tool)
        created_tools.append(tool)

    db.commit()
    print(f"✓ Created {len(created_tools)} tools")
    return created_tools


def seed_sample_llm_providers(db: Session, tenant_id: UUID, user_id: UUID):
    """
    Create sample LLM provider configurations.
    """
    print("Creating sample LLM providers...")

    providers = [
        {
            "name": "OpenAI GPT-4",
            "provider_type": "openai",
            "model_name": "gpt-4",
            "config": {
                "temperature": 0.7,
                "max_tokens": 2000
            }
        },
        {
            "name": "OpenAI GPT-3.5",
            "provider_type": "openai",
            "model_name": "gpt-3.5-turbo",
            "config": {
                "temperature": 0.7,
                "max_tokens": 1500
            }
        }
    ]

    created_providers = []
    for provider_data in providers:
        # Check if already exists
        existing = db.query(LLMProvider).filter(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.name == provider_data["name"]
        ).first()

        if not existing:
            provider = LLMProvider(
                tenant_id=tenant_id,
                name=provider_data["name"],
                provider_type=provider_data["provider_type"],
                model_name=provider_data["model_name"],
                config=provider_data["config"],
                is_active=True,
                created_by=user_id
            )
            db.add(provider)
            created_providers.append(provider)

    db.commit()
    print(f"✓ Created {len(created_providers)} LLM providers")
    return created_providers


def seed_all_sample_data(tenant_id: UUID = None, user_id: UUID = None):
    """
    Seed all sample data for a tenant.

    Args:
        tenant_id: Tenant ID (defaults to first active tenant)
        user_id: User ID (defaults to first user in tenant)
    """
    db = SessionLocal()

    try:
        # Get or create tenant
        if not tenant_id:
            tenant = db.query(Tenant).filter(
                Tenant.status == TenantStatus.ACTIVE
            ).first()

            if not tenant:
                print("No active tenant found. Creating default tenant...")
                from backend.src.services.tenant_service import TenantService
                tenant_service = TenantService()
                import asyncio
                tenant = asyncio.run(tenant_service.create_tenant(
                    db,
                    name="Demo Tenant",
                    max_users=50,
                    max_agents=100,
                    max_flows=200
                ))

            tenant_id = tenant.id

        # Get or create user
        if not user_id:
            user = db.query(User).filter(
                User.tenant_id == tenant_id,
                User.is_active == True
            ).first()

            if not user:
                print("No active user found for tenant. Creating default user...")
                from backend.src.models.user import User as UserModel
                user = UserModel(
                    tenant_id=tenant_id,
                    email="demo@example.com",
                    full_name="Demo User",
                    hashed_password="not_a_real_password",  # In production, use proper hashing
                    is_active=True,
                    is_superuser=False
                )
                db.add(user)
                db.commit()

            user_id = user.id

        print(f"\n=== Seeding sample data for tenant {tenant_id} ===\n")

        # Seed all components
        crew = seed_sample_crew(db, tenant_id, user_id)
        flow = seed_sample_flow(db, tenant_id, user_id)
        tools = seed_sample_tools(db, tenant_id, user_id)
        providers = seed_sample_llm_providers(db, tenant_id, user_id)

        print(f"\n=== Sample data seeding complete ===")
        print(f"Created:")
        print(f"  - 1 crew with 2 agents and 2 tasks")
        print(f"  - 1 flow with 4 nodes")
        print(f"  - {len(tools)} tools")
        print(f"  - {len(providers)} LLM providers")

        return {
            "crew": crew,
            "flow": flow,
            "tools": tools,
            "providers": providers
        }

    except Exception as e:
        print(f"\n✗ Error seeding sample data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    """
    Run as: python -m backend.src.scripts.seed_sample_data
    """
    import argparse

    parser = argparse.ArgumentParser(description="Seed sample data for quickstart")
    parser.add_argument("--tenant-id", type=str, help="Tenant ID (UUID)")
    parser.add_argument("--user-id", type=str, help="User ID (UUID)")

    args = parser.parse_args()

    tenant_id = UUID(args.tenant_id) if args.tenant_id else None
    user_id = UUID(args.user_id) if args.user_id else None

    seed_all_sample_data(tenant_id, user_id)
