"""Unit tests for LLMService."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.services.llm_service import LLMService
from src.models.llm_provider import LLMProvider, LLMProviderType


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def llm_service(mock_db):
    """Create an LLMService instance with mock database."""
    return LLMService(mock_db)


@pytest.fixture
def sample_provider():
    """Create a sample LLM provider."""
    return LLMProvider(
        id=1,
        tenant_id=1,
        name="Test Provider",
        provider_type=LLMProviderType.OPENAI,
        model_name="gpt-4",
        api_key="encrypted_key_here",
        api_base=None,
        config={},
        is_active=True,
        is_default=True,
    )


class TestGetProvider:
    """Tests for get_provider method."""

    @pytest.mark.asyncio
    async def test_get_provider_success(self, llm_service, mock_db, sample_provider):
        """Test successful provider retrieval."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_provider

        # Act
        result = await llm_service.get_provider(1)

        # Assert
        assert result == sample_provider
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_get_provider_not_found(self, llm_service, mock_db):
        """Test provider not found raises 404."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await llm_service.get_provider(999)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_get_provider_inactive(self, llm_service, mock_db, sample_provider):
        """Test inactive provider raises 400."""
        # Arrange
        sample_provider.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = sample_provider

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await llm_service.get_provider(1)

        assert exc_info.value.status_code == 400
        assert "inactive" in str(exc_info.value.detail).lower()


class TestBuildLitellmParams:
    """Tests for _build_litellm_params method."""

    @patch('src.services.llm_service.decrypt_api_key')
    def test_build_params_with_api_key(self, mock_decrypt, llm_service, sample_provider):
        """Test parameter building with API key."""
        # Arrange
        mock_decrypt.return_value = "decrypted_key"

        # Act
        params = llm_service._build_litellm_params(sample_provider)

        # Assert
        assert params["model"] == "gpt-4"
        assert params["api_key"] == "decrypted_key"
        mock_decrypt.assert_called_once_with("encrypted_key_here")

    def test_build_params_without_api_key(self, llm_service):
        """Test parameter building without API key."""
        # Arrange
        provider = LLMProvider(
            id=2,
            tenant_id=1,
            name="Ollama Provider",
            provider_type=LLMProviderType.OLLAMA,
            model_name="llama2",
            api_key=None,
            api_base="http://localhost:11434",
            config={"timeout": 300},
            is_active=True,
            is_default=False,
        )

        # Act
        params = llm_service._build_litellm_params(provider)

        # Assert
        assert params["model"] == "llama2"
        assert "api_key" not in params
        assert params["api_base"] == "http://localhost:11434"
        assert params["timeout"] == 300

    def test_build_params_with_custom_config(self, llm_service):
        """Test parameter building with custom configuration."""
        # Arrange
        provider = LLMProvider(
            id=3,
            tenant_id=1,
            name="Custom Provider",
            provider_type=LLMProviderType.CUSTOM,
            model_name="custom-model",
            api_key=None,
            api_base="https://custom.api.com",
            config={"custom_param": "value", "timeout": 120},
            is_active=True,
            is_default=False,
        )

        # Act
        params = llm_service._build_litellm_params(provider)

        # Assert
        assert params["model"] == "custom-model"
        assert params["api_base"] == "https://custom.api.com"
        assert params["custom_param"] == "value"
        assert params["timeout"] == 120


class TestChatCompletion:
    """Tests for chat_completion method."""

    @pytest.mark.asyncio
    @patch('src.services.llm_service.acompletion')
    @patch('src.services.llm_service.decrypt_api_key')
    async def test_chat_completion_success(
        self, mock_decrypt, mock_acompletion, llm_service, mock_db, sample_provider
    ):
        """Test successful chat completion."""
        # Arrange
        mock_decrypt.return_value = "decrypted_key"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_provider

        mock_response = {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?"
                    }
                }
            ],
            "usage": {"total_tokens": 20}
        }
        mock_acompletion.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]

        # Act
        result = await llm_service.chat_completion(
            provider_id=1,
            messages=messages,
            temperature=0.7,
            max_tokens=100
        )

        # Assert
        assert result == mock_response
        mock_acompletion.assert_called_once()
        call_kwargs = mock_acompletion.call_args[1]
        assert call_kwargs["model"] == "gpt-4"
        assert call_kwargs["messages"] == messages
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 100

    @pytest.mark.asyncio
    @patch('src.services.llm_service.acompletion')
    @patch('src.services.llm_service.decrypt_api_key')
    async def test_chat_completion_failure(
        self, mock_decrypt, mock_acompletion, llm_service, mock_db, sample_provider
    ):
        """Test chat completion with LiteLLM error."""
        # Arrange
        mock_decrypt.return_value = "decrypted_key"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_provider
        mock_acompletion.side_effect = Exception("API rate limit exceeded")

        messages = [{"role": "user", "content": "Hello"}]

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await llm_service.chat_completion(provider_id=1, messages=messages)

        assert exc_info.value.status_code == 500
        assert "LLM completion failed" in str(exc_info.value.detail)
        assert "rate limit" in str(exc_info.value.detail)


class TestCreateProvider:
    """Tests for create_provider method."""

    @pytest.mark.asyncio
    @patch('src.services.llm_service.encrypt_api_key')
    async def test_create_provider_success(self, mock_encrypt, llm_service, mock_db):
        """Test successful provider creation."""
        # Arrange
        mock_encrypt.return_value = "encrypted_key"
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # Act
        result = await llm_service.create_provider(
            name="New Provider",
            provider_type="openai",
            model_name="gpt-4",
            api_key="sk-test-key",
            api_base=None,
            config={"temperature": 0.7},
            is_default=False,
        )

        # Assert
        assert result.name == "New Provider"
        assert result.provider_type == "openai"
        assert result.model_name == "gpt-4"
        assert result.api_key == "encrypted_key"
        assert result.config == {"temperature": 0.7}
        mock_encrypt.assert_called_once_with("sk-test-key")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.services.llm_service.encrypt_api_key')
    async def test_create_provider_as_default(self, mock_encrypt, llm_service, mock_db):
        """Test creating provider as default unsets other defaults."""
        # Arrange
        mock_encrypt.return_value = "encrypted_key"
        mock_query = Mock()
        mock_db.query.return_value = mock_query
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # Act
        await llm_service.create_provider(
            name="Default Provider",
            provider_type="anthropic",
            model_name="claude-3-opus-20240229",
            api_key="sk-ant-key",
            is_default=True,
        )

        # Assert
        mock_query.update.assert_called_once_with({"is_default": False})

    @pytest.mark.asyncio
    async def test_create_provider_without_api_key(self, llm_service, mock_db):
        """Test creating provider without API key (e.g., Ollama)."""
        # Arrange
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # Act
        result = await llm_service.create_provider(
            name="Ollama",
            provider_type="ollama",
            model_name="llama2",
            api_key=None,
            api_base="http://localhost:11434",
        )

        # Assert
        assert result.name == "Ollama"
        assert result.api_key is None
        assert result.api_base == "http://localhost:11434"


class TestGetDefaultProvider:
    """Tests for get_default_provider method."""

    @pytest.mark.asyncio
    async def test_get_default_provider_exists(self, llm_service, mock_db, sample_provider):
        """Test retrieving default provider."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = sample_provider

        # Act
        result = await llm_service.get_default_provider()

        # Assert
        assert result == sample_provider
        assert result.is_default is True

    @pytest.mark.asyncio
    async def test_get_default_provider_not_exists(self, llm_service, mock_db):
        """Test when no default provider exists."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act
        result = await llm_service.get_default_provider()

        # Assert
        assert result is None


class TestListProviders:
    """Tests for list_providers method."""

    @pytest.mark.asyncio
    async def test_list_providers_active_only(self, llm_service, mock_db):
        """Test listing only active providers."""
        # Arrange
        providers = [
            MagicMock(id=1, is_active=True),
            MagicMock(id=2, is_active=True),
        ]
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = providers
        mock_db.query.return_value = mock_query

        # Act
        result = await llm_service.list_providers(active_only=True)

        # Assert
        assert len(result) == 2
        assert all(p.is_active for p in result)
        mock_query.filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_providers_all(self, llm_service, mock_db):
        """Test listing all providers including inactive."""
        # Arrange
        providers = [
            MagicMock(id=1, is_active=True),
            MagicMock(id=2, is_active=False),
        ]
        mock_query = Mock()
        mock_query.all.return_value = providers
        mock_db.query.return_value = mock_query

        # Act
        result = await llm_service.list_providers(active_only=False)

        # Assert
        assert len(result) == 2
        mock_query.all.assert_called_once()
