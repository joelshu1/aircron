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
    now = datetime.now().isoformat()
    logger.info(f"[cron_service] get_cron_preview called at {now}")
    current_lines = cronblock.cron_manager._get_current_crontab()
    logger.info(f"[cron_service] Current crontab lines: {current_lines}")
    app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
    jobs_store = JobsStore(app_support_dir)
    all_jobs = jobs_store.get_all_jobs()
    logger.info(f"[cron_service] jobs.json contents: {all_jobs}")
    current_cron_jobs = set(status_data["current_cron_jobs"])
    expected_cron_jobs = set(status_data["expected_cron_jobs"])
    logger.info(f"[cron_service] Normalized current_cron_jobs: {current_cron_jobs}")
    logger.info(f"[cron_service] Normalized expected_cron_jobs: {expected_cron_jobs}")
    # Build job dicts by ID
    expected_jobs_by_id = {}
    current_jobs_by_id = {}
    cron_to_job = {}
    for zone, jobs in all_jobs.items():
        for job in jobs:
            expected_jobs_by_id[job.id] = job
            cron_line = cronblock.cron_manager._job_to_cron_line(job)
            if cron_line:
                norm_line = _normalize_cron_line(cron_line)
                cron_to_job[norm_line] = job
    # Find jobs in crontab by parsing lines
    crontab_jobs_by_id = {}
    for zone, jobs in all_jobs.items():
        for job in jobs:
            cron_line = cronblock.cron_manager._job_to_cron_line(job)
            if cron_line and _normalize_cron_line(cron_line) in current_cron_jobs:
                crontab_jobs_by_id[job.id] = job
    # Diff by job ID
    job_details = []
    changed_jobs = []
    # 1. Changed jobs (present in both, but fields differ)
    for job_id, expected_job in expected_jobs_by_id.items():
        current_job = crontab_jobs_by_id.get(job_id)
        if current_job:
            diffs = []
            for field in ["time", "days", "action", "args", "label", "zone"]:
                v1 = getattr(expected_job, field, None)
                v2 = getattr(current_job, field, None)
                if v1 != v2:
                    diffs.append({"field": field, "old": v2, "new": v1})
            if diffs:
                job_details.append({
                    "zone": expected_job.zone,
                    "job": expected_job.to_dict(),
                    "cron_line": cronblock.cron_manager._job_to_cron_line(expected_job),
                    "status": "changed",
                    "diffs": diffs
                })
                changed_jobs.append({
                    "old_job": current_job.to_dict(),
                    "new_job": expected_job.to_dict(),
                    "diffs": diffs
                })
    # 2. Added jobs (in expected, not in crontab)
    for job_id, expected_job in expected_jobs_by_id.items():
        if job_id not in crontab_jobs_by_id:
            job_details.append({
                "zone": expected_job.zone,
                "job": expected_job.to_dict(),
                "cron_line": cronblock.cron_manager._job_to_cron_line(expected_job),
                "status": "will_add"
            })
    # 3. Removed jobs (in crontab, not in expected)
    for job_id, current_job in crontab_jobs_by_id.items():
        if job_id not in expected_jobs_by_id:
            job_details.append({
                "zone": current_job.zone,
                "job": current_job.to_dict(),
                "cron_line": cronblock.cron_manager._job_to_cron_line(current_job),
                "status": "will_remove"
            })
    # 4. Orphaned cron lines (in crontab, not mapped to any job)
    for line in current_cron_jobs:
        if line not in [ _normalize_cron_line(cronblock.cron_manager._job_to_cron_line(job)) for job in crontab_jobs_by_id.values() ]:
            job_details.append({
                "zone": None,
                "job": None,
                "cron_line": line,
                "status": "will_remove"
            })
    total_changes = len(job_details)
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
    jobs_with_status = {}
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
        "has_jobs": len(jobs_with_status) > 0
    } 