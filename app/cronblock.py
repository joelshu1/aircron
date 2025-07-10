"""Cron block management for AirCron."""

import logging
import re
import shlex
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from croniter import croniter

from .jobs_store import Job, JobsStore

logger = logging.getLogger(__name__)

# Constants
AIRCRON_BEGIN = "# BEGIN AirCron (auto-generated; do not edit between markers)"
AIRCRON_END = "# END AirCron"


class CronManager:
    """Manages cron entries within AirCron markers."""

    def __init__(self, app_support_dir: Optional[Path] = None) -> None:
        self.app_support_dir = app_support_dir
        self._jobs_store: Optional[JobsStore] = None
        self._aircron_script_path: Optional[str] = None

    @property
    def jobs_store(self) -> JobsStore:
        """Get JobsStore instance, creating it if needed."""
        if self._jobs_store is None:
            self._jobs_store = JobsStore(self.app_support_dir)
        return self._jobs_store

    def _get_aircron_script_path(self) -> str:
        """Get path to aircron_run.sh script with robust error handling."""
        if self._aircron_script_path:
            return self._aircron_script_path

        # List of potential locations for aircron_run.sh
        potential_paths = [
            # Current working directory
            Path.cwd() / "aircron_run.sh",
            # Same directory as this module
            Path(__file__).parent.parent / "aircron_run.sh",
            # App support directory
            self.app_support_dir / "aircron_run.sh" if self.app_support_dir else None,
            # System locations
            Path("/usr/local/bin/aircron_run.sh"),
            Path("/usr/bin/aircron_run.sh"),
        ]

        # Filter out None values and check each path
        for path in filter(None, potential_paths):
            if path.exists() and path.is_file():
                # Make sure it's executable
                if not path.stat().st_mode & 0o111:
                    logger.warning(f"Found aircron_run.sh at {path} but it's not executable")
                    continue

                self._aircron_script_path = str(path.absolute())
                logger.info(f"Found aircron_run.sh at: {self._aircron_script_path}")
                return self._aircron_script_path

        # If not found, check if we can create it in current directory
        current_script = Path.cwd() / "aircron_run.sh"
        if current_script.exists():
            self._aircron_script_path = str(current_script.absolute())
            return self._aircron_script_path

        # Last resort: use absolute path assuming it's in the project root
        fallback_path = "/usr/local/bin/aircron_run.sh"
        logger.warning(
            f"aircron_run.sh not found in standard locations, using fallback: {fallback_path}"
        )
        self._aircron_script_path = fallback_path
        return self._aircron_script_path

    def _get_current_crontab(self) -> List[str]:
        """Get current crontab as list of lines."""
        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip().split("\n") if result.stdout.strip() else []
            else:
                logger.warning("No existing crontab found")
                return []
        except subprocess.CalledProcessError:
            logger.warning("No existing crontab found")
            return []
        except Exception as e:
            logger.error(f"Error reading crontab: {e}")
            raise

    def _backup_crontab(self, lines: List[str]) -> None:
        """Create backup of current crontab."""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H%M%S")
            backup_file = Path.home() / f"aircron_backup_{timestamp}.txt"

            backup_file.write_text("\n".join(lines) + "\n" if lines else "")
            logger.info(f"Crontab backed up to: {backup_file}")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            # Don't fail the operation for backup errors

    def _write_crontab(self, lines: List[str]) -> None:
        """Write lines to crontab."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cron", delete=False) as f:
                temp_file = Path(f.name)
                content = "\n".join(lines) + "\n" if lines else ""
                f.write(content)

            # Install new crontab
            result = subprocess.run(
                ["crontab", str(temp_file)], capture_output=True, text=True, timeout=10
            )

            # Clean up temp file
            temp_file.unlink()

            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, "crontab", result.stderr)

            logger.info("Crontab updated successfully")

        except Exception as e:
            logger.error(f"Error writing crontab: {e}")
            raise

    def _generate_cron_lines(self) -> List[str]:
        """Generate cron lines from jobs in store."""
        lines = [AIRCRON_BEGIN, ""]

        # Always create a fresh JobsStore instance to ensure we get latest jobs
        fresh_jobs_store = JobsStore(self.app_support_dir)
        all_jobs = fresh_jobs_store.get_all_jobs()

        # Add logging to debug job count
        total_jobs = sum(len(jobs) for jobs in all_jobs.values())
        logger.info(f"Generating cron lines for {len(all_jobs)} zones with {total_jobs} total jobs")

        for zone, jobs in all_jobs.items():
            if not jobs:
                continue

            logger.info(f"Processing {len(jobs)} jobs for zone: {zone}")
            lines.append(f"# {zone}")
            lines.append("")

            for job in jobs:
                cron_line = self._job_to_cron_line(job)
                if cron_line:
                    lines.extend([f"# {zone} – {job.action.title()} {job.time}", cron_line, ""])
                    logger.info(f"Generated cron line for job {job.id}: {cron_line}")
                else:
                    logger.warning(f"Failed to generate cron line for job {job.id}")

        lines.append(AIRCRON_END)
        logger.info(f"Generated {len(lines)} total cron lines")
        return lines

    def _job_to_cron_line(self, job: Job) -> Optional[str]:
        """Convert job to cron line format."""
        try:
            hour_str, minute_str = job.time.split(":")
            int(hour_str)
            int(minute_str)

            # Convert days (1=Monday, 7=Sunday) to cron format (0=Sunday)
            cron_days = [str(d % 7) for d in job.days]
            days_str = ",".join(sorted(cron_days, key=int))

            aircron_script = self._get_aircron_script_path()
            service = getattr(job, "service", "spotify")
            zone = job.zone
            action = job.action

            # Argument mapping based on action
            arg1 = ""
            arg2 = ""  # Not currently used, but here for future-proofing
            if action == "play":
                if service == "applemusic":
                    arg1 = job.args.get("playlist", "")
                else:  # spotify
                    arg1 = job.args.get("uri", "")
            elif action == "volume":
                arg1 = job.args.get("volume", "50")

            # All other actions (pause, resume, connect, disconnect) have no script arguments.

            cmd_parts = [aircron_script, zone, action, arg1, arg2, service]

            command = " ".join(shlex.quote(str(part)) for part in cmd_parts)
            return f"{minute_str} {hour_str} * * {days_str} {command}"

        except Exception as e:
            logger.error(f"Error converting job {job.id} to cron line: {e}", exc_info=True)
            return None

    def apply_jobs_to_cron(self) -> None:
        """Apply all jobs from store to crontab."""
        try:
            # Get current crontab
            current_lines = self._get_current_crontab()

            # Backup current crontab
            self._backup_crontab(current_lines)

            # Find AirCron section
            begin_idx = None
            end_idx = None

            for i, line in enumerate(current_lines):
                if line.strip() == AIRCRON_BEGIN:
                    begin_idx = i
                elif line.strip() == AIRCRON_END:
                    end_idx = i
                    break

            # Generate new cron lines
            new_cron_lines = self._generate_cron_lines()

            # Build new crontab
            if begin_idx is not None and end_idx is not None:
                # Replace existing AirCron section
                new_lines = (
                    current_lines[:begin_idx] + new_cron_lines + current_lines[end_idx + 1 :]
                )
            else:
                # Add AirCron section to end
                new_lines = current_lines + [""] + new_cron_lines

            # Remove empty lines at start/end
            while new_lines and not new_lines[0].strip():
                new_lines.pop(0)
            while new_lines and not new_lines[-1].strip():
                new_lines.pop()

            # Write new crontab
            self._write_crontab(new_lines)

            logger.info("Successfully applied jobs to crontab")

        except Exception as e:
            logger.error(f"Error applying jobs to cron: {e}")
            raise

    def validate_cron_syntax(self, time: str, days: List[int]) -> bool:
        """Validate cron syntax for given time and days."""
        try:
            hour_str, minute_str = time.split(":")
            hour = int(hour_str)
            minute = int(minute_str)

            # Convert days to cron format
            cron_days = []
            for day in days:
                if day == 7:  # Sunday
                    cron_days.append("0")
                else:
                    cron_days.append(str(day))

            days_str = ",".join(sorted(cron_days, key=lambda x: int(x)))

            # Test with croniter
            croniter(f"{minute} {hour} * * {days_str}")
            return True

        except Exception as e:
            logger.error(f"Invalid cron syntax: {e}")
            return False

    def get_cron_section_from_crontab(self) -> List[str]:
        """Get the AirCron section from the current crontab."""
        current_lines = self._get_current_crontab()
        aircron_lines = []
        in_aircron_section = False

        for line in current_lines:
            if line.strip() == AIRCRON_BEGIN:
                in_aircron_section = True
                aircron_lines.append(line)
            elif line.strip() == AIRCRON_END:
                aircron_lines.append(line)
                break
            elif in_aircron_section:
                aircron_lines.append(line)

        return aircron_lines


# Global instance - will be initialized when Flask app is created
cron_manager: Optional[CronManager] = None


def _normalize_cron_line(line: str) -> str:
    """Normalize a cron line for comparison (strip, collapse whitespace, remove quotes)."""
    line = line.strip()
    line = re.sub(r"\s+", " ", line)
    line = line.replace('"', "").replace("'", "")
    return line
