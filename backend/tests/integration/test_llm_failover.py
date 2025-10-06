"""
Integration Test: LLM Provider Failover

This test validates:
1. Primary LLM provider failures are detected
2. Automatic failover to secondary provider
3. Request retry logic with exponential backoff
4. Provider health checking
5. Graceful degradation when all providers fail
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from src.services.llm_service import LLMService, LLMProviderError
from src.models import LLMProvider


class TestLLMProviderFailover:
    """Test suite for LLM provider failover logic."""

    @pytest.fixture
    async def primary_provider(self, db_session, test_tenant):
        """Create primary OpenAI provider."""
        provider = LLMProvider(
            id="primary-id",
            tenant_id=test_tenant.id,
            name="Primary OpenAI",
            provider_type="openai",
            api_credentials="encrypted-key-1",  # Would be encrypted in real impl
            config={"model": "gpt-4", "temperature": 0.7},
            is_active=True,
        )
        db_session.add(provider)
        await db_session.commit()
        return provider

    @pytest.fixture
    async def secondary_provider(self, db_session, test_tenant):
        """Create secondary Anthropic provider."""
        provider = LLMProvider(
            id="secondary-id",
            tenant_id=test_tenant.id,
            name="Secondary Anthropic",
            provider_type="anthropic",
            api_credentials="encrypted-key-2",
            config={"model": "claude-3-opus", "temperature": 0.7},
            is_active=True,
        )
        db_session.add(provider)
        await db_session.commit()
        return provider

    @pytest.mark.asyncio
    async def test_successful_primary_request(self, db_session, primary_provider):
        """Test normal request without failover."""
        llm_service = LLMService(db_session)

        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value = Mock(
                choices=[Mock(message=Mock(content="Test response"))]
            )

            response = await llm_service.complete(
                provider_id=primary_provider.id,
                messages=[{"role": "user", "content": "Test prompt"}],
            )

            assert response["content"] == "Test response"
            assert response["provider_used"] == "primary-id"
            mock_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_failover_on_primary_error(
        self, db_session, primary_provider, secondary_provider
    ):
        """Test failover to secondary when primary fails."""
        llm_service = LLMService(db_session)

        # Configure failover
        await llm_service.set_failover_chain(
            primary_id=primary_provider.id, secondary_ids=[secondary_provider.id]
        )

        with patch("litellm.completion") as mock_completion:
            # First call (primary) fails
            # Second call (secondary) succeeds
            mock_completion.side_effect = [
                LLMProviderError("Primary provider unavailable"),
                Mock(choices=[Mock(message=Mock(content="Failover response"))]),
            ]

            response = await llm_service.complete(
                provider_id=primary_provider.id,
                messages=[{"role": "user", "content": "Test prompt"}],
            )

            assert response["content"] == "Failover response"
            assert response["provider_used"] == "secondary-id"
            assert response["failover_occurred"] is True
            assert mock_completion.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, db_session, primary_provider):
        """Test retry logic with exponential backoff."""
        llm_service = LLMService(db_session)

        with patch("litellm.completion") as mock_completion:
            # Fail twice, then succeed
            mock_completion.side_effect = [
                LLMProviderError("Rate limit"),
                LLMProviderError("Rate limit"),
                Mock(choices=[Mock(message=Mock(content="Success after retry"))]),
            ]

            start_time = asyncio.get_event_loop().time()

            response = await llm_service.complete(
                provider_id=primary_provider.id,
                messages=[{"role": "user", "content": "Test"}],
                max_retries=3,
            )

            elapsed = asyncio.get_event_loop().time() - start_time

            assert response["content"] == "Success after retry"
            assert mock_completion.call_count == 3
            # Verify exponential backoff occurred (should take > 1 second for 2 retries)
            assert elapsed > 1.0  # 1s backoff + 2s backoff

    @pytest.mark.asyncio
    async def test_all_providers_fail(
        self, db_session, primary_provider, secondary_provider
    ):
        """Test behavior when all providers in chain fail."""
        llm_service = LLMService(db_session)

        await llm_service.set_failover_chain(
            primary_id=primary_provider.id, secondary_ids=[secondary_provider.id]
        )

        with patch("litellm.completion") as mock_completion:
            mock_completion.side_effect = LLMProviderError("All providers down")

            with pytest.raises(LLMProviderError, match="All providers failed"):
                await llm_service.complete(
                    provider_id=primary_provider.id,
                    messages=[{"role": "user", "content": "Test"}],
                )

            # Should have tried both providers
            assert mock_completion.call_count >= 2

    @pytest.mark.asyncio
    async def test_provider_health_check(self, db_session, primary_provider):
        """Test provider health check functionality."""
        llm_service = LLMService(db_session)

        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value = Mock(
                choices=[Mock(message=Mock(content="ok"))]
            )

            health = await llm_service.check_provider_health(primary_provider.id)

            assert health["status"] == "healthy"
            assert health["latency_ms"] > 0
            assert health["provider_id"] == primary_provider.id

    @pytest.mark.asyncio
    async def test_provider_health_check_failure(self, db_session, primary_provider):
        """Test health check when provider is down."""
        llm_service = LLMService(db_session)

        with patch("litellm.completion") as mock_completion:
            mock_completion.side_effect = Exception("Connection refused")

            health = await llm_service.check_provider_health(primary_provider.id)

            assert health["status"] == "unhealthy"
            assert "error" in health
            assert health["provider_id"] == primary_provider.id

    @pytest.mark.asyncio
    async def test_streaming_with_failover(
        self, db_session, primary_provider, secondary_provider
    ):
        """Test streaming responses with failover."""
        llm_service = LLMService(db_session)

        await llm_service.set_failover_chain(
            primary_id=primary_provider.id, secondary_ids=[secondary_provider.id]
        )

        async def mock_stream_primary():
            raise LLMProviderError("Stream failed")

        async def mock_stream_secondary():
            for chunk in ["Hello", " ", "World"]:
                yield {"delta": {"content": chunk}}

        with patch("litellm.completion") as mock_completion:
            mock_completion.side_effect = [mock_stream_primary(), mock_stream_secondary()]

            chunks = []
            async for chunk in llm_service.complete_stream(
                provider_id=primary_provider.id,
                messages=[{"role": "user", "content": "Test"}],
            ):
                chunks.append(chunk["delta"]["content"])

            assert "".join(chunks) == "Hello World"

    @pytest.mark.asyncio
    async def test_cost_tracking_across_failover(
        self, db_session, primary_provider, secondary_provider
    ):
        """Test that usage costs are tracked correctly during failover."""
        llm_service = LLMService(db_session)

        await llm_service.set_failover_chain(
            primary_id=primary_provider.id, secondary_ids=[secondary_provider.id]
        )

        with patch("litellm.completion") as mock_completion:
            mock_completion.side_effect = [
                LLMProviderError("Primary fail"),
                Mock(
                    choices=[Mock(message=Mock(content="Response"))],
                    usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                ),
            ]

            response = await llm_service.complete(
                provider_id=primary_provider.id,
                messages=[{"role": "user", "content": "Test"}],
            )

            # Verify usage was tracked
            usage = response.get("usage")
            assert usage is not None
            assert usage["total_tokens"] == 30
            assert usage["provider_id"] == secondary_provider.id  # From secondary

            # Verify cost calculation
            assert "estimated_cost" in response

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_failover(
        self, db_session, primary_provider, secondary_provider
    ):
        """Test multiple concurrent requests don't interfere during failover."""
        llm_service = LLMService(db_session)

        await llm_service.set_failover_chain(
            primary_id=primary_provider.id, secondary_ids=[secondary_provider.id]
        )

        call_count = 0

        def mock_completion_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                # Odd calls (primary) fail
                raise LLMProviderError("Primary fail")
            else:
                # Even calls (secondary) succeed
                return Mock(
                    choices=[Mock(message=Mock(content=f"Response {call_count // 2}"))]
                )

        with patch("litellm.completion", side_effect=mock_completion_side_effect):
            # Send 5 concurrent requests
            tasks = [
                llm_service.complete(
                    provider_id=primary_provider.id,
                    messages=[{"role": "user", "content": f"Request {i}"}],
                )
                for i in range(5)
            ]

            responses = await asyncio.gather(*tasks)

            assert len(responses) == 5
            for response in responses:
                assert response["failover_occurred"] is True
                assert response["provider_used"] == secondary_provider.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
