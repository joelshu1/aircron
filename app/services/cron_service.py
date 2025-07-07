import logging
from typing import Any, Dict
from flask import current_app, jsonify
from .. import cronblock
from ..jobs_store import JobsStore
import json
from ..cronblock import _normalize_cron_line
from datetime import datetime

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
    logger.info(f"[cron_service] Apply cron called with {len(all_jobs)} zones and {total_jobs} total jobs")
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
        logger.warning("[cron_service] Detected desync: jobs.json has jobs but AirCron block is empty!")
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
        "cron_desync": cron_desync
    }

def get_cron_preview() -> Dict[str, Any]:
    if cronblock.cron_manager is None:
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        cronblock.cron_manager = cronblock.CronManager(app_support_dir)
    status_data = get_cron_status()
    if status_data.get("error"):
        return status_data
    # Add timestamp for debug
    now = datetime.now().isoformat()
    logger.info(f"[cron_service] get_cron_preview called at {now}")
    # Log current crontab lines
    current_lines = cronblock.cron_manager._get_current_crontab()
    logger.info(f"[cron_service] Current crontab lines: {current_lines}")
    # Log jobs.json contents
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    all_jobs = jobs_store.get_all_jobs()
    logger.info(f"[cron_service] jobs.json contents: {all_jobs}")
    # Log normalized cron lines
    current_cron_jobs = set(status_data["current_cron_jobs"])
    expected_cron_jobs = set(status_data["expected_cron_jobs"])
    logger.info(f"[cron_service] Normalized current_cron_jobs: {current_cron_jobs}")
    logger.info(f"[cron_service] Normalized expected_cron_jobs: {expected_cron_jobs}")
    # If the sets are identical, there are no changes to apply
    if current_cron_jobs == expected_cron_jobs:
        logger.info(f"[cron_service] No changes to apply: crontab and jobs.json are in sync.")
        return {
            "has_changes": False,
            "total_changes": 0,
            "job_details": [],
            "changed_jobs": [],
            "timestamp": now
        }
    # Compute diffs
    jobs_to_add = expected_cron_jobs - current_cron_jobs
    jobs_to_remove = current_cron_jobs - expected_cron_jobs
    jobs_unchanged = current_cron_jobs & expected_cron_jobs
    logger.info(f"[cron_service] jobs_to_add: {jobs_to_add}")
    logger.info(f"[cron_service] jobs_to_remove: {jobs_to_remove}")
    logger.info(f"[cron_service] jobs_unchanged: {jobs_unchanged}")
    # Build job_details and changed_jobs as before
    cron_to_job = {}
    id_to_job = {}
    for zone, jobs in all_jobs.items():
        for job in jobs:
            cron_line = cronblock.cron_manager._job_to_cron_line(job)
            if cron_line:
                norm_line = _normalize_cron_line(cron_line)
                cron_to_job[norm_line] = job
                id_to_job[job.id] = job
    job_details = []
    changed_jobs = []
    crontab_lines = list(current_cron_jobs)
    for zone, jobs in all_jobs.items():
        for job in jobs:
            expected_line = _normalize_cron_line(cronblock.cron_manager._job_to_cron_line(job))
            if expected_line in jobs_to_add:
                job_details.append({
                    "zone": job.zone,
                    "job": job.to_dict(),
                    "cron_line": expected_line,
                    "status": "will_add"
                })
            else:
                for line in crontab_lines:
                    cr_job = cron_to_job.get(line)
                    if not cr_job:
                        continue
                    diffs = []
                    for field in ["time", "days", "action", "args", "label"]:
                        v1 = getattr(job, field, None)
                        v2 = getattr(cr_job, field, None)
                        if v1 != v2:
                            diffs.append({"field": field, "old": v2, "new": v1})
                    if diffs:
                        job_details.append({
                            "zone": job.zone,
                            "job": job.to_dict(),
                            "cron_line": expected_line,
                            "status": "changed",
                            "diffs": diffs
                        })
                        changed_jobs.append({
                            "old_job": cr_job.to_dict(),
                            "new_job": job.to_dict(),
                            "diffs": diffs
                        })
                        break
    for line in jobs_to_remove:
        job = None
        job_details.append({
            "zone": None,
            "job": None,
            "cron_line": line,
            "status": "will_remove"
        })
    for line in jobs_unchanged:
        job = cron_to_job.get(line)
        if job:
            job_details.append({
                "zone": job.zone,
                "job": job.to_dict(),
                "cron_line": line,
                "status": "unchanged"
            })
    total_changes = sum(1 for d in job_details if d["status"] != "unchanged")
    has_changes = total_changes > 0
    logger.info(f"[cron_service] changed_jobs: {changed_jobs}")
    logger.info(f"[cron_service] Returning preview: has_changes={has_changes}, total_changes={total_changes}")
    return {
        "has_changes": has_changes,
        "total_changes": total_changes,
        "job_details": job_details,
        "changed_jobs": changed_jobs,
        "timestamp": now
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
        "total_lines": len(aircron_lines)
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
    applied_jobs = {}
    for zone, jobs in all_jobs.items():
        zone_applied_jobs = []
        for job in jobs:
            cron_line = cronblock.cron_manager._job_to_cron_line(job)
            if cron_line and _normalize_cron_line(cron_line) in current_cron_jobs:
                zone_applied_jobs.append(job.to_dict())
        if zone_applied_jobs:
            applied_jobs[zone] = zone_applied_jobs
    return {
        "zones": applied_jobs,
        "total_jobs": sum(len(jobs) for jobs in applied_jobs.values()),
        "has_jobs": len(applied_jobs) > 0
    } 