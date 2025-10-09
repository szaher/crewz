"""LLM service with multi-provider support via LiteLLM."""

from typing import Optional, Dict, Any, List, AsyncIterator
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import litellm
from litellm import acompletion, completion_cost

from ..models import LLMProvider
from .encryption_service import get_encryption_service


class LLMService:
    """
    Service for LLM operations with provider abstraction.

    Supports multiple providers through LiteLLM:
    - OpenAI
    - Anthropic
    - Ollama
    - vLLM
    - Custom endpoints
    """

    def __init__(self, db: Session):
        self.db = db

    async def get_provider(self, provider_id: int) -> LLMProvider:
        """
        Get LLM provider by ID.

        Args:
            provider_id: Provider ID

        Returns:
            LLMProvider model

        Raises:
            HTTPException: If provider not found or inactive
        """
        provider = (
            self.db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
        )

        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LLM provider not found",
            )

        if not provider.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="LLM provider is inactive",
            )

        return provider

    def _build_litellm_params(self, provider: LLMProvider) -> Dict[str, Any]:
        """
        Build LiteLLM parameters from provider config.

        Args:
            provider: LLMProvider model

        Returns:
            Dict of parameters for litellm.acompletion()
        """
        params = {
            "model": provider.model_name,
        }

        # Decrypt API key if present (use the same encryption service as provider CRUD)
        if provider.api_key:
            try:
                enc = get_encryption_service()
                params["api_key"] = enc.decrypt(provider.api_key)
            except Exception as e:
                # Provide a clearer error upstream
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LLM provider credentials invalid or cannot be decrypted",
                )

        # Set API base for custom providers
        if provider.api_base:
            params["api_base"] = provider.api_base

        # Add provider-specific config
        if provider.config:
            params.update(provider.config)

        return params

    async def chat_completion(
        self,
        provider_id: int,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate a chat completion.

        Args:
            provider_id: LLM provider ID
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters for LiteLLM

        Returns:
            Completion response dict

        Raises:
            HTTPException: If completion fails
        """
        provider = await self.get_provider(provider_id)
        litellm_params = self._build_litellm_params(provider)

        try:
            response = await acompletion(
                **litellm_params,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )

            return response
        except Exception as e:
            msg = str(e)
            # Provide clearer client error for common misconfigurations
            if "Decryption failed" in msg or "api key" in msg.lower() or "authentication" in msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="LLM provider credentials invalid or missing",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM completion failed: {msg}",
            )

    async def chat_completion_stream(
        self,
        provider_id: int,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Generate a streaming chat completion.

        Args:
            provider_id: LLM provider ID
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Yields:
            Streamed response chunks

        Raises:
            HTTPException: If streaming fails
        """
        provider = await self.get_provider(provider_id)
        litellm_params = self._build_litellm_params(provider)

        try:
            response = await acompletion(
                **litellm_params,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM streaming failed: {str(e)}",
            )

    async def create_provider(
        self,
        name: str,
        provider_type: str,
        model_name: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        is_default: bool = False,
    ) -> LLMProvider:
        """
        Create a new LLM provider.

        Args:
            name: Provider display name
            provider_type: Provider type (openai, anthropic, ollama, vllm, custom)
            model_name: Model identifier
            api_key: API key (will be encrypted)
            api_base: Custom API base URL
            config: Additional configuration
            is_default: Whether this is the default provider

        Returns:
            Created LLMProvider

        Raises:
            HTTPException: If creation fails
        """
        # Encrypt API key if provided (consistent with provider service)
        encrypted_key = None
        if api_key:
            enc = get_encryption_service()
            encrypted_key = enc.encrypt(api_key)

        provider = LLMProvider(
            name=name,
            provider_type=provider_type,
            model_name=model_name,
            api_key=encrypted_key,
            api_base=api_base,
            config=config or {},
            is_active=True,
            is_default=is_default,
        )

        # If setting as default, unset other defaults
        if is_default:
            self.db.query(LLMProvider).update({"is_default": False})

        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)

        return provider

    async def get_default_provider(self) -> Optional[LLMProvider]:
        """
        Get the default LLM provider.

        Returns:
            Default LLMProvider or None
        """
        return (
            self.db.query(LLMProvider)
            .filter(LLMProvider.is_default == True, LLMProvider.is_active == True)
            .first()
        )

    async def list_providers(
        self, active_only: bool = True
    ) -> List[LLMProvider]:
        """
        List all LLM providers.

        Args:
            active_only: Only return active providers

        Returns:
            List of LLMProvider models
        """
        query = self.db.query(LLMProvider)

        if active_only:
            query = query.filter(LLMProvider.is_active == True)

        return query.all()
