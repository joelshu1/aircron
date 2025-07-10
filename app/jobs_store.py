"""Job storage management for AirCron."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from uuid import uuid4

from flask import current_app, has_app_context

logger = logging.getLogger(__name__)


class Job:
    """Represents a single scheduled job."""

    def __init__(
        self,
        job_id: str,
        zone: str,
        days: List[int],
        time: str,
        action: str,
        args: Dict[str, Any],
        label: str = "",
        service: str = "spotify",
    ) -> None:
        self.id = job_id
        self.zone = zone
        self.days = days  # 1=Monday, 7=Sunday
        self.time = time  # HH:MM format
        self.action = action  # play, pause, resume, volume
        self.args = args
        self.label = label
        self.service = service or "spotify"

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return {
            "id": self.id,
            "zone": self.zone,
            "days": self.days,
            "time": self.time,
            "action": self.action,
            "args": self.args,
            "label": self.label,
            "service": self.service,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create job from dictionary."""
        return cls(
            job_id=data["id"],
            zone=data["zone"],
            days=data["days"],
            time=data["time"],
            action=data["action"],
            args=data.get("args", {}),
            label=data.get("label", ""),
            service=data.get("service", "spotify"),
        )


class JobsStore:
    """Manages job persistence to JSON file."""

    def __init__(self, app_support_dir: Optional[Path] = None) -> None:
        if app_support_dir is None and has_app_context():
            app_support_dir = current_app.config["APP_SUPPORT_DIR"]
        elif app_support_dir is None:
            # Default fallback when no Flask context
            app_support_dir = Path.home() / "Library" / "Application Support" / "AirCron"
            app_support_dir.mkdir(parents=True, exist_ok=True)

        self.jobs_file = Path(app_support_dir) / "jobs.json"
        self.lock_file = self.jobs_file.with_suffix(".json.lock")
        if not self.jobs_file.exists():
            self.jobs_file.parent.mkdir(parents=True, exist_ok=True)
            self.jobs_file.write_text("{}")

    def _get_jobs_file_path(self) -> Path:
        """Get path to jobs.json file."""
        return self.jobs_file

    def _ensure_file_exists(self) -> None:
        """Create jobs.json if it doesn't exist."""
        if not self.jobs_file.exists():
            self.jobs_file.write_text(json.dumps({}))
            logger.info(f"Created jobs file: {self.jobs_file}")

    def _load_and_migrate_jobs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Loads jobs from disk and runs any necessary data migrations."""
        jobs = self._load_jobs_from_disk()

        # --- Migration Section ---
        changed = False
        for job_list in jobs.values():
            for job_dict in job_list:
                if "service" not in job_dict:
                    job_dict["service"] = "spotify"
                    changed = True

        if changed:
            logger.info("Migrated old jobs to include 'service' field. Saving.")
            self._save_jobs(jobs)

        return jobs

    def _load_jobs_from_disk(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Loads a valid dictionary from jobs.json or its backup.
        If both are corrupt, it cleans up and returns an empty dict.
        """
        # 1. Try to load the main jobs file
        if self.jobs_file.exists():
            try:
                with self.jobs_file.open("r", encoding="utf-8") as f:
                    return cast(Dict[str, List[Dict[str, Any]]], json.load(f))
            except json.JSONDecodeError as e:
                logger.error(f"Jobs file is corrupt: {e}. Attempting recovery from backup.")

        # 2. Main file failed or doesn't exist. Try to load the backup.
        backup_file = self.jobs_file.with_suffix(".json.bak")
        if backup_file.exists():
            logger.info(f"Attempting to restore from backup: {backup_file}")
            try:
                with backup_file.open("r", encoding="utf-8") as bf:
                    data = cast(Dict[str, List[Dict[str, Any]]], json.load(bf))
                logger.info("Successfully loaded data from backup file. Restoring...")
                self._save_jobs(data)  # Atomically save the good data back
                return data
            except json.JSONDecodeError as be:
                logger.error(f"Backup file is also corrupt: {be}")

        # 3. Both files are corrupt or don't exist.
        logger.warning("No valid jobs file found. Resetting jobs store.")
        if self.jobs_file.exists():
            self.jobs_file.unlink()
        if backup_file.exists():
            backup_file.unlink()

        return {}

    def _save_jobs(self, jobs: Dict[str, List[Dict[str, Any]]]) -> None:
        """
        Atomically saves jobs to disk using a file lock and atomic replace to ensure
        data integrity and prevent race conditions.
        """
        timeout = 5.0  # 5-second timeout to acquire the lock
        start_time = time.time()
        lock_fd = -1

        # 1. Acquire an exclusive lock
        while True:
            try:
                # Atomically create the lock file. Fails if it already exists.
                lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break  # Lock acquired
            except FileExistsError:
                if time.time() - start_time > timeout:
                    raise TimeoutError(
                        f"Could not acquire lock on {self.lock_file} within {timeout}s"
                    )
                time.sleep(0.1)  # Wait and retry

        # 2. Perform the atomic write operation inside a try...finally block
        try:
            temp_file = self.jobs_file.with_suffix(".json.tmp")
            backup_file = self.jobs_file.with_suffix(".json.bak")

            # Write to a temporary file first
            with temp_file.open("w", encoding="utf-8") as f:
                json.dump(jobs, f, indent=2)

            # Atomically create a backup of the current file (if it exists)
            if self.jobs_file.exists():
                os.replace(self.jobs_file, backup_file)

            # Atomically replace the main file with the new data
            os.replace(temp_file, self.jobs_file)

            logger.info(f"[JobsStore] Jobs saved successfully to {self.jobs_file}")

        except Exception as e:
            logger.error(f"[JobsStore] Error during atomic save: {e}")
            # Clean up and attempt to restore from backup
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(backup_file) and not os.path.exists(self.jobs_file):
                os.replace(backup_file, self.jobs_file)
                logger.info(f"Restored jobs from backup {backup_file} due to save error.")
            raise
        finally:
            # 3. Always release the lock
            if lock_fd != -1:
                os.close(lock_fd)
                os.remove(self.lock_file)

    def get_jobs_for_zone(self, zone: str) -> List[Job]:
        """Get all jobs for a specific zone."""
        all_jobs = self._load_and_migrate_jobs()
        zone_jobs = all_jobs.get(zone, [])
        return [Job.from_dict(job_data) for job_data in zone_jobs]

    def get_all_jobs(self) -> Dict[str, List[Job]]:
        """Get all jobs organized by zone."""
        all_jobs = self._load_and_migrate_jobs()
        result = {}
        for zone, job_list in all_jobs.items():
            result[zone] = [Job.from_dict(job_data) for job_data in job_list]
        return result

    def add_job(self, job: Job) -> None:
        """Add a new job."""
        logger.info(f"[JobsStore] add_job called with job: {job.to_dict()}")
        all_jobs = self._load_and_migrate_jobs()
        logger.info(f"[JobsStore] add_job loaded jobs: {all_jobs}")

        # Validate no conflicts (same time + overlapping days in same zone)
        existing_jobs = self.get_jobs_for_zone(job.zone)
        for existing in existing_jobs:
            if existing.time == job.time and set(existing.days) & set(job.days):
                raise ValueError(
                    f"Conflict: Job at {job.time} already exists for overlapping days in {job.zone}"
                )

        # Add job
        if job.zone not in all_jobs:
            all_jobs[job.zone] = []
            logger.info(f"Created new zone: {job.zone}")

        all_jobs[job.zone].append(job.to_dict())
        logger.info(
            f"[JobsStore] add_job: Added job {job.id} to zone {job.zone}. "
            f"Zone now has {len(all_jobs[job.zone])} jobs"
        )

        self._save_jobs(all_jobs)
        logger.info(f"[JobsStore] add_job: Saved jobs after adding job {job.id}")
        logger.info(f"[JobsStore] add_job: Added job {job.id} for zone {job.zone}")

    def update_job(self, job: Job) -> None:
        """Update an existing job."""
        logger.info(f"[JobsStore] update_job called with job: {job.to_dict()}")
        all_jobs = self._load_and_migrate_jobs()
        logger.info(f"[JobsStore] update_job loaded jobs: {all_jobs}")

        if job.zone not in all_jobs:
            raise ValueError(f"Zone {job.zone} not found")

        # Find and update job
        zone_jobs = all_jobs[job.zone]
        for i, existing_job in enumerate(zone_jobs):
            if existing_job["id"] == job.id:
                # Validate no conflicts with other jobs
                for j, other_job in enumerate(zone_jobs):
                    if (
                        i != j
                        and other_job["time"] == job.time
                        and set(other_job["days"]) & set(job.days)
                    ):
                        raise ValueError(
                            f"Conflict: Job at {job.time} already exists for overlapping days"
                        )

                zone_jobs[i] = job.to_dict()
                logger.info(f"[JobsStore] update_job: Updated job {job.id}")
                self._save_jobs(all_jobs)
                logger.info(f"[JobsStore] update_job: Saved jobs after updating job {job.id}")
                return

        raise ValueError(f"Job {job.id} not found in zone {job.zone}")

    def delete_job(self, zone: str, job_id: str) -> None:
        """Delete a job."""
        logger.info(f"[JobsStore] delete_job called with zone: {zone}, job_id: {job_id}")
        all_jobs = self._load_and_migrate_jobs()
        logger.info(f"[JobsStore] delete_job loaded jobs: {all_jobs}")

        if zone not in all_jobs:
            raise ValueError(f"Zone {zone} not found")

        zone_jobs = all_jobs[zone]
        for i, job in enumerate(zone_jobs):
            if job["id"] == job_id:
                del zone_jobs[i]
                if not zone_jobs:
                    del all_jobs[zone]
                logger.info(f"[JobsStore] delete_job: Deleted job {job_id} from zone {zone}")
                self._save_jobs(all_jobs)
                logger.info(f"[JobsStore] delete_job: Saved jobs after deleting job {job_id}")
                return

        raise ValueError(f"Job {job_id} not found in zone {zone}")

    def create_job_id(self) -> str:
        """Generate a unique job ID."""
        return str(uuid4())[:8]
