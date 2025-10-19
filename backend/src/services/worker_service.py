"""Worker service for managing Celery worker pool health and job assignments.

Tracks worker heartbeats, marks crashed workers, assigns jobs, and provides pool metrics.
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from src.models.worker_instance import WorkerInstance, WorkerStatus
from src.models.execution import Execution


class WorkerService:
    """Service for managing worker instances and health monitoring."""

    HEARTBEAT_TIMEOUT_SECONDS = 90  # Workers are marked crashed after 90s without heartbeat

    def __init__(self, db_session: Session):
        """
        Initialize worker service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def register_worker(
        self,
        worker_hostname: str,
        cpu_percent: float = None,
        memory_mb: int = None
    ) -> WorkerInstance:
        """
        Register new worker or update existing worker.

        Args:
            worker_hostname: Unique worker hostname (e.g., "celery@worker1")
            cpu_percent: Initial CPU usage
            memory_mb: Initial memory usage

        Returns:
            WorkerInstance object
        """
        # Check if worker already exists
        worker = self.db.query(WorkerInstance).filter(
            WorkerInstance.worker_hostname == worker_hostname
        ).first()

        if worker:
            # Update existing worker
            worker.status = WorkerStatus.IDLE
            worker.last_heartbeat_at = datetime.utcnow()
            worker.crashed_at = None
            if cpu_percent is not None:
                worker.cpu_usage_percent = cpu_percent
            if memory_mb is not None:
                worker.memory_usage_mb = memory_mb
        else:
            # Create new worker
            worker = WorkerInstance(
                worker_hostname=worker_hostname,
                status=WorkerStatus.STARTING,
                last_heartbeat_at=datetime.utcnow(),
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory_mb
            )
            self.db.add(worker)

        self.db.commit()
        self.db.refresh(worker)
        return worker

    def update_heartbeat(
        self,
        worker_hostname: str,
        cpu_percent: float = None,
        memory_mb: int = None
    ) -> bool:
        """
        Update worker heartbeat and resource metrics.

        Args:
            worker_hostname: Worker hostname
            cpu_percent: Current CPU usage
            memory_mb: Current memory usage

        Returns:
            True if updated, False if worker not found
        """
        worker = self.db.query(WorkerInstance).filter(
            WorkerInstance.worker_hostname == worker_hostname
        ).first()

        if not worker:
            return False

        worker.update_heartbeat(cpu_percent, memory_mb)
        self.db.commit()
        return True

    def mark_as_crashed(self, worker_id: UUID) -> bool:
        """
        Mark worker as crashed due to missing heartbeat.

        Args:
            worker_id: Worker UUID

        Returns:
            True if marked crashed, False if not found
        """
        worker = self.db.query(WorkerInstance).filter(
            WorkerInstance.id == worker_id
        ).first()

        if not worker:
            return False

        worker.mark_as_crashed()
        self.db.commit()
        return True

    def check_and_mark_crashed_workers(self) -> List[WorkerInstance]:
        """
        Check all workers for stale heartbeats and mark as crashed.

        Returns:
            List of workers marked as crashed
        """
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.HEARTBEAT_TIMEOUT_SECONDS)

        stale_workers = self.db.query(WorkerInstance).filter(
            WorkerInstance.status.in_([WorkerStatus.IDLE, WorkerStatus.BUSY]),
            WorkerInstance.last_heartbeat_at < cutoff_time
        ).all()

        crashed_workers = []
        for worker in stale_workers:
            worker.mark_as_crashed()
            crashed_workers.append(worker)

        if crashed_workers:
            self.db.commit()

        return crashed_workers

    def assign_job(self, worker_id: UUID, execution_id: UUID) -> bool:
        """
        Assign job to worker.

        Args:
            worker_id: Worker UUID
            execution_id: Execution UUID to assign

        Returns:
            True if assigned, False if worker not found or not idle
        """
        worker = self.db.query(WorkerInstance).filter(
            WorkerInstance.id == worker_id
        ).first()

        if not worker or worker.status != WorkerStatus.IDLE:
            return False

        worker.assign_job(execution_id)
        self.db.commit()
        return True

    def release_job(self, worker_id: UUID) -> bool:
        """
        Release current job from worker.

        Args:
            worker_id: Worker UUID

        Returns:
            True if released, False if worker not found
        """
        worker = self.db.query(WorkerInstance).filter(
            WorkerInstance.id == worker_id
        ).first()

        if not worker:
            return False

        worker.release_job()
        self.db.commit()
        return True

    def get_worker_by_hostname(self, worker_hostname: str) -> Optional[WorkerInstance]:
        """
        Get worker by hostname.

        Args:
            worker_hostname: Worker hostname

        Returns:
            WorkerInstance or None
        """
        return self.db.query(WorkerInstance).filter(
            WorkerInstance.worker_hostname == worker_hostname
        ).first()

    def get_healthy_workers(self) -> List[WorkerInstance]:
        """
        Get all healthy workers.

        Returns:
            List of healthy WorkerInstance objects
        """
        return WorkerInstance.get_healthy_workers(self.db)

    def get_idle_workers(self) -> List[WorkerInstance]:
        """
        Get all idle workers available for new tasks.

        Returns:
            List of idle WorkerInstance objects
        """
        return WorkerInstance.get_idle_workers(self.db)

    def get_pool_metrics(self) -> Dict:
        """
        Get worker pool metrics for monitoring and autoscaling.

        Returns:
            Dict with pool statistics
        """
        all_workers = self.db.query(WorkerInstance).all()

        metrics = {
            "total_workers": len(all_workers),
            "healthy_workers": 0,
            "idle_workers": 0,
            "busy_workers": 0,
            "crashed_workers": 0,
            "avg_cpu_percent": 0.0,
            "avg_memory_mb": 0.0,
            "max_cpu_percent": 0.0,
            "max_memory_mb": 0.0
        }

        cpu_values = []
        memory_values = []

        for worker in all_workers:
            if worker.is_healthy():
                metrics["healthy_workers"] += 1

            if worker.status == WorkerStatus.IDLE:
                metrics["idle_workers"] += 1
            elif worker.status == WorkerStatus.BUSY:
                metrics["busy_workers"] += 1
            elif worker.status == WorkerStatus.CRASHED:
                metrics["crashed_workers"] += 1

            if worker.cpu_usage_percent is not None:
                cpu_values.append(worker.cpu_usage_percent)
            if worker.memory_usage_mb is not None:
                memory_values.append(worker.memory_usage_mb)

        if cpu_values:
            metrics["avg_cpu_percent"] = sum(cpu_values) / len(cpu_values)
            metrics["max_cpu_percent"] = max(cpu_values)

        if memory_values:
            metrics["avg_memory_mb"] = sum(memory_values) / len(memory_values)
            metrics["max_memory_mb"] = max(memory_values)

        return metrics

    def get_worker_job(self, worker_id: UUID) -> Optional[Execution]:
        """
        Get current job assigned to worker.

        Args:
            worker_id: Worker UUID

        Returns:
            Execution object or None
        """
        worker = self.db.query(WorkerInstance).filter(
            WorkerInstance.id == worker_id
        ).first()

        if not worker or not worker.current_job_id:
            return None

        return worker.current_job
