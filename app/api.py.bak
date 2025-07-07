"""AirCron API endpoints."""

import logging
from typing import Any, Dict, List
import json
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app

from . import cronblock
from .jobs_store import Job, JobsStore
from .speakers import speaker_discovery

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


@api_bp.route("/speakers", methods=["GET"])
def get_speakers() -> Any:
    """Get current connected speakers from Airfoil."""
    try:
        speakers = speaker_discovery.get_available_speakers()
        return jsonify(speakers)
    except Exception as e:
        logger.error(f"Error getting speakers: {e}")
        return jsonify({"error": "Failed to get speakers"}), 500


@api_bp.route("/speakers/refresh", methods=["POST"])
def refresh_speakers() -> Any:
    """Force refresh of speaker list."""
    try:
        speakers = speaker_discovery.refresh_speakers()
        return jsonify(speakers)
    except Exception as e:
        logger.error(f"Error refreshing speakers: {e}")
        return jsonify({"error": "Failed to refresh speakers"}), 500


@api_bp.route("/jobs/<zone>", methods=["GET"])
def get_jobs_for_zone(zone: str) -> Any:
    """Get all jobs for a specific zone."""
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        jobs = jobs_store.get_jobs_for_zone(zone)
        return jsonify([job.to_dict() for job in jobs])
    except Exception as e:
        logger.error(f"Error getting jobs for zone {zone}: {e}")
        return jsonify({"error": f"Failed to get jobs for zone {zone}"}), 500


