"""Seed a set of rich default prompt templates and categories."""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from .prompt_service import PromptService
from ..models import PromptTemplate, PromptCategory


def _ensure_category(db: Session, tenant_id: int, name: str, description: str | None = None) -> PromptCategory:
    cat = (
        db.query(PromptCategory)
        .filter(and_(PromptCategory.tenant_id == tenant_id, PromptCategory.name == name))
        .first()
    )
    if cat:
        return cat
    cat = PromptCategory(
        tenant_id=tenant_id,
        name=name,
        description=description,
    )
    db.add(cat)
    db.flush()
    return cat


def _exists_slug(db: Session, tenant_id: int, slug: str) -> bool:
    return (
        db.query(PromptTemplate)
        .filter(and_(PromptTemplate.tenant_id == tenant_id, PromptTemplate.slug == slug))
        .first()
        is not None
    )


def seed_default_prompts(db: Session, tenant_id: int = 1) -> None:
    """Create a handful of rich prompts (with and without variables) for first-time use.

    Safe to run multiple times — will upsert by slug.
    """
    # Categories
    writing = _ensure_category(db, tenant_id, "Writing", "Writing tasks and content generation")
    research = _ensure_category(db, tenant_id, "Research", "Structured research and analysis")
    engineering = _ensure_category(db, tenant_id, "Engineering", "Code reviews and technical prompts")
    product = _ensure_category(db, tenant_id, "Product", "Productivity & operations")
    data = _ensure_category(db, tenant_id, "Data", "Data analysis, planning, and SQL")
    marketing = _ensure_category(db, tenant_id, "Marketing", "Marketing copy, positioning, and messaging")
    support = _ensure_category(db, tenant_id, "Support", "Customer support and success")
    design = _ensure_category(db, tenant_id, "Design/UX", "UX writing and design prompts")

    prompts: List[Dict[str, Any]] = [
        {
            "slug": "article-writer",
            "name": "Article Writer",
            "category": writing,
            "description": "Write clear, engaging long-form content on a topic with a chosen depth.",
            "tags": ["content", "writer", "article"],
            "content": (
                "You are a talented educational writer with a clear, engaging style.\n\n"
                "Act as an Educational Content Writer and create an article on {topic}.\n"
                "Target audience: {target_audience}.\n"
                "Depth: {level}.\n\n"
                "Requirements:\n"
                "- Strong, helpful introduction\n"
                "- Structured headings and subheadings\n"
                "- Clear examples and analogies where useful\n"
                "- Balanced depth matching the requested level\n"
                "- Concise conclusion with actionable takeaways\n"
            ),
            "variables": {
                "topic": {"type": "string", "required": True, "description": "Main subject of the article"},
                "target_audience": {"type": "string", "required": True, "description": "Who will read this?"},
                "level": {"type": "string", "required": True, "description": "High-level, intermediate, or deep-dive"},
            },
        },
        {
            "slug": "research-brief",
            "name": "Research Brief Generator",
            "category": research,
            "description": "Produce a structured research brief with key findings, sources, and open questions.",
            "tags": ["research", "analysis"],
            "content": (
                "Create a concise research brief on: {topic}.\n\n"
                "Include:\n"
                "1) Executive summary (4–6 bullet points)\n"
                "2) Key insights with short explanations\n"
                "3) Notable sources (with 1–2 line annotations)\n"
                "4) Open questions / next steps\n"
            ),
            "variables": {
                "topic": {"type": "string", "required": True},
            },
        },
        {
            "slug": "email-polisher",
            "name": "Email Polisher",
            "category": product,
            "description": "Rewrite an email to be clearer, friendlier, and more effective.",
            "tags": ["email", "rewrite", "tone"],
            "content": (
                "Please rewrite the following email to be clear, concise, and kind.\n\n"
                "Tone guidelines: {tone}.\n\n"
                "Original email:\n"
                "---\n{email}\n---\n\n"
                "Return only the improved email body."
            ),
            "variables": {
                "email": {"type": "string", "required": True},
                "tone": {"type": "string", "required": False, "default": "professional and friendly"},
            },
        },
        {
            "slug": "pr-review-checklist",
            "name": "PR Code Review Checklist",
            "category": engineering,
            "description": "A quick, reusable checklist to apply when reviewing pull requests.",
            "tags": ["engineering", "review", "checklist"],
            "content": (
                "Use this checklist during code review:\n\n"
                "- Correctness: logic, edge cases, and error handling\n"
                "- Tests: coverage for core paths and tricky cases\n"
                "- Readability: naming, structure, comments where needed\n"
                "- Security: input validation, secrets, and data handling\n"
                "- Performance: obvious hot paths, unnecessary work\n"
                "- Consistency: style and patterns used in the repository\n"
            ),
            "variables": {},  # No variables
        },
        {
            "slug": "standup-summarizer",
            "name": "Daily Standup Summarizer",
            "category": product,
            "description": "Summarize daily updates into a crisp standup-style report.",
            "tags": ["ops", "summary", "standup"],
            "content": (
                "Summarize the following updates into standup format:\n\n"
                "Yesterday:\n{yesterday}\n\n"
                "Today:\n{today}\n\n"
                "Blockers:\n{blockers}\n\n"
                "Return a concise, well-formatted summary with bullet points."
            ),
            "variables": {
                "yesterday": {"type": "string", "required": False},
                "today": {"type": "string", "required": False},
                "blockers": {"type": "string", "required": False},
            },
        },
        {
            "slug": "sql-query-builder",
            "name": "SQL Query Builder",
            "category": data,
            "description": "Generate a safe, readable SQL query for a data question based on a schema.",
            "tags": ["data", "sql", "analysis"],
            "content": (
                "You are a helpful data analyst.\n\n"
                "Task: Generate an SQL query to answer the question.\n\n"
                "Schema:\n{schema}\n\n"
                "Question:\n{question}\n\n"
                "Guidelines:\n"
                "- Use CTEs for clarity when helpful\n"
                "- Add brief inline comments for non-trivial steps\n"
                "- Avoid vendor-specific features unless required\n"
                "- Do not drop or modify tables\n\n"
                "Return only the SQL code block."
            ),
            "variables": {
                "schema": {"type": "string", "required": True, "description": "DDL or table/column descriptions"},
                "question": {"type": "string", "required": True},
            },
        },
        {
            "slug": "bug-triage",
            "name": "Bug Triage",
            "category": engineering,
            "description": "Summarize a bug report and propose severity, impact, and next steps.",
            "tags": ["engineering", "qa", "triage"],
            "content": (
                "Summarize and triage the following bug report.\n\n"
                "Title: {title}\n\n"
                "Description:\n{description}\n\n"
                "Logs (optional):\n{logs}\n\n"
                "Provide:\n"
                "- Summary\n"
                "- Severity (Critical/High/Medium/Low)\n"
                "- Impact\n"
                "- Likely root cause\n"
                "- Next steps and owner suggestions\n"
            ),
            "variables": {
                "title": {"type": "string", "required": True},
                "description": {"type": "string", "required": True},
                "logs": {"type": "string", "required": False},
            },
        },
        {
            "slug": "landing-page-hero",
            "name": "Landing Page Hero Copy",
            "category": marketing,
            "description": "Craft a compelling hero headline and subheadline for a product landing page.",
            "tags": ["marketing", "copy", "landing-page"],
            "content": (
                "Create a hero section for a landing page.\n\n"
                "Product: {product_name}\n"
                "Audience: {audience}\n"
                "Primary benefit: {benefit}\n"
                "Tone: {tone}\n\n"
                "Return:\n"
                "- Headline (<= 8 words)\n"
                "- Subheadline (1–2 short sentences)\n"
                "- 3 supporting bullets\n"
            ),
            "variables": {
                "product_name": {"type": "string", "required": True},
                "audience": {"type": "string", "required": True},
                "benefit": {"type": "string", "required": True},
                "tone": {"type": "string", "required": False, "default": "clear, confident, approachable"},
            },
        },
        {
            "slug": "meeting-notes-summarizer",
            "name": "Meeting Notes Summarizer",
            "category": product,
            "description": "Summarize meeting transcript into decisions, action items, and risks.",
            "tags": ["ops", "meeting", "summary"],
            "content": (
                "Summarize the following meeting transcript.\n\n"
                "Transcript:\n{transcript}\n\n"
                "Return:\n"
                "- Decisions\n"
                "- Action items (with owners and due dates if present)\n"
                "- Risks / open questions\n"
            ),
            "variables": {
                "transcript": {"type": "string", "required": True},
            },
        },
        {
            "slug": "code-explainer",
            "name": "Code Explainer",
            "category": engineering,
            "description": "Explain what a code snippet does and identify potential issues.",
            "tags": ["engineering", "explain", "code"],
            "content": (
                "Explain the following {language} code.\n\n"
                "Code:\n"
                "---\n{code}\n---\n\n"
                "Provide:\n"
                "- High-level summary\n"
                "- Step-by-step explanation\n"
                "- Potential issues (correctness, security, performance)\n"
                "- Refactoring suggestions if any\n"
            ),
            "variables": {
                "code": {"type": "string", "required": True},
                "language": {"type": "string", "required": False, "default": "auto-detect"},
            },
        },
        {
            "slug": "user-story-generator",
            "name": "User Story Generator",
            "category": product,
            "description": "Create user stories with persona, goal, and acceptance tests.",
            "tags": ["product", "agile", "story"],
            "content": (
                "Create user stories for the following feature.\n\n"
                "Feature: {feature}\n"
                "Persona: {persona}\n"
                "Goal: {goal}\n\n"
                "Return multiple stories with concise acceptance tests (Gherkin if helpful)."
            ),
            "variables": {
                "feature": {"type": "string", "required": True},
                "persona": {"type": "string", "required": True},
                "goal": {"type": "string", "required": True},
            },
        },
        {
            "slug": "acceptance-criteria",
            "name": "Acceptance Criteria",
            "category": product,
            "description": "Draft acceptance criteria from a user story.",
            "tags": ["product", "qa", "criteria"],
            "content": (
                "Generate acceptance criteria for this user story:\n\n{user_story}\n\n"
                "Return a short, testable checklist."
            ),
            "variables": {
                "user_story": {"type": "string", "required": True},
            },
        },
        {
            "slug": "api-design-outline",
            "name": "API Design Outline",
            "category": engineering,
            "description": "Draft a high-level API design with resources, endpoints, and constraints.",
            "tags": ["engineering", "api", "design"],
            "content": (
                "Create an API design outline for the service.\n\n"
                "Service: {service}\n"
                "Known endpoints (optional): {endpoints}\n"
                "Constraints (optional): {constraints}\n\n"
                "Return:\n"
                "- Resources & relationships\n"
                "- Endpoints with verbs\n"
                "- Request/response shapes (concise)\n"
                "- Auth and rate limiting\n"
                "- Error handling\n"
            ),
            "variables": {
                "service": {"type": "string", "required": True},
                "endpoints": {"type": "string", "required": False},
                "constraints": {"type": "string", "required": False},
            },
        },
        {
            "slug": "data-analysis-plan",
            "name": "Data Analysis Plan",
            "category": data,
            "description": "Outline an analysis plan for a data question with methods and pitfalls.",
            "tags": ["data", "analysis", "plan"],
            "content": (
                "Create an analysis plan for the question.\n\n"
                "Question: {question}\n"
                "Data sources (optional): {data_sources}\n\n"
                "Return:\n"
                "- Hypotheses & definitions\n"
                "- Methods & validation\n"
                "- Metrics & visualizations\n"
                "- Pitfalls & assumptions\n"
            ),
            "variables": {
                "question": {"type": "string", "required": True},
                "data_sources": {"type": "string", "required": False},
            },
        },
        {
            "slug": "social-post-writer",
            "name": "Social Post Writer",
            "category": marketing,
            "description": "Write a concise social post tailored to a platform.",
            "tags": ["marketing", "social", "copy"],
            "content": (
                "Write a social post about: {topic}.\n"
                "Platform: {platform}.\n"
                "Tone: {tone}.\n\n"
                "Return 2–3 variants with hashtags where appropriate; keep it concise."
            ),
            "variables": {
                "topic": {"type": "string", "required": True},
                "platform": {"type": "string", "required": True},
                "tone": {"type": "string", "required": False, "default": "upbeat and informative"},
            },
        },
        {
            "slug": "release-notes",
            "name": "Release Notes Generator",
            "category": product,
            "description": "Turn a list of changes into clear, user-facing release notes.",
            "tags": ["product", "release", "notes"],
            "content": (
                "Create user-facing release notes for version {version}.\n\n"
                "Changes:\n{changes}\n\n"
                "Return categorized notes (Improvements, Fixes, Breaking) with a short intro."
            ),
            "variables": {
                "changes": {"type": "string", "required": True},
                "version": {"type": "string", "required": False, "default": "next"},
            },
        },
        {
            "slug": "support-reply",
            "name": "Support Reply Composer",
            "category": support,
            "description": "Draft an empathetic support response with next steps.",
            "tags": ["support", "cs", "reply"],
            "content": (
                "Write a support reply.\n\n"
                "User message:\n{user_message}\n\n"
                "Context (optional): {context}\n"
                "Tone: {tone}\n\n"
                "Return a short, empathetic message with clear next steps."
            ),
            "variables": {
                "user_message": {"type": "string", "required": True},
                "context": {"type": "string", "required": False},
                "tone": {"type": "string", "required": False, "default": "empathetic and solution-oriented"},
            },
        },
        {
            "slug": "ux-microcopy",
            "name": "UX Microcopy",
            "category": design,
            "description": "Generate concise, user-friendly microcopy for UI elements.",
            "tags": ["design", "ux", "copy"],
            "content": (
                "Generate UX microcopy.\n\n"
                "Context: {context}\n"
                "Constraints: {constraints}\n"
                "Style: {style}\n\n"
                "Return 3 options; keep each under 120 characters."
            ),
            "variables": {
                "context": {"type": "string", "required": True, "description": "Where will this copy appear?"},
                "constraints": {"type": "string", "required": False},
                "style": {"type": "string", "required": False, "default": "concise, friendly, accessible"},
            },
        },
    ]

    for p in prompts:
        if _exists_slug(db, tenant_id, p["slug"]):
            continue

        tpl = PromptTemplate(
            tenant_id=tenant_id,
            user_id=1,  # system/admin user; adjust if needed
            category_id=p["category"].id,
            name=p["name"],
            slug=p["slug"],
            description=p.get("description"),
            content=p["content"],
            tags=p.get("tags", []),
            variables=p.get("variables", {}),
            is_public=False,
            is_command_enabled=True,
        )
        db.add(tpl)

    db.commit()
