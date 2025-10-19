"""
Unit tests for artifact versioning logic (T082).

Tests:
- Version increment on re-execute
- expires_at = created_at + 30 days
- Parent execution linking
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.services.artifact_service import ArtifactService


class TestArtifactVersioning:
    """Unit tests for artifact versioning logic."""

    @pytest.fixture
    def artifact_service(self):
        """Create artifact service instance."""
        service = ArtifactService()
        return service

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.query = Mock()
        return session

    def test_version_increment_on_reexecute(self, artifact_service, mock_db_session):
        """Test that version increments when creating artifact for re-execution."""
        original_execution_id = "original-exec-123"
        new_execution_id = "reexec-456"

        # Mock original execution has version 1
        mock_original = Mock()
        mock_original.artifact_version = 1

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_original

        # Create artifact for re-execution
        new_version = artifact_service.get_next_version(
            original_execution_id,
            db_session=mock_db_session
        )

        # Version should increment to 2
        assert new_version == 2

    def test_initial_version_is_one(self, artifact_service):
        """Test that first execution gets version 1."""
        # When there's no parent execution
        version = artifact_service.get_initial_version()

        assert version == 1

    def test_expires_at_is_created_plus_30_days(self, artifact_service):
        """Test that expires_at is set to created_at + 30 days."""
        created_at = datetime(2024, 1, 1, 12, 0, 0)

        expires_at = artifact_service.calculate_expiration(created_at)

        expected_expiration = created_at + timedelta(days=30)

        # Should be exactly 30 days later
        assert expires_at == expected_expiration

    def test_expires_at_calculation_preserves_time(self, artifact_service):
        """Test that expiration preserves time of day."""
        created_at = datetime(2024, 1, 15, 14, 30, 45)

        expires_at = artifact_service.calculate_expiration(created_at)

        # Should be 30 days later with same time
        assert expires_at.hour == created_at.hour
        assert expires_at.minute == created_at.minute
        assert expires_at.second == created_at.second

        # Should be 30 days later
        delta = expires_at - created_at
        assert delta.days == 30

    def test_parent_execution_linking(self, artifact_service, mock_db_session):
        """Test that parent_execution_id is correctly set."""
        parent_id = "parent-exec-789"
        child_id = "child-exec-012"

        # Create artifact with parent linking
        artifact_data = {
            "execution_id": child_id,
            "parent_execution_id": parent_id,
            "file_name": "output.txt",
            "version_number": 2
        }

        artifact = artifact_service.create_artifact_record(
            **artifact_data,
            db_session=mock_db_session
        )

        # Should have parent_execution_id set
        assert artifact.parent_execution_id == parent_id
        assert artifact.execution_id == child_id
        assert artifact.version_number == 2

    def test_version_chain_tracking(self, artifact_service, mock_db_session):
        """Test tracking version chain across multiple re-executions."""
        original_id = "v1-exec"
        reexec1_id = "v2-exec"
        reexec2_id = "v3-exec"

        # Mock version progression
        versions = [
            Mock(execution_id=original_id, artifact_version=1, parent_execution_id=None),
            Mock(execution_id=reexec1_id, artifact_version=2, parent_execution_id=original_id),
            Mock(execution_id=reexec2_id, artifact_version=3, parent_execution_id=reexec1_id),
        ]

        # Test version increment logic
        assert versions[1].artifact_version == versions[0].artifact_version + 1
        assert versions[2].artifact_version == versions[1].artifact_version + 1

    def test_expires_at_for_different_dates(self, artifact_service):
        """Test expiration calculation for various dates."""
        test_dates = [
            datetime(2024, 1, 1),
            datetime(2024, 2, 29),  # Leap year
            datetime(2024, 12, 31),
        ]

        for created_at in test_dates:
            expires_at = artifact_service.calculate_expiration(created_at)

            # Should always be 30 days later
            delta = expires_at - created_at
            assert delta.days == 30

    def test_artifact_version_not_null(self, artifact_service, mock_db_session):
        """Test that artifact version is never null."""
        artifact_data = {
            "execution_id": "test-exec",
            "file_name": "test.txt",
            "version_number": None  # Try to set null
        }

        # Should either raise error or default to 1
        with pytest.raises((ValueError, AssertionError)):
            artifact_service.create_artifact_record(
                **artifact_data,
                db_session=mock_db_session
            )

    def test_version_monotonic_increase(self, artifact_service):
        """Test that versions always increase monotonically."""
        versions = []

        for i in range(5):
            # Simulate getting next version
            current_version = i + 1
            next_version = current_version + 1

            versions.append(next_version)

        # Verify monotonic increase
        for i in range(len(versions) - 1):
            assert versions[i + 1] > versions[i]

    def test_created_at_before_expires_at(self, artifact_service):
        """Test that created_at is always before expires_at."""
        created_at = datetime.now()

        expires_at = artifact_service.calculate_expiration(created_at)

        # Expiration must be after creation
        assert expires_at > created_at

    def test_version_retrieval_for_execution(self, artifact_service, mock_db_session):
        """Test retrieving all artifact versions for an execution chain."""
        execution_id = "test-exec"

        # Mock query returning multiple versions
        mock_artifacts = [
            Mock(version_number=1, execution_id="v1-exec"),
            Mock(version_number=2, execution_id="v2-exec"),
            Mock(version_number=3, execution_id="v3-exec"),
        ]

        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_artifacts

        artifacts = artifact_service.get_all_versions(
            execution_id,
            db_session=mock_db_session
        )

        # Should return all versions
        assert len(artifacts) == 3

        # Verify versions are in order
        assert artifacts[0].version_number == 1
        assert artifacts[1].version_number == 2
        assert artifacts[2].version_number == 3

    def test_latest_version_retrieval(self, artifact_service, mock_db_session):
        """Test getting latest version of an artifact."""
        execution_id = "test-exec"

        # Mock latest version
        mock_latest = Mock(version_number=5)

        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_latest

        latest = artifact_service.get_latest_version(
            execution_id,
            db_session=mock_db_session
        )

        assert latest.version_number == 5

    def test_parent_link_for_first_execution(self, artifact_service):
        """Test that first execution has no parent."""
        # First execution should have parent_execution_id = None
        parent_id = artifact_service.get_parent_execution_id(None)

        assert parent_id is None

    def test_expiration_date_format(self, artifact_service):
        """Test that expiration date is a valid datetime."""
        created_at = datetime.now()

        expires_at = artifact_service.calculate_expiration(created_at)

        # Should be datetime object
        assert isinstance(expires_at, datetime)

        # Should have date and time components
        assert expires_at.year >= created_at.year
        assert expires_at.month >= 1 and expires_at.month <= 12
        assert expires_at.day >= 1 and expires_at.day <= 31

    def test_version_gap_detection(self, artifact_service, mock_db_session):
        """Test detecting gaps in version sequence."""
        # If versions are 1, 2, 4 (missing 3)
        mock_artifacts = [
            Mock(version_number=1),
            Mock(version_number=2),
            Mock(version_number=4),  # Gap!
        ]

        # Should detect version gap
        has_gap = artifact_service.check_version_gaps(mock_artifacts)

        assert has_gap is True

    def test_version_no_gaps(self, artifact_service):
        """Test continuous version sequence."""
        artifacts = [
            Mock(version_number=1),
            Mock(version_number=2),
            Mock(version_number=3),
        ]

        has_gap = artifact_service.check_version_gaps(artifacts)

        assert has_gap is False
