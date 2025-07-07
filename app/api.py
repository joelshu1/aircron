"""AirCron API endpoints."""

import logging
from typing import Any, Dict, List
import json
from datetime import datetime

from flask import Blueprint, jsonify, request, current_app
from werkzeug.exceptions import BadRequest

from . import cronblock
from .jobs_store import Job, JobsStore
from .speakers import speaker_discovery
from .services import jobs_service, cron_service, speakers_service, playlists_service
from .cronblock import _normalize_cron_line

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


@api_bp.route("/speakers", methods=["GET"])
def get_speakers() -> Any:
    """Get current connected speakers from Airfoil."""
    try:
        speakers = speakers_service.list_speakers()
        return jsonify({"speakers": speakers})
    except Exception as e:
        logger.error(f"Error listing speakers: {e}")
        return jsonify({"error": "Failed to list speakers"}), 500


@api_bp.route("/speakers/refresh", methods=["POST"])
def refresh_speakers() -> Any:
    """Force refresh of speaker list."""
    try:
        result = speakers_service.refresh_speakers()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error refreshing speakers: {e}")
        return jsonify({"error": "Failed to refresh speakers"}), 500


@api_bp.route("/jobs/<zone>", methods=["GET"])
def get_jobs_for_zone(zone: str) -> Any:
    """Get all jobs for a specific zone."""
    try:
        jobs = jobs_service.get_jobs_for_zone(zone)
        return jsonify(jobs)
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
        job = jobs_service.create_job(zone, data)
        logger.info(f"[API] POST /jobs/{zone} - Created job {job['id']} for zone {zone}")
        return jsonify(job), 201
    except ValueError as e:
        msg = str(e)
        if (
            'Invalid time format' in msg or 'Invalid time range' in msg or
            'Missing required field' in msg or
            'Days must be integers' in msg or 'Days must be a non-empty list' in msg or
            'Invalid action' in msg
        ):
            logger.warning(f"[API] POST /jobs/{zone} - BadRequest: {e}")
            return jsonify({"error": msg}), 400
        logger.warning(f"[API] POST /jobs/{zone} - ValueError: {e}")
        return jsonify({"error": msg}), 409
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
        job = jobs_service.update_job(zone, job_id, data)
        logger.info(f"[API] PUT /jobs/{zone}/{job_id} - Updated job {job_id} in zone {zone}")
        return jsonify(job)
    except ValueError as e:
        msg = str(e)
        if 'Job not found' in msg:
            logger.warning(f"[API] PUT /jobs/{zone}/{job_id} - NotFound: {e}")
            return jsonify({"error": msg}), 404
        logger.warning(f"[API] PUT /jobs/{zone}/{job_id} - ValueError: {e}")
        return jsonify({"error": msg}), 409
    except Exception as e:
        logger.error(f"[API] PUT /jobs/{zone}/{job_id} - Exception: {e}", exc_info=True)
        return jsonify({"error": "Failed to update job"}), 500


@api_bp.route("/jobs/<zone>/<job_id>", methods=["DELETE"])
def delete_job(zone: str, job_id: str) -> Any:
    """Delete a job."""
    logger.info(f"[API] DELETE /jobs/{zone}/{job_id} - incoming request")
    try:
        jobs_service.delete_job(zone, job_id)
        logger.info(f"[API] DELETE /jobs/{zone}/{job_id} - Deleted job {job_id} from zone {zone}")
        return '<div style="display: none;"></div>', 200
    except ValueError as e:
        logger.warning(f"[API] DELETE /jobs/{zone}/{job_id} - ValueError: {e}")
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"[API] DELETE /jobs/{zone}/{job_id} - Exception: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete job"}), 500


@api_bp.route("/cron/apply", methods=["POST"])
def apply_jobs_to_cron() -> Any:
    try:
        result = cron_service.apply_jobs_to_cron()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error applying jobs to cron: {e}")
        return jsonify({"error": "Failed to apply jobs to cron"}), 500


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


@api_bp.route("/cron/status", methods=["GET"])
def get_cron_status() -> Any:
    try:
        result = cron_service.get_cron_status()
        # If result['cron_desync'] is True, frontend should prompt user to apply jobs
        return jsonify(result)
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
    try:
        result = cron_service.get_cron_preview()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting cron preview: {e}")
        return jsonify({"error": "Failed to get cron preview"}), 500


@api_bp.route("/cron/current", methods=["GET"])
def get_current_cron_jobs() -> Any:
    try:
        result = cron_service.get_current_cron_jobs()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting current cron jobs: {e}")
        return jsonify({"error": "Failed to get current cron jobs"}), 500


@api_bp.route("/cron/all", methods=["GET"])
def get_all_cron_jobs() -> Any:
    try:
        result = cron_service.get_all_cron_jobs()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting all cron jobs: {e}")
        return jsonify({"error": "Failed to get all cron jobs"}), 500


@api_bp.route("/playlists", methods=["GET"])
def get_playlists() -> Any:
    try:
        playlists = playlists_service.list_playlists()
        return jsonify({"playlists": playlists})
    except Exception as e:
        logger.error(f"Error getting playlists: {e}")
        return jsonify({"error": "Failed to get playlists"}), 500


@api_bp.route("/playlists", methods=["POST"])
def create_playlist() -> Any:
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        result = playlists_service.create_playlist(data)
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Error creating playlist: {e}")
        return jsonify({"error": "Failed to create playlist"}), 500


@api_bp.route("/playlists/<playlist_id>", methods=["PUT"])
def update_playlist(playlist_id: str) -> Any:
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        result = playlists_service.update_playlist(playlist_id, data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error updating playlist: {e}")
        return jsonify({"error": "Failed to update playlist"}), 500


@api_bp.route("/playlists/<playlist_id>", methods=["DELETE"])
def delete_playlist(playlist_id: str) -> Any:
    try:
        result = playlists_service.delete_playlist(playlist_id)
        return "", 204
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}")
        return jsonify({"error": "Failed to delete playlist"}), 500


@api_bp.route("/jobs/all", methods=["GET"])
def get_all_jobs_flat() -> Any:
    """Return all jobs as a flat list for the view schedule tab."""
    try:
        jobs_flat = jobs_service.get_all_jobs_flat()
        return jsonify({"jobs": jobs_flat})
    except Exception as e:
        logger.error(f"Error getting all jobs flat: {e}")
        return jsonify({"error": "Failed to get jobs"}), 500 