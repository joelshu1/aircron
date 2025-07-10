import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import current_app

from .. import cronblock
from ..cronblock import _normalize_cron_line
from ..jobs_store import Job, JobsStore

logger = logging.getLogger(__name__)


def apply_jobs_to_cron() -> Dict[str, Any]:
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    jobs_file = jobs_store.jobs_file
    if not jobs_file.exists():
        jobs_file.touch()
        jobs_file.write_text(json.dumps({}))
    all_jobs = jobs_store.get_all_jobs()
    total_jobs = sum(len(jobs) for jobs in all_jobs.values())
    logger.info(
        f"[cron_service] Apply cron called with {len(all_jobs)} zones and {total_jobs} total jobs"
    )
    cronblock.cron_manager.apply_jobs_to_cron()
    if total_jobs == 0:
        logger.info("[cron_service] Successfully cleared all jobs from crontab")
    else:
        logger.info("[cron_service] Successfully applied jobs to crontab")
    return {"ok": True}


def get_cron_status() -> Dict[str, Any]:
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    jobs_file = jobs_store.jobs_file
    if not jobs_file.exists():
        jobs_file.touch()
        jobs_file.write_text(json.dumps({}))
    current_lines = cronblock.cron_manager._get_current_crontab()
    has_aircron_section = False
    current_cron_jobs = []
    in_aircron_section = False
    for line in current_lines:
        line = line.strip()
        if line == cronblock.AIRCRON_BEGIN:
            has_aircron_section = True
            in_aircron_section = True
        elif line == cronblock.AIRCRON_END:
            in_aircron_section = False
        elif in_aircron_section and line and not line.startswith("#"):
            current_cron_jobs.append(_normalize_cron_line(line))
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    all_jobs = jobs_store.get_all_jobs()
    total_stored_jobs = sum(len(jobs) for jobs in all_jobs.values())
    expected_cron_lines = []
    for zone, jobs in all_jobs.items():
        for job in jobs:
            cron_line = cronblock.cron_manager._job_to_cron_line(job)
            if cron_line:
                expected_cron_lines.append(_normalize_cron_line(cron_line))
    has_jobs_in_cron = len(current_cron_jobs) > 0
    jobs_match = set(current_cron_jobs) == set(expected_cron_lines)
    needs_apply = total_stored_jobs > 0 and not jobs_match
    # Robust desync check: jobs.json has jobs, but AirCron block is empty
    cron_desync = False
    if total_stored_jobs > 0 and not has_jobs_in_cron:
        cron_desync = True
        logger.warning(
            "[cron_service] Detected desync: jobs.json has jobs but AirCron block is empty!"
        )
    return {
        "has_aircron_section": has_aircron_section,
        "has_jobs_in_cron": has_jobs_in_cron,
        "total_stored_jobs": total_stored_jobs,
        "current_cron_jobs_count": len(current_cron_jobs),
        "expected_cron_jobs_count": len(expected_cron_lines),
        "jobs_match": jobs_match,
        "needs_apply": needs_apply,
        "current_cron_jobs": current_cron_jobs,
        "expected_cron_jobs": expected_cron_lines,
        "cron_desync": cron_desync,
    }


def get_cron_preview() -> Dict[str, Any]:
    """
    Compares the current crontab with jobs.json and returns a preview of changes.
    This version is robust and correctly identifies changes based on the final
    cron line content, which naturally includes the zone.
    """
    now = datetime.now().isoformat()
    logger.info(f"[cron_service] get_cron_preview called at {now}")

    status_data = get_cron_status()
    if status_data.get("error"):
        return status_data

    current_cron_set = set(status_data["current_cron_jobs"])
    expected_cron_set = set(status_data["expected_cron_jobs"])

    logger.info(f"[cron_service] Preview - Current normalized lines: {current_cron_set}")
    logger.info(f"[cron_service] Preview - Expected normalized lines: {expected_cron_set}")

    if current_cron_set == expected_cron_set:
        logger.info("[cron_service] Preview - No changes detected.")
        return {
            "has_changes": False,
            "total_changes": 0,
            "job_details": [],
            "timestamp": now,
        }

    # Use sets to find what's changed
    lines_to_add = expected_cron_set - current_cron_set
    lines_to_remove = current_cron_set - expected_cron_set

    job_details = []

    # Map expected cron lines back to their job objects for rich details
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    if cronblock.cron_manager is None:
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    jobs_store = JobsStore(app_support_dir)
    all_jobs = jobs_store.get_all_jobs()

    expected_line_to_job = {}
    for _, jobs in all_jobs.items():
        for job in jobs:
            cron_line = cronblock.cron_manager._job_to_cron_line(job)
            if cron_line:
                normalized_line = _normalize_cron_line(cron_line)
                expected_line_to_job[normalized_line] = job

    for line in lines_to_add:
        found_job: Optional[Job] = expected_line_to_job.get(line)
        if found_job is not None:
            job_details.append(
                {
                    "zone": found_job.zone,
                    "job": found_job.to_dict(),
                    "cron_line": line,
                    "status": "will_add",
                }
            )
        else:
            job_details.append(
                {
                    "zone": "Unknown",
                    "job": None,
                    "cron_line": line,
                    "status": "will_add",
                }
            )

    for line in lines_to_remove:
        # We can't easily map a removed line back to a job if the job was deleted,
        # so we just show the line itself.
        job_details.append(
            {
                "zone": "Unknown",
                "job": None,
                "cron_line": line,
                "status": "will_remove",
            }
        )

    total_changes = len(job_details)
    has_changes = total_changes > 0
    logger.info(f"[cron_service] Preview - Found {total_changes} changes.")

    return {
        "has_changes": has_changes,
        "total_changes": total_changes,
        "job_details": job_details,
        "timestamp": now,
    }


def get_current_cron_jobs() -> Dict[str, Any]:
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    current_lines = cronblock.cron_manager._get_current_crontab()
    aircron_lines = []
    in_aircron_section = False
    for line in current_lines:
        if line.strip() == cronblock.AIRCRON_BEGIN:
            in_aircron_section = True
            aircron_lines.append(line)
        elif line.strip() == cronblock.AIRCRON_END:
            in_aircron_section = False
            aircron_lines.append(line)
            break
        elif in_aircron_section:
            aircron_lines.append(line)
    return {
        "aircron_section": aircron_lines,
        "has_section": len(aircron_lines) > 0,
        "total_lines": len(aircron_lines),
    }


def get_all_cron_jobs() -> Dict[str, Any]:
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    all_jobs = jobs_store.get_all_jobs()
    status_data = get_cron_status()
    if status_data.get("error"):
        return status_data
    current_cron_jobs = set(status_data["current_cron_jobs"])
    jobs_with_status: Dict[str, List[Dict[str, Any]]] = {}
    for zone, jobs in all_jobs.items():
        jobs_with_status[zone] = []
        for job in jobs:
            cron_line = cronblock.cron_manager._job_to_cron_line(job)
            status = "pending"
            if cron_line and _normalize_cron_line(cron_line) in current_cron_jobs:
                status = "applied"
            jobs_with_status[zone].append({**job.to_dict(), "status": status})
    return {
        "zones": jobs_with_status,
        "total_jobs": sum(len(jobs) for jobs in jobs_with_status.values()),
        "has_jobs": bool(jobs_with_status),
    }
