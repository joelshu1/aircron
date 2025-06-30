"""Job storage management for AirCron."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
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
        label: str = ""
    ) -> None:
        self.id = job_id
        self.zone = zone
        self.days = days  # 1=Monday, 7=Sunday
        self.time = time  # HH:MM format
        self.action = action  # play, pause, resume, volume
        self.args = args
        self.label = label
    
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
            label=data.get("label", "")
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
        
        self.jobs_file = app_support_dir / "jobs.json"
        self._ensure_file_exists()
    
    def _get_jobs_file_path(self) -> Path:
        """Get path to jobs.json file."""
        return self.jobs_file
    
    def _ensure_file_exists(self) -> None:
        """Create jobs.json if it doesn't exist."""
        if not self.jobs_file.exists():
            self.jobs_file.write_text(json.dumps({}))
            logger.info(f"Created jobs file: {self.jobs_file}")
    
    def _load_jobs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load all jobs from JSON file."""
        try:
            with self.jobs_file.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading jobs: {e}")
            return {}
    
    def _save_jobs(self, jobs: Dict[str, List[Dict[str, Any]]]) -> None:
        """Save all jobs to JSON file."""
        try:
            with self.jobs_file.open("w") as f:
                json.dump(jobs, f, indent=2)
            logger.info("Jobs saved successfully")
        except Exception as e:
            logger.error(f"Error saving jobs: {e}")
            raise
    
    def get_jobs_for_zone(self, zone: str) -> List[Job]:
        """Get all jobs for a specific zone."""
        all_jobs = self._load_jobs()
        zone_jobs = all_jobs.get(zone, [])
        return [Job.from_dict(job_data) for job_data in zone_jobs]
    
    def get_all_jobs(self) -> Dict[str, List[Job]]:
        """Get all jobs organized by zone."""
        all_jobs = self._load_jobs()
        result = {}
        for zone, job_list in all_jobs.items():
            result[zone] = [Job.from_dict(job_data) for job_data in job_list]
        return result
    
    def add_job(self, job: Job) -> None:
        """Add a new job."""
        all_jobs = self._load_jobs()
        logger.info(f"Loading jobs for add_job: found {len(all_jobs)} zones with {sum(len(jobs) for jobs in all_jobs.values())} total jobs")
        
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
        logger.info(f"Added job {job.id} to zone {job.zone}. Zone now has {len(all_jobs[job.zone])} jobs")
        
        self._save_jobs(all_jobs)
        logger.info(f"Saved jobs to disk. Total zones: {len(all_jobs)}, total jobs: {sum(len(jobs) for jobs in all_jobs.values())}")
        logger.info(f"Added job {job.id} for zone {job.zone}")
    
    def update_job(self, job: Job) -> None:
        """Update an existing job."""
        all_jobs = self._load_jobs()
        
        if job.zone not in all_jobs:
            raise ValueError(f"Zone {job.zone} not found")
        
        # Find and update job
        zone_jobs = all_jobs[job.zone]
        for i, existing_job in enumerate(zone_jobs):
            if existing_job["id"] == job.id:
                # Validate no conflicts with other jobs
                for j, other_job in enumerate(zone_jobs):
                    if i != j and other_job["time"] == job.time and set(other_job["days"]) & set(job.days):
                        raise ValueError(
                            f"Conflict: Job at {job.time} already exists for overlapping days"
                        )
                
                zone_jobs[i] = job.to_dict()
                self._save_jobs(all_jobs)
                logger.info(f"Updated job {job.id}")
                return
        
        raise ValueError(f"Job {job.id} not found in zone {job.zone}")
    
    def delete_job(self, zone: str, job_id: str) -> None:
        """Delete a job."""
        all_jobs = self._load_jobs()
        
        if zone not in all_jobs:
            raise ValueError(f"Zone {zone} not found")
        
        zone_jobs = all_jobs[zone]
        for i, job in enumerate(zone_jobs):
            if job["id"] == job_id:
                del zone_jobs[i]
                if not zone_jobs:
                    del all_jobs[zone]
                self._save_jobs(all_jobs)
                logger.info(f"Deleted job {job_id} from zone {zone}")
                return
        
        raise ValueError(f"Job {job_id} not found in zone {zone}")
    
    def create_job_id(self) -> str:
        """Generate a unique job ID."""
        return str(uuid4())[:8] 