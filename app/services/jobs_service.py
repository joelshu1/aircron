import logging
from typing import Any, Dict, List, Optional
from flask import current_app
from ..jobs_store import Job, JobsStore
from .. import cronblock
from werkzeug.exceptions import BadRequest

logger = logging.getLogger(__name__)

def get_jobs_for_zone(zone: str) -> List[Dict[str, Any]]:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    jobs = jobs_store.get_jobs_for_zone(zone)
    return [job.to_dict() for job in jobs]

def create_job(zone: str, data: dict) -> Dict[str, Any]:
    required_fields = ["days", "time", "action"]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    time_str = data["time"]
    try:
        hour, minute = time_str.split(":")
        hour = int(hour)
        minute = int(minute)
        if not (0 <= hour <= 23) or not (0 <= minute <= 59):
            raise ValueError("Invalid time range")
    except (ValueError, IndexError):
        raise ValueError("Invalid time format (use HH:MM)")
    days = [int(day) for day in data["days"]]
    if not isinstance(days, list) or not days:
        raise ValueError("Days must be a non-empty list")
    for day in days:
        if not isinstance(day, int) or day < 1 or day > 7:
            raise ValueError("Days must be integers 1-7 (1=Monday, 7=Sunday)")
    action = data["action"]
    valid_actions = ["play", "pause", "resume", "volume"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action. Must be one of: {valid_actions}")
    args = data.get("args", {})
    if action == "play" and "uri" not in args:
        raise ValueError("Play action requires 'uri' in args")
    elif action == "volume" and "volume" not in args:
        raise ValueError("Volume action requires 'volume' in args")
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    if not cronblock.cron_manager.validate_cron_syntax(time_str, days):
        raise ValueError("Invalid cron syntax")
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    job_id = jobs_store.create_job_id()
    job = Job(
        job_id=job_id,
        zone=zone,
        days=days,
        time=time_str,
        action=action,
        args=args,
        label=data.get("label", "")
    )
    jobs_store.add_job(job)
    logger.info(f"[jobs_service] Created job {job_id} for zone {zone}")
    return job.to_dict()

def update_job(zone: str, job_id: str, data: dict) -> Dict[str, Any]:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    existing_jobs = jobs_store.get_jobs_for_zone(zone)
    existing_job = None
    for job in existing_jobs:
        if job.id == job_id:
            existing_job = job
            break
    if not existing_job:
        raise ValueError("Job not found")
    if "time" in data:
        time_str = data["time"]
        try:
            hour, minute = time_str.split(":")
            hour = int(hour)
            minute = int(minute)
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Invalid time range")
        except (ValueError, IndexError):
            raise ValueError("Invalid time format (use HH:MM)")
    if "days" in data:
        days = [int(day) for day in data["days"]]
        if not isinstance(days, list) or not days:
            raise ValueError("Days must be a non-empty list")
        for day in days:
            if not isinstance(day, int) or day < 1 or day > 7:
                raise ValueError("Days must be integers 1-7")
    else:
        days = existing_job.days
    action = data.get("action", existing_job.action)
    args = data.get("args", existing_job.args)
    label = data.get("label", getattr(existing_job, "label", ""))
    time_val = data.get("time", existing_job.time)
    # Determine new zone (may be different from old zone)
    new_zone = data.get("zone", zone)
    updated_job = Job(
        job_id=job_id,
        zone=new_zone,
        days=days,
        time=time_val,
        action=action,
        args=args,
        label=label
    )
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    if not cronblock.cron_manager.validate_cron_syntax(updated_job.time, updated_job.days):
        raise ValueError("Invalid cron syntax")
    # If zone changed, remove from old zone and add to new zone
    if new_zone != zone:
        jobs_store.delete_job(zone, job_id)
        jobs_store.add_job(updated_job)
        logger.info(f"[jobs_service] Moved job {job_id} from zone {zone} to {new_zone}")
    else:
        jobs_store.update_job(updated_job)
        logger.info(f"[jobs_service] Updated job {job_id} in zone {zone}")
    return updated_job.to_dict()

def delete_job(zone: str, job_id: str) -> None:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    jobs_store.delete_job(zone, job_id)
    logger.info(f"[jobs_service] Deleted job {job_id} from zone {zone}")

def get_all_jobs_flat() -> List[Dict[str, Any]]:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    all_jobs = jobs_store.get_all_jobs()
    jobs_flat = []
    for zone, jobs in all_jobs.items():
        for job in jobs:
            job_dict = job.to_dict()
            job_dict["zone"] = zone
            jobs_flat.append(job_dict)
    return jobs_flat 