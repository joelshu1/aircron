import logging
from typing import Any, Dict, List

from flask import current_app

from .. import cronblock
from ..jobs_store import Job, JobsStore

logger = logging.getLogger(__name__)


def get_jobs_for_zone(zone: str) -> List[Dict[str, Any]]:
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    jobs = jobs_store.get_jobs_for_zone(zone)
    return [job.to_dict() for job in jobs]


def create_job(zone: str, data: Dict[str, Any]) -> Dict[str, Any]:
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
    valid_actions = ["play", "pause", "resume", "volume", "connect", "disconnect"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action. Must be one of: {valid_actions}")
    args = data.get("args", {})
    service = data.get("service", "spotify")

    valid_services = ["spotify", "applemusic"]
    if service not in valid_services:
        raise ValueError(f"Invalid service. Must be one of: {valid_services}")

    # Additional validation for empty service
    if not service or service.strip() == "":
        raise ValueError("Service cannot be empty")

    if action == "play":
        if service == "spotify":
            if "uri" not in args or not args["uri"]:
                raise ValueError("Play action for Spotify requires 'uri' in args")
        elif service == "applemusic":
            if "playlist" not in args or not args["playlist"]:
                raise ValueError("Play action for Apple Music requires 'playlist' in args")
    elif action == "volume" and "volume" not in args:
        raise ValueError("Volume action requires 'volume' in args")
    elif action in ["connect", "disconnect"]:
        if not service or service.strip() == "":
            raise ValueError(f"{action.title()} action requires a valid 'service' to be specified")
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
        label=data.get("label", ""),
        service=service,
    )
    jobs_store.add_job(job)
    logger.info(f"[jobs_service] Created job {job_id} for zone {zone}")
    return job.to_dict()


def update_job(zone: str, job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
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
    service = data.get("service", getattr(existing_job, "service", "spotify"))

    valid_services = ["spotify", "applemusic"]
    if service not in valid_services:
        raise ValueError(f"Invalid service. Must be one of: {valid_services}")

    # Additional validation for empty service
    if not service or service.strip() == "":
        raise ValueError("Service cannot be empty")

    valid_actions = ["play", "pause", "resume", "volume", "connect", "disconnect"]
    if action not in valid_actions:
        raise ValueError(f"Invalid action. Must be one of: {valid_actions}")

    if action == "play":
        if service == "spotify":
            if "uri" not in args or not args["uri"]:
                raise ValueError("Play action for Spotify requires 'uri' in args")
        elif service == "applemusic":
            if "playlist" not in args or not args["playlist"]:
                raise ValueError("Play action for Apple Music requires 'playlist' in args")
    elif action == "volume" and "volume" not in args:
        raise ValueError("Volume action requires 'volume' in args")
    elif action in ["connect", "disconnect"]:
        if not service or service.strip() == "":
            raise ValueError(f"{action.title()} action requires a valid 'service' to be specified")

    updated_job = Job(
        job_id=job_id,
        zone=data.get("zone", zone),
        days=days,
        time=time_val,
        action=action,
        args=args,
        label=label,
        service=service,
    )
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    if not cronblock.cron_manager.validate_cron_syntax(updated_job.time, updated_job.days):
        raise ValueError("Invalid cron syntax")
    # If zone changed, remove from old zone and add to new zone
    new_zone = data.get("zone", zone)
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