@api_bp.route("/jobs/<zone>", methods=["POST"])
def create_job(zone: str) -> Any:
    """Create a new job for the specified zone."""
    logger.info(f"[API] POST /jobs/{zone} - incoming request")
    try:
        data = request.get_json()
        logger.info(f"[API] POST /jobs/{zone} - data: {data}")
        if not data:
            logger.warning(f"[API] POST /jobs/{zone} - No JSON data provided")
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate required fields
        required_fields = ["days", "time", "action"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate time format
        time_str = data["time"]
        try:
            hour, minute = time_str.split(":")
            hour = int(hour)
            minute = int(minute)
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Invalid time range")
        except (ValueError, IndexError):
            return jsonify({"error": "Invalid time format (use HH:MM)"}), 400
        
        # Validate days
        days = data["days"]
        days = [int(day) for day in days]
        if not isinstance(days, list) or not days:
            return jsonify({"error": "Days must be a non-empty list"}), 400
        
        for day in days:
            if not isinstance(day, int) or day < 1 or day > 7:
                return jsonify({"error": "Days must be integers 1-7 (1=Monday, 7=Sunday)"}), 400
        
        # Validate action
        action = data["action"]
        valid_actions = ["play", "pause", "resume", "volume"]
        if action not in valid_actions:
            return jsonify({"error": f"Invalid action. Must be one of: {valid_actions}"}), 400
        
        # Validate args based on action
        args = data.get("args", {})
        if action == "play" and "uri" not in args:
            return jsonify({"error": "Play action requires 'uri' in args"}), 400
        elif action == "volume" and "volume" not in args:
            return jsonify({"error": "Volume action requires 'volume' in args"}), 400
        
        # Validate cron syntax
        if cronblock.cron_manager is None:
            # Initialize if not already done
            from flask import current_app
            app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
        
        if not cronblock.cron_manager.validate_cron_syntax(time_str, days):
            return jsonify({"error": "Invalid cron syntax"}), 400
        
        # Create job
        from flask import current_app
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
        logger.info(f"[API] POST /jobs/{zone} - Created job {job_id} for zone {zone}")
        
        return jsonify(job.to_dict()), 201
        
    except ValueError as e:
        logger.warning(f"[API] POST /jobs/{zone} - ValueError: {e}")
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        logger.error(f"[API] POST /jobs/{zone} - Exception: {e}", exc_info=True)
        return jsonify({"error": "Failed to create job"}), 500


@api_bp.route("/jobs/<zone>/<job_id>", methods=["PUT"])
def update_job(zone: str, job_id: str) -> Any:
    """Update an existing job."""
    logger.info(f"[API] PUT /jobs/{zone}/{job_id} - incoming request")
    try:
        data = request.get_json()
        logger.info(f"[API] PUT /jobs/{zone}/{job_id} - data: {data}")
        if not data:
            logger.warning(f"[API] PUT /jobs/{zone}/{job_id} - No JSON data provided")
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate fields if provided (partial updates allowed)
        if "time" in data:
            time_str = data["time"]
            try:
                hour, minute = time_str.split(":")
                hour = int(hour)
                minute = int(minute)
                if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                    raise ValueError("Invalid time range")
            except (ValueError, IndexError):
                return jsonify({"error": "Invalid time format (use HH:MM)"}), 400
        
        if "days" in data:
            days = data["days"]
            days = [int(day) for day in days]
            if not isinstance(days, list) or not days:
                return jsonify({"error": "Days must be a non-empty list"}), 400
            
            for day in days:
                if not isinstance(day, int) or day < 1 or day > 7:
                    return jsonify({"error": "Days must be integers 1-7"}), 400
        
        if "action" in data:
            action = data["action"]
            valid_actions = ["play", "pause", "resume", "volume"]
            if action not in valid_actions:
                return jsonify({"error": f"Invalid action. Must be one of: {valid_actions}"}), 400
        
        # Get existing job
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        existing_jobs = jobs_store.get_jobs_for_zone(zone)
        existing_job = None
        for job in existing_jobs:
            if job.id == job_id:
                existing_job = job
                break
        
        if not existing_job:
            return jsonify({"error": "Job not found"}), 404
        
        # Update job fields
        updated_job = Job(
            job_id=job_id,
            zone=zone,
            days=data.get("days", existing_job.days),
            time=data.get("time", existing_job.time),
            action=data.get("action", existing_job.action),
            args=data.get("args", existing_job.args),
            label=data.get("label", getattr(existing_job, "label", ""))
        )
        
        # Validate cron syntax for updated job
        if cronblock.cron_manager is None:
            from flask import current_app
            app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
            
        if not cronblock.cron_manager.validate_cron_syntax(updated_job.time, updated_job.days):
            return jsonify({"error": "Invalid cron syntax"}), 400
        
        jobs_store.update_job(updated_job)
        logger.info(f"[API] PUT /jobs/{zone}/{job_id} - Updated job {job_id} in zone {zone}")
        
        return jsonify(updated_job.to_dict())
        
    except ValueError as e:
        logger.warning(f"[API] PUT /jobs/{zone}/{job_id} - ValueError: {e}")
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        logger.error(f"[API] PUT /jobs/{zone}/{job_id} - Exception: {e}", exc_info=True)
        return jsonify({"error": "Failed to update job"}), 500


@api_bp.route("/jobs/<zone>/<job_id>", methods=["DELETE"])
def delete_job(zone: str, job_id: str) -> Any:
    """Delete a job."""
    logger.info(f"[API] DELETE /jobs/{zone}/{job_id} - incoming request")
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        jobs_store.delete_job(zone, job_id)
        logger.info(f"[API] DELETE /jobs/{zone}/{job_id} - Deleted job {job_id} from zone {zone}")
        
        # Return empty div for HTMX to replace the deleted job element
        return '<div style="display: none;"></div>', 200
        
    except ValueError as e:
        logger.warning(f"[API] DELETE /jobs/{zone}/{job_id} - ValueError: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"[API] DELETE /jobs/{zone}/{job_id} - Exception: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete job"}), 500


@api_bp.route("/cron/apply", methods=["POST"])
def apply_cron() -> Any:
    """Apply all jobs from store to crontab."""
    try:
        from . import cronblock
        if cronblock.cron_manager is None:
            from flask import current_app
            app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
        
        # Log the current state before applying
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        all_jobs = jobs_store.get_all_jobs()
        total_jobs = sum(len(jobs) for jobs in all_jobs.values())
        logger.info(f"Apply cron called with {len(all_jobs)} zones and {total_jobs} total jobs")
        
        # Apply jobs to cron (this includes clearing cron if no jobs exist)
        cronblock.cron_manager.apply_jobs_to_cron()
        
        if total_jobs == 0:
            logger.info("Successfully cleared all jobs from crontab")
        else:
            logger.info("Successfully applied jobs to crontab")
        
        return jsonify({"ok": True})
        
    except Exception as e:
        logger.error(f"Error applying jobs to cron: {e}", exc_info=True)
        return jsonify({"error": f"Failed to apply jobs to cron: {str(e)}"}), 500


@api_bp.route("/status", methods=["GET"])
def get_status() -> Any:
    """Get system status."""
    try:
        airfoil_running = speaker_discovery.is_airfoil_running()
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        all_jobs = jobs_store.get_all_jobs()
        total_jobs = sum(len(jobs) for jobs in all_jobs.values())
        
        return jsonify({
            "airfoil_running": airfoil_running,
            "total_jobs": total_jobs,
            "zones": list(all_jobs.keys())
        })
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({"error": "Failed to get status"}), 500


def _normalize_cron_line(line: str) -> str:
    """Normalize a cron line for comparison (strip, collapse whitespace, remove quotes)."""
    import re
    line = line.strip()
    line = re.sub(r'\s+', ' ', line)
    line = line.replace('"', '').replace("'", '')
    return line


@api_bp.route("/cron/status", methods=["GET"])
def get_cron_status() -> Any:
    """Get status of cron application (whether jobs are applied to cron)."""
    try:
        from . import cronblock
        if cronblock.cron_manager is None:
            app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
        
        # Get current crontab
        current_lines = cronblock.cron_manager._get_current_crontab()
        
        # Check if AirCron section exists and extract current cron jobs
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
                # This is a cron job line
                current_cron_jobs.append(_normalize_cron_line(line))
        
        # Get stored jobs and generate what cron should look like
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        all_jobs = jobs_store.get_all_jobs()
        total_stored_jobs = sum(len(jobs) for jobs in all_jobs.values())
        
        # Generate expected cron lines
        expected_cron_lines = []
        for zone, jobs in all_jobs.items():
            for job in jobs:
                cron_line = cronblock.cron_manager._job_to_cron_line(job)
                if cron_line:
                    expected_cron_lines.append(_normalize_cron_line(cron_line))
        
        # Compare current vs expected cron jobs
        has_jobs_in_cron = len(current_cron_jobs) > 0
        jobs_match = set(current_cron_jobs) == set(expected_cron_lines)
        needs_apply = total_stored_jobs > 0 and not jobs_match
        
        return jsonify({
            "has_aircron_section": has_aircron_section,
            "has_jobs_in_cron": has_jobs_in_cron,
            "total_stored_jobs": total_stored_jobs,
            "current_cron_jobs_count": len(current_cron_jobs),
            "expected_cron_jobs_count": len(expected_cron_lines),
            "jobs_match": jobs_match,
            "needs_apply": needs_apply,
            "current_cron_jobs": current_cron_jobs,
            "expected_cron_jobs": expected_cron_lines
        })
        
    except Exception as e:
        logger.error(f"Error getting cron status: {e}")
        return jsonify({"error": "Failed to get cron status"}), 500


def _get_json_response(resp):
    """Helper to always get the JSON from a Flask response, even if it's a (resp, status) tuple."""
    if isinstance(resp, tuple):
        return resp[0].get_json()
    return resp.get_json()


@api_bp.route("/cron/preview", methods=["GET"])
def get_cron_preview() -> Any:
    """Get preview of changes that will be made when applying jobs to cron."""
    try:
        from . import cronblock
        if cronblock.cron_manager is None:
            app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)

        # Get current cron status
        status_response = get_cron_status()
        status_data = _get_json_response(status_response)

        if status_data.get("error"):
            return status_response

        current_cron_jobs = set(status_data["current_cron_jobs"])
        expected_cron_jobs = set(status_data["expected_cron_jobs"])

        jobs_to_add = expected_cron_jobs - current_cron_jobs
        jobs_to_remove = current_cron_jobs - expected_cron_jobs
        jobs_unchanged = current_cron_jobs & expected_cron_jobs

        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        all_jobs = jobs_store.get_all_jobs()

        # Build mapping: normalized cron line -> job dict (for jobs in store)
        cron_to_job = {}
        id_to_job = {}
        for zone, jobs in all_jobs.items():
            for job in jobs:
                cron_line = cronblock.cron_manager._job_to_cron_line(job)
                if cron_line:
                    norm_line = _normalize_cron_line(cron_line)
                    cron_to_job[norm_line] = job
                    id_to_job[job.id] = job

        # Try to parse removed cron lines to job-like dicts
        def parse_cron_line(line: str) -> dict:
            # Try to extract zone, time, action, args from cron line
            import re
            # Example: 30 7 * * 1,2,3,4,5 /usr/local/bin/aircron_run.sh "Kitchen" play "spotify:playlist:..."
            parts = line.strip().split()
            if len(parts) < 8:
                return {"raw": line}
            minute, hour = parts[0], parts[1]
            days = parts[5]
            cmd = parts[6:]
            # Find quoted zone
            zone = None
            action = None
            args = {}
            label = None
            try:
                # Find quoted strings
                quoted = re.findall(r'"([^"]+)"', line)
                if quoted:
                    zone = quoted[0]
                # Action is next after zone
                after_zone = line.split('"'+zone+'"',1)[1]
                action_match = re.search(r'\b(play|pause|resume|volume)\b', after_zone)
                if action_match:
                    action = action_match.group(1)
                # Args
                if action == "play":
                    uri_match = re.search(r'play\s+"([^"]+)"', after_zone)
                    if uri_match:
                        args["uri"] = uri_match.group(1)
                elif action == "volume":
                    vol_match = re.search(r'volume\s+(\d+)', after_zone)
                    if vol_match:
                        args["volume"] = vol_match.group(1)
            except Exception:
                pass
            # Days: convert cron days to AirCron days (0=Sun, 1=Mon...6=Sat)
            cron_days = days.split(",")
            aircron_days = []
            for d in cron_days:
                if d == "0":
                    aircron_days.append(7)
                else:
                    try:
                        aircron_days.append(int(d))
                    except Exception:
                        pass
            return {
                "zone": zone,
                "days": aircron_days,
                "time": f"{int(hour):02d}:{int(minute):02d}",
                "action": action,
                "args": args,
                "label": label,
                "raw": line
            }

        # Build mapping for removed jobs
        removed_jobs = []
        for line in jobs_to_remove:
            # Try to find a matching job in the store (by cron line)
            job = cron_to_job.get(line)
            if job:
                removed_jobs.append({
                    "zone": job.zone,
                    "job": job.to_dict(),
                    "cron_line": line,
                    "status": "will_remove"
                })
            else:
                # Try to parse
                parsed = parse_cron_line(line)
                removed_jobs.append({
                    "zone": parsed.get("zone"),
                    "job": parsed,
                    "cron_line": line,
                    "status": "will_remove"
                })

        # Detect changed jobs (edits):
        # Heuristic: if a job with the same ID exists in both removed and added, it's an edit
        # Build mapping: job signature (zone+label+action+time) -> job for both old and new
        def job_signature(job):
            # Use ID if present, else fallback to zone+label+action+time
            if isinstance(job, dict):
                return (job.get("id"), job.get("zone"), job.get("label"), job.get("action"), job.get("time"))
            return (getattr(job, "id", None), getattr(job, "zone", None), getattr(job, "label", None), getattr(job, "action", None), getattr(job, "time", None))

        # Map added jobs
        added_jobs_map = {}
        for line in jobs_to_add:
            job = cron_to_job.get(line)
            if job:
                sig = job_signature(job)
                added_jobs_map[sig] = job

        # Map removed jobs
        removed_jobs_map = {}
        for rj in removed_jobs:
            sig = job_signature(rj["job"])
            removed_jobs_map[sig] = rj["job"]

        # Find changed jobs (edit): present in both add and remove by signature (ID or fallback)
        changed_jobs = []
        matched_sigs = set()
        for sig in removed_jobs_map:
            if sig in added_jobs_map:
                old_job = removed_jobs_map[sig]
                new_job = added_jobs_map[sig]
                # Compute field diffs
                diffs = []
                for field in ["zone", "label", "days", "time", "action", "args"]:
                    old_val = old_job.get(field) if isinstance(old_job, dict) else getattr(old_job, field, None)
                    new_val = new_job.to_dict()[field] if hasattr(new_job, "to_dict") else new_job.get(field)
                    if old_val != new_val:
                        diffs.append({"field": field, "old": old_val, "new": new_val})
                changed_jobs.append({
                    "old_job": old_job if isinstance(old_job, dict) else old_job.to_dict(),
                    "new_job": new_job.to_dict() if hasattr(new_job, "to_dict") else new_job,
                    "diffs": diffs
                })
                matched_sigs.add(sig)

        # Remove changed jobs from will_add/will_remove
        jobs_to_add_final = [line for line in jobs_to_add if job_signature(cron_to_job.get(line)) not in matched_sigs]
        removed_jobs_final = [rj for rj in removed_jobs if job_signature(rj["job"]) not in matched_sigs]

        # Build job_details for UI
        job_details = []
        for zone, jobs in all_jobs.items():
            for job in jobs:
                cron_line = cronblock.cron_manager._job_to_cron_line(job)
                if cron_line:
                    norm_line = _normalize_cron_line(cron_line)
                    status = "unchanged"
                    if norm_line in jobs_to_add_final:
                        status = "will_add"
                    elif norm_line in jobs_to_remove:
                        status = "will_remove"
                    job_details.append({
                        "zone": zone,
                        "job": job.to_dict(),
                        "cron_line": cron_line,
                        "status": status
                    })
        # Add removed jobs not in store
        for rj in removed_jobs_final:
            job_details.append(rj)

        preview = {
            "will_add": list(jobs_to_add_final),
            "will_remove": [rj["cron_line"] for rj in removed_jobs_final],
            "will_keep": list(jobs_unchanged),
            "total_changes": len(jobs_to_add_final) + len(removed_jobs_final) + len(changed_jobs),
            "has_changes": len(jobs_to_add_final) > 0 or len(removed_jobs_final) > 0 or len(changed_jobs) > 0,
            "job_details": job_details,
            "changed_jobs": changed_jobs
        }
        return jsonify(preview)
    except Exception as e:
        logger.error(f"Error getting cron preview: {e}")
        return jsonify({"error": "Failed to get cron preview"}), 500


@api_bp.route("/cron/current", methods=["GET"])
def get_current_cron_jobs() -> Any:
    """Get all current cron jobs within AirCron section."""
    try:
        from . import cronblock
        if cronblock.cron_manager is None:
            from flask import current_app
            app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
        
        # Get current crontab
        current_lines = cronblock.cron_manager._get_current_crontab()
        
        # Extract AirCron section
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
        
        return jsonify({
            "aircron_section": aircron_lines,
            "has_section": len(aircron_lines) > 0,
            "total_lines": len(aircron_lines)
        })
        
    except Exception as e:
        logger.error(f"Error getting current cron jobs: {e}")
        return jsonify({"error": "Failed to get current cron jobs"}), 500


@api_bp.route("/cron/jobs", methods=["GET"])
def get_all_cron_jobs() -> Any:
    """Get all jobs that are currently applied to cron, organized by zone."""
    try:
        from . import cronblock
        if cronblock.cron_manager is None:
            app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
        
        # Get all stored jobs
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        all_jobs = jobs_store.get_all_jobs()
        
        # Get current cron status to filter only applied jobs
        status_response = get_cron_status()
        status_data = _get_json_response(status_response)
        
        if status_data.get("error"):
            return status_response
        
        current_cron_jobs = set(status_data["current_cron_jobs"])
        
        # Filter jobs to only include those that are actually in cron
        applied_jobs = {}
        for zone, jobs in all_jobs.items():
            zone_applied_jobs = []
            for job in jobs:
                cron_line = cronblock.cron_manager._job_to_cron_line(job)
                if cron_line and _normalize_cron_line(cron_line) in current_cron_jobs:
                    zone_applied_jobs.append(job.to_dict())
            if zone_applied_jobs:
                applied_jobs[zone] = zone_applied_jobs
        
        return jsonify({
            "zones": applied_jobs,
            "total_jobs": sum(len(jobs) for jobs in applied_jobs.values()),
            "has_jobs": len(applied_jobs) > 0
        })
        
    except Exception as e:
        logger.error(f"Error getting all cron jobs: {e}")
        return jsonify({"error": "Failed to get all cron jobs"}), 500


@api_bp.route("/playlists", methods=["GET"])
def get_playlists() -> Any:
    """Get all saved playlists."""
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        playlists_file = app_support_dir / "playlists.json"
        
        if not playlists_file.exists():
            return jsonify({"playlists": []})
        
        with playlists_file.open() as f:
            data = json.load(f)
        
        return jsonify(data)
        
    except Exception as e:
        logger.error(f"Error getting playlists: {e}")
        return jsonify({"error": "Failed to get playlists"}), 500


@api_bp.route("/playlists", methods=["POST"])
def create_playlist() -> Any:
    """Create a new playlist."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Validate required fields
        if not data.get("name"):
            return jsonify({"error": "Name is required"}), 400
        if not data.get("uri"):
            return jsonify({"error": "URI is required"}), 400
        
        # Validate Spotify URI format
        uri = data["uri"].strip()
        if not (uri.startswith("spotify:") and ("playlist:" in uri or "album:" in uri or "track:" in uri)):
            return jsonify({"error": "Invalid Spotify URI format"}), 400
        
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        playlists_file = app_support_dir / "playlists.json"
        
        # Load existing playlists
        if playlists_file.exists():
            with playlists_file.open() as f:
                playlists_data = json.load(f)
        else:
            playlists_data = {"playlists": []}
        
        # Check for duplicate names
        for playlist in playlists_data["playlists"]:
            if playlist["name"].lower() == data["name"].strip().lower():
                return jsonify({"error": "A playlist with this name already exists"}), 409
        
        # Create new playlist
        from uuid import uuid4
        new_playlist = {
            "id": str(uuid4())[:8],
            "name": data["name"].strip(),
            "description": data.get("description", "").strip(),
            "uri": uri,
            "created_at": datetime.now().isoformat()
        }
        
        playlists_data["playlists"].append(new_playlist)
        
        # Save to file
        with playlists_file.open("w") as f:
            json.dump(playlists_data, f, indent=2)
        
        logger.info(f"Created playlist: {new_playlist['name']}")
        return jsonify(new_playlist), 201
        
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        return jsonify({"error": "Failed to create playlist"}), 500


@api_bp.route("/playlists/<playlist_id>", methods=["PUT"])
def update_playlist(playlist_id: str) -> Any:
    """Update an existing playlist."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        playlists_file = app_support_dir / "playlists.json"
        
        if not playlists_file.exists():
            return jsonify({"error": "Playlist not found"}), 404
        
        with playlists_file.open() as f:
            playlists_data = json.load(f)
        
        # Find playlist to update
        playlist_to_update = None
        for i, playlist in enumerate(playlists_data["playlists"]):
            if playlist["id"] == playlist_id:
                playlist_to_update = playlist
                playlist_index = i
                break
        
        if not playlist_to_update:
            return jsonify({"error": "Playlist not found"}), 404
        
        # Validate and update fields
        if "name" in data:
            name = data["name"].strip()
            if not name:
                return jsonify({"error": "Name cannot be empty"}), 400
            
            # Check for duplicate names (excluding current playlist)
            for playlist in playlists_data["playlists"]:
                if playlist["id"] != playlist_id and playlist["name"].lower() == name.lower():
                    return jsonify({"error": "A playlist with this name already exists"}), 409
            
            playlist_to_update["name"] = name
        
        if "description" in data:
            playlist_to_update["description"] = data["description"].strip()
        
        if "uri" in data:
            uri = data["uri"].strip()
            if not (uri.startswith("spotify:") and ("playlist:" in uri or "album:" in uri or "track:" in uri)):
                return jsonify({"error": "Invalid Spotify URI format"}), 400
            playlist_to_update["uri"] = uri
        
        playlist_to_update["updated_at"] = datetime.now().isoformat()
        
        # Save to file
        with playlists_file.open("w") as f:
            json.dump(playlists_data, f, indent=2)
        
        logger.info(f"Updated playlist: {playlist_to_update['name']}")
        return jsonify(playlist_to_update)
        
    except Exception as e:
        logger.error(f"Error updating playlist: {e}")
        return jsonify({"error": "Failed to update playlist"}), 500


@api_bp.route("/playlists/<playlist_id>", methods=["DELETE"])
def delete_playlist(playlist_id: str) -> Any:
    """Delete a playlist."""
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        playlists_file = app_support_dir / "playlists.json"
        
        if not playlists_file.exists():
            return jsonify({"error": "Playlist not found"}), 404
        
        with playlists_file.open() as f:
            playlists_data = json.load(f)
        
        # Find and remove playlist
        original_count = len(playlists_data["playlists"])
        playlists_data["playlists"] = [
            p for p in playlists_data["playlists"] if p["id"] != playlist_id
        ]
        
        if len(playlists_data["playlists"]) == original_count:
            return jsonify({"error": "Playlist not found"}), 404
        
        # Save to file
        with playlists_file.open("w") as f:
            json.dump(playlists_data, f, indent=2)
        
        logger.info(f"Deleted playlist: {playlist_id}")
        return "", 204
        
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        return jsonify({"error": "Failed to delete playlist"}), 500


@api_bp.route("/jobs/all", methods=["GET"])
def get_all_jobs_flat() -> Any:
    """Return all jobs as a flat list for the view schedule tab."""
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        all_jobs = jobs_store.get_all_jobs()
        jobs_flat = []
        for zone, jobs in all_jobs.items():
            for job in jobs:
                job_dict = job.to_dict()
                job_dict["zone"] = zone  # ensure zone is present
                jobs_flat.append(job_dict)
        return jsonify({"jobs": jobs_flat})
    except Exception as e:
        logger.error(f"Error getting all jobs flat: {e}")
        return jsonify({"error": "Failed to get jobs"}), 500 