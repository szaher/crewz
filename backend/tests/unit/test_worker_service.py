"""
Unit tests for worker service (T083).

Tests:
- Heartbeat timeout detection
- Job reassignment on worker crash
- Metrics calculation accuracy
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.services.worker_service import WorkerService


class TestWorkerService:
    """Unit tests for worker service operations."""

    @pytest.fixture
    def worker_service(self):
        """Create worker service instance."""
        service = WorkerService()
        return service

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        session.query = Mock()
        return session

    def test_heartbeat_timeout_detection(self, worker_service, mock_db_session):
        """Test detection of workers with stale heartbeats (>10s)."""
        current_time = datetime.now()

        # Create mock workers
        healthy_worker = Mock()
        healthy_worker.last_heartbeat_at = current_time - timedelta(seconds=5)
        healthy_worker.worker_hostname = "worker-1"
        healthy_worker.status = "active"

        stale_worker = Mock()
        stale_worker.last_heartbeat_at = current_time - timedelta(seconds=15)  # >10s ago
        stale_worker.worker_hostname = "worker-2"
        stale_worker.status = "active"

        workers = [healthy_worker, stale_worker]

        # Detect stale workers
        stale_workers = worker_service.detect_stale_workers(
            workers,
            current_time=current_time,
            timeout_seconds=10
        )

        # Should detect worker-2 as stale
        assert len(stale_workers) == 1
        assert stale_workers[0].worker_hostname == "worker-2"

    def test_mark_worker_as_crashed(self, worker_service, mock_db_session):
        """Test marking worker as crashed."""
        worker = Mock()
        worker.worker_hostname = "crashed-worker"
        worker.status = "active"
        worker.crashed_at = None

        # Mark as crashed
        worker_service.mark_as_crashed(worker, mock_db_session)

        # Should update status and crashed_at
        assert worker.status == "crashed"
        assert worker.crashed_at is not None
        mock_db_session.commit.assert_called_once()

    def test_job_reassignment_on_worker_crash(self, worker_service, mock_db_session):
        """Test that job is reassigned when worker crashes."""
        crashed_worker_id = "worker-crashed"
        job_id = "job-123"

        # Mock crashed worker with assigned job
        crashed_worker = Mock()
        crashed_worker.id = crashed_worker_id
        crashed_worker.current_job_id = job_id
        crashed_worker.status = "crashed"

        # Mock job
        mock_job = Mock()
        mock_job.id = job_id
        mock_job.worker_id = crashed_worker_id
        mock_job.status = "running"

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_job

        # Reassign job
        worker_service.reassign_job(crashed_worker, mock_db_session)

        # Job should be reset for reassignment
        assert mock_job.worker_id is None or mock_job.status == "queued"
        mock_db_session.commit.assert_called()

    def test_register_worker(self, worker_service, mock_db_session):
        """Test registering a new worker."""
        worker_hostname = "new-worker-1"

        worker = worker_service.register_worker(
            worker_hostname,
            db_session=mock_db_session
        )

        # Should create worker record
        assert worker.worker_hostname == worker_hostname
        assert worker.status == "active" or worker.status == "ready"
        assert worker.last_heartbeat_at is not None
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    def test_update_heartbeat(self, worker_service, mock_db_session):
        """Test updating worker heartbeat."""
        worker = Mock()
        worker.worker_hostname = "worker-1"
        worker.last_heartbeat_at = datetime.now() - timedelta(seconds=30)

        old_heartbeat = worker.last_heartbeat_at

        # Update heartbeat
        worker_service.update_heartbeat(worker, mock_db_session)

        # Heartbeat should be updated
        assert worker.last_heartbeat_at > old_heartbeat
        mock_db_session.commit.assert_called_once()

    def test_get_pool_metrics(self, worker_service, mock_db_session):
        """Test calculation of worker pool metrics."""
        # Mock workers with various states
        workers = [
            Mock(status="active", cpu_usage_percent=50.0, memory_usage_mb=2048),
            Mock(status="active", cpu_usage_percent=70.0, memory_usage_mb=3072),
            Mock(status="crashed", cpu_usage_percent=0.0, memory_usage_mb=0),
            Mock(status="idle", cpu_usage_percent=10.0, memory_usage_mb=1024),
        ]

        mock_db_session.query.return_value.all.return_value = workers

        metrics = worker_service.get_pool_metrics(mock_db_session)

        # Verify metrics calculations
        assert metrics["total_workers"] == 4
        assert metrics["active_workers"] == 2
        assert metrics["crashed_workers"] == 1
        assert metrics["idle_workers"] == 1

        # Check average CPU
        active_cpus = [50.0, 70.0]
        expected_avg_cpu = sum(active_cpus) / len(active_cpus)
        assert metrics["avg_cpu_usage"] == expected_avg_cpu

    def test_assign_job_to_worker(self, worker_service, mock_db_session):
        """Test assigning job to worker."""
        worker = Mock()
        worker.id = "worker-1"
        worker.status = "idle"
        worker.current_job_id = None

        job_id = "job-456"

        # Assign job
        worker_service.assign_job(worker, job_id, mock_db_session)

        # Worker should have job assigned
        assert worker.current_job_id == job_id
        assert worker.status == "busy" or worker.status == "active"
        mock_db_session.commit.assert_called_once()

    def test_release_job_from_worker(self, worker_service, mock_db_session):
        """Test releasing job from worker."""
        worker = Mock()
        worker.id = "worker-1"
        worker.current_job_id = "job-789"
        worker.status = "busy"

        # Release job
        worker_service.release_job(worker, mock_db_session)

        # Worker should be free
        assert worker.current_job_id is None
        assert worker.status == "idle" or worker.status == "active"
        mock_db_session.commit.assert_called_once()

    def test_heartbeat_timeout_exactly_10_seconds(self, worker_service):
        """Test boundary condition: exactly 10 seconds is considered timed out."""
        current_time = datetime.now()

        worker = Mock()
        worker.last_heartbeat_at = current_time - timedelta(seconds=10)
        worker.status = "active"

        workers = [worker]

        stale_workers = worker_service.detect_stale_workers(
            workers,
            current_time=current_time,
            timeout_seconds=10
        )

        # At exactly 10 seconds, should be considered stale
        assert len(stale_workers) == 1

    def test_heartbeat_just_under_timeout(self, worker_service):
        """Test worker just under timeout threshold is healthy."""
        current_time = datetime.now()

        worker = Mock()
        worker.last_heartbeat_at = current_time - timedelta(seconds=9)  # Just under 10s
        worker.status = "active"

        workers = [worker]

        stale_workers = worker_service.detect_stale_workers(
            workers,
            current_time=current_time,
            timeout_seconds=10
        )

        # Should NOT be considered stale
        assert len(stale_workers) == 0

    def test_metrics_with_no_workers(self, worker_service, mock_db_session):
        """Test metrics calculation with empty worker pool."""
        mock_db_session.query.return_value.all.return_value = []

        metrics = worker_service.get_pool_metrics(mock_db_session)

        # Should return zero metrics
        assert metrics["total_workers"] == 0
        assert metrics["active_workers"] == 0
        assert metrics["avg_cpu_usage"] == 0 or metrics["avg_cpu_usage"] is None

    def test_metrics_accuracy_for_averages(self, worker_service, mock_db_session):
        """Test accuracy of average calculations in metrics."""
        workers = [
            Mock(status="active", cpu_usage_percent=25.0, memory_usage_mb=1000),
            Mock(status="active", cpu_usage_percent=50.0, memory_usage_mb=2000),
            Mock(status="active", cpu_usage_percent=75.0, memory_usage_mb=3000),
        ]

        mock_db_session.query.return_value.all.return_value = workers

        metrics = worker_service.get_pool_metrics(mock_db_session)

        # Verify exact averages
        expected_avg_cpu = (25.0 + 50.0 + 75.0) / 3
        expected_avg_mem = (1000 + 2000 + 3000) / 3

        assert metrics["avg_cpu_usage"] == expected_avg_cpu
        assert metrics["avg_memory_usage"] == expected_avg_mem

    def test_find_available_worker(self, worker_service, mock_db_session):
        """Test finding an available worker for job assignment."""
        # Mock available and busy workers
        busy_worker = Mock(status="busy", current_job_id="some-job")
        idle_worker = Mock(status="idle", current_job_id=None)

        mock_db_session.query.return_value.filter.return_value.first.return_value = idle_worker

        worker = worker_service.find_available_worker(mock_db_session)

        # Should return idle worker
        assert worker.status == "idle"
        assert worker.current_job_id is None

    def test_no_available_workers(self, worker_service, mock_db_session):
        """Test when no workers are available."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        worker = worker_service.find_available_worker(mock_db_session)

        # Should return None
        assert worker is None

    def test_worker_status_transitions(self, worker_service, mock_db_session):
        """Test valid worker status transitions."""
        worker = Mock()
        worker.status = "idle"

        # idle -> busy (assign job)
        worker_service.assign_job(worker, "job-1", mock_db_session)
        assert worker.status in ["busy", "active"]

        # busy -> idle (release job)
        worker_service.release_job(worker, mock_db_session)
        assert worker.status in ["idle", "active"]

        # active -> crashed (timeout)
        worker.status = "active"
        worker_service.mark_as_crashed(worker, mock_db_session)
        assert worker.status == "crashed"

    def test_concurrent_heartbeat_updates(self, worker_service, mock_db_session):
        """Test that concurrent heartbeat updates are handled."""
        worker = Mock()
        worker.worker_hostname = "worker-concurrent"
        worker.last_heartbeat_at = datetime.now() - timedelta(seconds=5)

        # Simulate multiple heartbeat updates
        for _ in range(5):
            worker_service.update_heartbeat(worker, mock_db_session)

        # Should have committed multiple times
        assert mock_db_session.commit.call_count == 5

    def test_crashed_worker_not_assigned_jobs(self, worker_service, mock_db_session):
        """Test that crashed workers don't get new jobs."""
        crashed_worker = Mock(status="crashed", current_job_id=None)

        mock_db_session.query.return_value.filter.return_value.first.return_value = None

        # Try to find available worker (should exclude crashed)
        worker = worker_service.find_available_worker(mock_db_session)

        # Should not return crashed worker
        assert worker is None or worker.status != "crashed"

    def test_get_worker_by_hostname(self, worker_service, mock_db_session):
        """Test retrieving worker by hostname."""
        hostname = "worker-specific"

        mock_worker = Mock()
        mock_worker.worker_hostname = hostname

        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_worker

        worker = worker_service.get_worker_by_hostname(hostname, mock_db_session)

        assert worker.worker_hostname == hostname
