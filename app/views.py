"""AirCron HTML views."""

import logging
import json
from typing import Any

from flask import Blueprint, render_template, request

from .jobs_store import JobsStore
from .speakers import speaker_discovery
from .cronblock import _normalize_cron_line

logger = logging.getLogger(__name__)

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index() -> Any:
    """Main application page."""
    try:
        # Get zone from URL parameter if provided
        requested_zone = request.args.get('zone', 'All Speakers')
        
        # Get speakers and jobs for initial load
        speakers = speaker_discovery.get_available_speakers()
        
        # Use Flask app context for JobsStore
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        all_jobs = jobs_store.get_all_jobs()
        
        # Use requested zone or default to "All Speakers"
        current_zone = requested_zone
        current_jobs_objs = all_jobs.get(current_zone, [])
        current_jobs = [job.to_dict() for job in current_jobs_objs]
        
        # Get cron status to determine which jobs are applied
        from . import cronblock
        if cronblock.cron_manager is None:
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
        
        # Get current cron jobs
        current_lines = cronblock.cron_manager._get_current_crontab()
        current_cron_jobs = set()
        in_aircron_section = False
        
        for line in current_lines:
            line = line.strip()
            if line == cronblock.AIRCRON_BEGIN:
                in_aircron_section = True
            elif line == cronblock.AIRCRON_END:
                in_aircron_section = False
            elif in_aircron_section and line and not line.startswith("#"):
                # Normalize the cron line for comparison
                current_cron_jobs.add(_normalize_cron_line(line))
        
        # Add status to each job in current zone
        for job in current_jobs:
            job_obj = None
            for j in current_jobs_objs:
                if j.id == job['id']:
                    job_obj = j
                    break
            
            if job_obj:
                cron_line = cronblock.cron_manager._job_to_cron_line(job_obj)
                if cron_line and _normalize_cron_line(cron_line) in current_cron_jobs:
                    job['status'] = 'applied'
                else:
                    job['status'] = 'pending'
            else:
                job['status'] = 'unknown'
        
        # Always aggregate zones for sidebar from all jobs
        all_jobs_full = jobs_store.get_all_jobs()
        composite_zones = []
        individual_speakers = []
        for zone in all_jobs_full:
            if zone == "All Speakers":
                continue
            if zone.startswith("Custom:"):
                speakers = [s.strip() for s in zone.replace("Custom:", "").split(",")]
                if len(speakers) > 1:
                    composite_zones.append(zone)
            else:
                individual_speakers.append(zone)
        composite_zones = sorted(composite_zones)
        individual_speakers = sorted(individual_speakers)
        
        return render_template(
            "index.html",
            speakers=speakers,
            current_zone=current_zone,
            current_jobs=current_jobs,
            all_jobs=all_jobs,
            composite_zones=composite_zones,
            individual_speakers=individual_speakers
        )
    except Exception as e:
        logger.error(f"Error loading index page: {e}")
        try:
            return render_template(
                "index.html",
                speakers=["All Speakers"],
                current_zone="All Speakers",
                current_jobs=[],
                all_jobs={},
                error="Failed to load application data"
            )
        except Exception as template_error:
            logger.error(f"Error rendering error template: {template_error}")
            return f"<html><body><h1>AirCron Error</h1><p>Failed to load application: {e}</p></body></html>"


