"""Prompt suggestion service for workflow context-aware recommendations."""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from uuid import UUID
import re

from ..models import PromptTemplate, Agent, Crew, Task
from ..schemas.prompt import PromptSuggestion


class PromptSuggestionService:
    """Service for suggesting prompts based on workflow context."""

    def __init__(self, db: Session):
        self.db = db

    def _calculate_tag_score(
        self, prompt_tags: List[str], context_keywords: List[str]
    ) -> float:
        """
        Calculate tag matching score.

        Args:
            prompt_tags: Tags from the prompt
            context_keywords: Keywords extracted from context

        Returns:
            Score between 0 and 1
        """
        if not prompt_tags or not context_keywords:
            return 0.0

        matches = 0
        total = len(context_keywords)

        for keyword in context_keywords:
            keyword_lower = keyword.lower()
            for tag in prompt_tags:
                tag_lower = tag.lower()
                # Exact match
                if keyword_lower == tag_lower:
                    matches += 1
                    break
                # Partial match
                elif keyword_lower in tag_lower or tag_lower in keyword_lower:
                    matches += 0.5
                    break

        return min(matches / total, 1.0) if total > 0 else 0.0

    def _calculate_rating_score(self, average_rating: float) -> float:
        """
        Calculate rating score normalized to 0-1.

        Args:
            average_rating: Average rating (0-5)

        Returns:
            Score between 0 and 1
        """
        return average_rating / 5.0

    def _calculate_usage_score(
        self, total_executions: int, max_executions: int
    ) -> float:
        """
        Calculate usage popularity score.

        Args:
            total_executions: Number of times prompt was executed
            max_executions: Maximum executions across all prompts

        Returns:
            Score between 0 and 1
        """
        if max_executions == 0:
            return 0.0

        # Logarithmic scaling for usage to avoid over-weighting popular prompts
        import math
        return min(math.log(total_executions + 1) / math.log(max_executions + 1), 1.0)

    def _calculate_content_similarity(
        self, prompt_content: str, context_text: str
    ) -> float:
        """
        Calculate content similarity using keyword matching.

        Args:
            prompt_content: Prompt template content
            context_text: Combined context text (name, description, etc.)

        Returns:
            Score between 0 and 1
        """
        if not prompt_content or not context_text:
            return 0.0

        # Extract words (3+ chars) from both texts
        prompt_words = set(
            re.findall(r'\b[a-z]{3,}\b', prompt_content.lower())
        )
        context_words = set(
            re.findall(r'\b[a-z]{3,}\b', context_text.lower())
        )

        if not prompt_words or not context_words:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(prompt_words & context_words)
        union = len(prompt_words | context_words)

        return intersection / union if union > 0 else 0.0

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        if not text:
            return []

        # Extract words (3+ chars), filter common words
        common_words = {
            'the', 'and', 'for', 'with', 'this', 'that', 'from',
            'are', 'was', 'will', 'can', 'has', 'have', 'been',
            'you', 'your', 'our', 'their', 'them', 'what', 'when',
            'where', 'who', 'why', 'how', 'all', 'any', 'some',
        }

        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [w for w in words if w not in common_words]

    def _calculate_confidence_score(
        self,
        prompt: PromptTemplate,
        context_keywords: List[str],
        context_text: str,
        max_executions: int,
    ) -> float:
        """
        Calculate overall confidence score for a prompt.

        Weights:
        - Tag matching: 35%
        - Content similarity: 30%
        - Rating: 20%
        - Usage popularity: 15%

        Args:
            prompt: Prompt template
            context_keywords: Keywords from context
            context_text: Combined context text
            max_executions: Max executions for normalization

        Returns:
            Confidence score between 0 and 1
        """
        tag_score = self._calculate_tag_score(prompt.tags or [], context_keywords)
        content_score = self._calculate_content_similarity(
            prompt.content or '', context_text
        )
        rating_score = self._calculate_rating_score(
            float(prompt.average_rating) if prompt.average_rating else 0.0
        )
        usage_score = self._calculate_usage_score(
            prompt.total_executions or 0, max_executions
        )

        # Weighted combination
        confidence = (
            tag_score * 0.35
            + content_score * 0.30
            + rating_score * 0.20
            + usage_score * 0.15
        )

        return confidence

    async def suggest_prompts_for_agent(
        self,
        agent_name: str,
        agent_role: str,
        agent_goal: str,
        agent_backstory: Optional[str],
        tenant_id: int,
        limit: int = 5,
        min_confidence: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Suggest prompts for agent configuration.

        Args:
            agent_name: Agent name
            agent_role: Agent role
            agent_goal: Agent goal
            agent_backstory: Agent backstory
            tenant_id: Tenant ID
            limit: Maximum suggestions to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of prompt suggestions with confidence scores
        """
        # Build context
        context_text = f"{agent_name} {agent_role} {agent_goal} {agent_backstory or ''}"
        context_keywords = self._extract_keywords(context_text)

        # Add agent-specific keywords
        context_keywords.extend(['agent', 'task', 'action', 'execute', 'perform'])

        # Get active prompts
        prompts = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.is_active == True,
            )
            .all()
        )

        if not prompts:
            return []

        # Get max executions for normalization
        max_executions = max(
            (p.total_executions or 0 for p in prompts), default=0
        )

        # Calculate scores
        suggestions = []
        for prompt in prompts:
            confidence = self._calculate_confidence_score(
                prompt, context_keywords, context_text, max_executions
            )

            if confidence >= min_confidence:
                suggestions.append({
                    'prompt_id': str(prompt.id),
                    'name': prompt.name,
                    'slug': prompt.slug,
                    'description': prompt.description,
                    'confidence': round(confidence, 3),
                    'tags': prompt.tags or [],
                    'average_rating': float(prompt.average_rating) if prompt.average_rating else 0.0,
                    'total_executions': prompt.total_executions or 0,
                    'reason': self._generate_reason(prompt, context_keywords, confidence),
                })

        # Sort by confidence and limit
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:limit]

    async def suggest_prompts_for_crew(
        self,
        crew_name: str,
        crew_description: str,
        crew_process_type: str,
        tenant_id: int,
        limit: int = 5,
        min_confidence: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Suggest prompts for crew configuration.

        Args:
            crew_name: Crew name
            crew_description: Crew description
            crew_process_type: Process type (sequential, hierarchical, etc.)
            tenant_id: Tenant ID
            limit: Maximum suggestions to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of prompt suggestions with confidence scores
        """
        context_text = f"{crew_name} {crew_description} {crew_process_type}"
        context_keywords = self._extract_keywords(context_text)

        # Add crew-specific keywords
        context_keywords.extend(['crew', 'team', 'workflow', 'orchestrate', 'coordinate'])

        prompts = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.is_active == True,
            )
            .all()
        )

        if not prompts:
            return []

        max_executions = max((p.total_executions or 0 for p in prompts), default=0)

        suggestions = []
        for prompt in prompts:
            confidence = self._calculate_confidence_score(
                prompt, context_keywords, context_text, max_executions
            )

            if confidence >= min_confidence:
                suggestions.append({
                    'prompt_id': str(prompt.id),
                    'name': prompt.name,
                    'slug': prompt.slug,
                    'description': prompt.description,
                    'confidence': round(confidence, 3),
                    'tags': prompt.tags or [],
                    'average_rating': float(prompt.average_rating) if prompt.average_rating else 0.0,
                    'total_executions': prompt.total_executions or 0,
                    'reason': self._generate_reason(prompt, context_keywords, confidence),
                })

        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:limit]

    async def suggest_prompts_for_task(
        self,
        task_name: str,
        task_description: str,
        task_expected_output: Optional[str],
        tenant_id: int,
        limit: int = 5,
        min_confidence: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Suggest prompts for task configuration.

        Args:
            task_name: Task name
            task_description: Task description
            task_expected_output: Expected output
            tenant_id: Tenant ID
            limit: Maximum suggestions to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of prompt suggestions with confidence scores
        """
        context_text = f"{task_name} {task_description} {task_expected_output or ''}"
        context_keywords = self._extract_keywords(context_text)

        # Add task-specific keywords
        context_keywords.extend(['task', 'objective', 'output', 'result', 'complete'])

        prompts = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.is_active == True,
            )
            .all()
        )

        if not prompts:
            return []

        max_executions = max((p.total_executions or 0 for p in prompts), default=0)

        suggestions = []
        for prompt in prompts:
            confidence = self._calculate_confidence_score(
                prompt, context_keywords, context_text, max_executions
            )

            if confidence >= min_confidence:
                suggestions.append({
                    'prompt_id': str(prompt.id),
                    'name': prompt.name,
                    'slug': prompt.slug,
                    'description': prompt.description,
                    'confidence': round(confidence, 3),
                    'tags': prompt.tags or [],
                    'average_rating': float(prompt.average_rating) if prompt.average_rating else 0.0,
                    'total_executions': prompt.total_executions or 0,
                    'reason': self._generate_reason(prompt, context_keywords, confidence),
                })

        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:limit]

    async def suggest_prompts_for_flow(
        self,
        flow_name: str,
        flow_description: str,
        tenant_id: int,
        limit: int = 5,
        min_confidence: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Suggest prompts for flow configuration.

        Args:
            flow_name: Flow name
            flow_description: Flow description
            tenant_id: Tenant ID
            limit: Maximum suggestions to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of prompt suggestions with confidence scores
        """
        context_text = f"{flow_name} {flow_description}"
        context_keywords = self._extract_keywords(context_text)

        # Add flow-specific keywords
        context_keywords.extend(['flow', 'pipeline', 'process', 'automation', 'sequence'])

        prompts = (
            self.db.query(PromptTemplate)
            .filter(
                PromptTemplate.tenant_id == tenant_id,
                PromptTemplate.is_active == True,
            )
            .all()
        )

        if not prompts:
            return []

        max_executions = max((p.total_executions or 0 for p in prompts), default=0)

        suggestions = []
        for prompt in prompts:
            confidence = self._calculate_confidence_score(
                prompt, context_keywords, context_text, max_executions
            )

            if confidence >= min_confidence:
                suggestions.append({
                    'prompt_id': str(prompt.id),
                    'name': prompt.name,
                    'slug': prompt.slug,
                    'description': prompt.description,
                    'confidence': round(confidence, 3),
                    'tags': prompt.tags or [],
                    'average_rating': float(prompt.average_rating) if prompt.average_rating else 0.0,
                    'total_executions': prompt.total_executions or 0,
                    'reason': self._generate_reason(prompt, context_keywords, confidence),
                })

        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:limit]

    def _generate_reason(
        self, prompt: PromptTemplate, context_keywords: List[str], confidence: float
    ) -> str:
        """
        Generate human-readable reason for suggestion.

        Args:
            prompt: Prompt template
            context_keywords: Context keywords
            confidence: Confidence score

        Returns:
            Reason string
        """
        reasons = []

        # Check tag matches
        if prompt.tags:
            matching_tags = [
                tag for tag in prompt.tags
                if any(kw.lower() in tag.lower() or tag.lower() in kw.lower()
                       for kw in context_keywords)
            ]
            if matching_tags:
                reasons.append(f"Tags: {', '.join(matching_tags[:3])}")

        # Check rating
        if prompt.average_rating and prompt.average_rating >= 4.0:
            reasons.append(f"Highly rated ({prompt.average_rating:.1f}★)")

        # Check usage
        if prompt.total_executions and prompt.total_executions > 10:
            reasons.append(f"Popular ({prompt.total_executions} uses)")

        # Default
        if not reasons:
            reasons.append("Content similarity")

        return " • ".join(reasons)
