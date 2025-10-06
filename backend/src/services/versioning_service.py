"""Versioning service for tracking configuration changes with diff and rollback support."""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Session
from datetime import datetime
import json

if TYPE_CHECKING:
    from ..models.agent_version import AgentVersion
    from ..models.provider_version import ProviderVersion
    from ..models.agent import Agent
    from ..models.llm_provider import LLMProvider


class VersioningService:
    """
    Service for managing version history, diffs, and rollbacks.

    Supports both Agent and Provider versioning.
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def generate_diff(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a diff between two configurations.

        Args:
            old_config: Previous configuration
            new_config: New configuration

        Returns:
            Dictionary with 'added', 'modified', 'removed' keys
        """
        diff = {
            "added": {},
            "modified": {},
            "removed": {}
        }

        # Find added and modified keys
        for key, new_value in new_config.items():
            if key not in old_config:
                diff["added"][key] = new_value
            elif old_config[key] != new_value:
                diff["modified"][key] = {
                    "old": old_config[key],
                    "new": new_value
                }

        # Find removed keys
        for key, old_value in old_config.items():
            if key not in new_config:
                diff["removed"][key] = old_value

        return diff

    @staticmethod
    def config_to_dict(obj: Any, exclude_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Convert a model object to a configuration dictionary.

        Args:
            obj: SQLAlchemy model object
            exclude_fields: Fields to exclude from the configuration

        Returns:
            Dictionary representation of the object
        """
        exclude = exclude_fields or ['id', 'created_at', 'updated_at', 'versions']
        config = {}

        for column in obj.__table__.columns:
            if column.name not in exclude:
                value = getattr(obj, column.name)
                # Handle datetime serialization
                if isinstance(value, datetime):
                    config[column.name] = value.isoformat()
                # Handle enum serialization
                elif hasattr(value, 'value'):
                    config[column.name] = value.value
                else:
                    config[column.name] = value

        return config

    def create_agent_version(
        self,
        agent_id: int,
        configuration: Dict[str, Any],
        action: str,
        changed_by_user_id: Optional[int] = None,
        change_description: Optional[str] = None
    ) -> "AgentVersion":
        """
        Create a new agent version.

        Args:
            agent_id: Agent ID
            configuration: Complete agent configuration
            action: Version action (create, update, rollback)
            changed_by_user_id: User who made the change
            change_description: Description of the change

        Returns:
            Created AgentVersion object
        """
        from ..models.agent_version import AgentVersion, VersionAction

        # Get the latest version number
        latest_version = (
            self.db.query(AgentVersion)
            .filter(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_number.desc())
            .first()
        )

        version_number = 1 if not latest_version else latest_version.version_number + 1

        # Generate diff if there's a previous version
        diff_from_previous = None
        if latest_version:
            diff_from_previous = self.generate_diff(
                latest_version.configuration,
                configuration
            )

        version = AgentVersion(
            agent_id=agent_id,
            version_number=version_number,
            action=VersionAction(action),
            changed_by_user_id=changed_by_user_id,
            configuration=configuration,
            diff_from_previous=diff_from_previous,
            change_description=change_description
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        return version

    def create_provider_version(
        self,
        provider_id: int,
        configuration: Dict[str, Any],
        action: str,
        changed_by_user_id: Optional[int] = None,
        change_description: Optional[str] = None
    ) -> "ProviderVersion":
        """
        Create a new provider version.

        Args:
            provider_id: Provider ID
            configuration: Complete provider configuration (with encrypted API key)
            action: Version action (create, update, rollback)
            changed_by_user_id: User who made the change
            change_description: Description of the change

        Returns:
            Created ProviderVersion object
        """
        from ..models.provider_version import ProviderVersion, VersionAction

        # Get the latest version number
        latest_version = (
            self.db.query(ProviderVersion)
            .filter(ProviderVersion.provider_id == provider_id)
            .order_by(ProviderVersion.version_number.desc())
            .first()
        )

        version_number = 1 if not latest_version else latest_version.version_number + 1

        # Generate diff if there's a previous version
        diff_from_previous = None
        if latest_version:
            # Exclude API key from diff for security
            old_config = {k: v for k, v in latest_version.configuration.items() if k != 'api_key'}
            new_config = {k: v for k, v in configuration.items() if k != 'api_key'}
            diff_from_previous = self.generate_diff(old_config, new_config)

            # Add API key change indicator
            if latest_version.configuration.get('api_key') != configuration.get('api_key'):
                diff_from_previous['modified']['api_key'] = {
                    "old": "***encrypted***",
                    "new": "***encrypted***"
                }

        version = ProviderVersion(
            provider_id=provider_id,
            version_number=version_number,
            action=VersionAction(action),
            changed_by_user_id=changed_by_user_id,
            configuration=configuration,
            diff_from_previous=diff_from_previous,
            change_description=change_description
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        return version

    def get_agent_versions(
        self,
        agent_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> tuple[List["AgentVersion"], int]:
        """Get version history for an agent."""
        from ..models.agent_version import AgentVersion

        query = (
            self.db.query(AgentVersion)
            .filter(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.version_number.desc())
        )

        total = query.count()
        versions = query.offset(offset).limit(limit).all()

        return versions, total

    def get_provider_versions(
        self,
        provider_id: int,
        limit: int = 10,
        offset: int = 0
    ) -> tuple[List["ProviderVersion"], int]:
        """Get version history for a provider."""
        from ..models.provider_version import ProviderVersion

        query = (
            self.db.query(ProviderVersion)
            .filter(ProviderVersion.provider_id == provider_id)
            .order_by(ProviderVersion.version_number.desc())
        )

        total = query.count()
        versions = query.offset(offset).limit(limit).all()

        return versions, total

    def rollback_agent(
        self,
        agent_id: int,
        version_number: int,
        changed_by_user_id: Optional[int] = None
    ) -> "Agent":
        """
        Rollback an agent to a specific version.

        Args:
            agent_id: Agent ID
            version_number: Version number to rollback to
            changed_by_user_id: User performing the rollback

        Returns:
            Updated Agent object
        """
        from ..models.agent_version import AgentVersion
        from ..models.agent import Agent

        # Get the version to rollback to
        version = (
            self.db.query(AgentVersion)
            .filter(
                AgentVersion.agent_id == agent_id,
                AgentVersion.version_number == version_number
            )
            .first()
        )

        if not version:
            raise ValueError(f"Version {version_number} not found for agent {agent_id}")

        # Get the agent
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Apply the configuration from the version
        for key, value in version.configuration.items():
            if hasattr(agent, key):
                setattr(agent, key, value)

        self.db.commit()
        self.db.refresh(agent)

        # Create a new version entry for the rollback
        current_config = self.config_to_dict(agent)
        self.create_agent_version(
            agent_id=agent_id,
            configuration=current_config,
            action="rollback",
            changed_by_user_id=changed_by_user_id,
            change_description=f"Rolled back to version {version_number}"
        )

        return agent

    def rollback_provider(
        self,
        provider_id: int,
        version_number: int,
        changed_by_user_id: Optional[int] = None
    ) -> "LLMProvider":
        """
        Rollback a provider to a specific version.

        Args:
            provider_id: Provider ID
            version_number: Version number to rollback to
            changed_by_user_id: User performing the rollback

        Returns:
            Updated LLMProvider object
        """
        from ..models.provider_version import ProviderVersion
        from ..models.llm_provider import LLMProvider

        # Get the version to rollback to
        version = (
            self.db.query(ProviderVersion)
            .filter(
                ProviderVersion.provider_id == provider_id,
                ProviderVersion.version_number == version_number
            )
            .first()
        )

        if not version:
            raise ValueError(f"Version {version_number} not found for provider {provider_id}")

        # Get the provider
        provider = self.db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")

        # Apply the configuration from the version
        for key, value in version.configuration.items():
            if hasattr(provider, key):
                setattr(provider, key, value)

        self.db.commit()
        self.db.refresh(provider)

        # Create a new version entry for the rollback
        current_config = self.config_to_dict(provider)
        self.create_provider_version(
            provider_id=provider_id,
            configuration=current_config,
            action="rollback",
            changed_by_user_id=changed_by_user_id,
            change_description=f"Rolled back to version {version_number}"
        )

        return provider