@views_bp.route("/zone/<zone_name>")
def zone_view(zone_name: str) -> Any:
    """Get jobs for a specific zone (HTMX partial)."""
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        jobs_objs = jobs_store.get_jobs_for_zone(zone_name)
        jobs = [job.to_dict() for job in jobs_objs]
        
        # Get cron status to determine which jobs are applied
        from . import cronblock
        if cronblock.cron_manager is None:
            cronblock.cron_manager = cronblock.CronManager(app_support_dir)
        
        # Get current cron jobs
        current_lines = cronblock.cron_manager._get_current_crontab()
        current_cron_jobs = set()
        in_aircron_section = False
        
        for line in current_lines:
            line = line.strip()
            if line == cronblock.AIRCRON_BEGIN:
                in_aircron_section = True
            elif line == cronblock.AIRCRON_END:
                in_aircron_section = False
            elif in_aircron_section and line and not line.startswith("#"):
                # Normalize the cron line for comparison
                current_cron_jobs.add(_normalize_cron_line(line))
        
        # Add status to each job
        for job in jobs:
            job_obj = None
            for j in jobs_objs:
                if j.id == job['id']:
                    job_obj = j
                    break
            
            if job_obj:
                cron_line = cronblock.cron_manager._job_to_cron_line(job_obj)
                if cron_line and _normalize_cron_line(cron_line) in current_cron_jobs:
                    job['status'] = 'applied'
                else:
                    job['status'] = 'pending'
            else:
                job['status'] = 'unknown'
        
        # Always aggregate zones for sidebar from all jobs
        all_jobs_full = jobs_store.get_all_jobs()
        composite_zones = []
        individual_speakers = []
        for zone in all_jobs_full:
            if zone == "All Speakers":
                continue
            if zone.startswith("Custom:"):
                speakers = [s.strip() for s in zone.replace("Custom:", "").split(",")]
                if len(speakers) > 1:
                    composite_zones.append(zone)
            else:
                individual_speakers.append(zone)
        composite_zones = sorted(composite_zones)
        individual_speakers = sorted(individual_speakers)
        
        # If ?cron=1, render all_cron_jobs.html for the cron jobs tab
        if request.args.get('cron') == '1':
            zones = {zone_name: jobs}
            total_jobs = len(jobs)
            return render_template(
                "partials/all_cron_jobs.html",
                zones=zones,
                total_jobs=total_jobs,
                composite_zones=composite_zones,
                individual_speakers=individual_speakers
            )
        # Otherwise, render jobs_list.html for the schedule tab
        return render_template(
            "partials/jobs_list.html",
            zone=zone_name,
            jobs=jobs,
            composite_zones=composite_zones,
            individual_speakers=individual_speakers
        )
    except Exception as e:
        logger.error(f"Error loading zone {zone_name}: {e}")
        return f"<div class='text-red-500'>Error loading zone: {e}</div>", 500


@views_bp.route("/modal/add/<zone_name>")
def add_job_modal(zone_name: str) -> Any:
    """Show add job modal (HTMX partial)."""
    # Get all available speakers for multi-select
    speakers = speaker_discovery.get_available_speakers()
    return render_template(
        "partials/job_modal.html",
        zone=zone_name,
        action="add",
        speakers=speakers
    )


@views_bp.route("/modal/edit/<zone_name>/<job_id>")
def edit_job_modal(zone_name: str, job_id: str) -> Any:
    """Show edit job modal (HTMX partial)."""
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        jobs_store = JobsStore(app_support_dir)
        jobs = jobs_store.get_jobs_for_zone(zone_name)
        job = None
        for j in jobs:
            if j.id == job_id:
                job = j
                break
        if not job:
            return "<div class='text-red-500'>Job not found</div>", 404
        # Get all available speakers for multi-select
        speakers = speaker_discovery.get_available_speakers()
        return render_template(
            "partials/job_modal.html",
            zone=zone_name,
            action="edit",
            job=job,
            speakers=speakers
        )
    except Exception as e:
        logger.error(f"Error loading edit modal for job {job_id}: {e}")
        return f"<div class='text-red-500'>Error loading job: {e}</div>", 500


@views_bp.route("/modal/cron/review")
def cron_review_modal() -> Any:
    """Show cron review modal (HTMX partial)."""
    return render_template("partials/cron_review_modal.html")


@views_bp.route("/modal/playlist/add")
def add_playlist_modal() -> Any:
    """Show add playlist modal (HTMX partial)."""
    return render_template(
        "partials/playlist_modal.html",
        action="add"
    )


@views_bp.route("/modal/playlist/edit/<playlist_id>")
def edit_playlist_modal(playlist_id: str) -> Any:
    """Show edit playlist modal (HTMX partial)."""
    try:
        from flask import current_app
        app_support_dir = current_app.config.get("APP_SUPPORT_DIR")
        playlists_file = app_support_dir / "playlists.json"
        
        if not playlists_file.exists():
            return "<div class='text-red-500'>Playlists file not found</div>", 404
        
        with playlists_file.open() as f:
            playlists_data = json.load(f)
        
        playlist = None
        for p in playlists_data["playlists"]:
            if p["id"] == playlist_id:
                playlist = p
                break
        
        if not playlist:
            return "<div class='text-red-500'>Playlist not found</div>", 404
        
        return render_template(
            "partials/playlist_modal.html",
            action="edit",
            playlist=playlist
        )
    except Exception as e:
        logger.error(f"Error loading edit playlist modal: {e}")
        return f"<div class='text-red-500'>Error loading playlist: {e}</div>", 500 