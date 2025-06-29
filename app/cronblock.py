"""Cron block management for AirCron."""

import logging
import shutil
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
        self._jobs_store = None
        self._aircron_script_path = None
    
    @property
    def jobs_store(self) -> JobsStore:
        """Get JobsStore instance, creating it if needed."""
        if self._jobs_store is None:
            self._jobs_store = JobsStore(self.app_support_dir)
        return self._jobs_store
    
    def _get_aircron_script_path(self) -> str:
        """Get the path to aircron_run.sh script."""
        if self._aircron_script_path is None:
            # Look for aircron_run.sh in common locations
            script_locations = [
                Path.cwd() / "aircron_run.sh",  # Current directory
                Path("/usr/local/bin/aircron_run.sh"),
                Path("/opt/homebrew/bin/aircron_run.sh"),
            ]
            
            for script_path in script_locations:
                if script_path.is_file():
                    self._aircron_script_path = str(script_path)
                    logger.info(f"Found aircron_run.sh at: {script_path}")
                    break
            
            if self._aircron_script_path is None:
                # Fallback to current directory
                self._aircron_script_path = str(Path.cwd() / "aircron_run.sh")
                logger.warning(f"aircron_run.sh not found, using: {self._aircron_script_path}")
        
        return self._aircron_script_path
    
    def _get_current_crontab(self) -> List[str]:
        """Get current crontab as list of lines."""
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n') if result.stdout.strip() else []
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
            
            backup_file.write_text('\n'.join(lines) + '\n' if lines else '')
            logger.info(f"Crontab backed up to: {backup_file}")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            # Don't fail the operation for backup errors
    
    def _write_crontab(self, lines: List[str]) -> None:
        """Write lines to crontab."""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cron', delete=False) as f:
                temp_file = Path(f.name)
                content = '\n'.join(lines) + '\n' if lines else ''
                f.write(content)
            
            # Install new crontab
            result = subprocess.run(
                ["crontab", str(temp_file)],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Clean up temp file
            temp_file.unlink()
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(
                    result.returncode, 
                    "crontab", 
                    result.stderr
                )
            
            logger.info("Crontab updated successfully")
            
        except Exception as e:
            logger.error(f"Error writing crontab: {e}")
            raise
    
    def _generate_cron_lines(self) -> List[str]:
        """Generate cron lines from jobs in store."""
        lines = [AIRCRON_BEGIN, ""]
        
        all_jobs = self.jobs_store.get_all_jobs()
        
        for zone, jobs in all_jobs.items():
            if not jobs:
                continue
                
            lines.append(f"# {zone}")
            lines.append("")
            
            for job in jobs:
                cron_line = self._job_to_cron_line(job)
                if cron_line:
                    lines.extend([
                        f"# {zone} – {job.action.title()} {job.time}",
                        cron_line,
                        ""
                    ])
        
        lines.append(AIRCRON_END)
        return lines
    
    def _job_to_cron_line(self, job: Job) -> Optional[str]:
        """Convert job to cron line format."""
        try:
            # Parse time
            hour, minute = job.time.split(':')
            hour = int(hour)
            minute = int(minute)
            
            # Convert days (1=Monday, 7=Sunday) to cron format (0=Sunday, 1=Monday...6=Saturday)
            cron_days = []
            for day in job.days:
                if day == 7:  # Sunday in our format = 0 in cron
                    cron_days.append("0")
                else:  # Monday=1 in our format = 1 in cron, etc.
                    cron_days.append(str(day))
            
            days_str = ",".join(sorted(cron_days, key=lambda x: int(x)))
            
            # Build command based on action
            aircron_script = self._get_aircron_script_path()
            
            if job.action == "play":
                uri = job.args.get("uri", "")
                cmd_parts = [
                    aircron_script,
                    f'"{job.zone}"',
                    "play",
                    f'"{uri}"'
                ]
            elif job.action == "pause":
                cmd_parts = [
                    aircron_script,
                    f'"{job.zone}"',
                    "pause"
                ]
            elif job.action == "resume":
                cmd_parts = [
                    aircron_script,
                    f'"{job.zone}"',
                    "resume"
                ]
            elif job.action == "volume":
                volume = job.args.get("volume", "50")
                cmd_parts = [
                    aircron_script,
                    f'"{job.zone}"',
                    "volume",
                    str(volume)
                ]
            else:
                logger.warning(f"Unknown action: {job.action}")
                return None
            
            cmd = " ".join(cmd_parts)
            
            # Build cron line: minute hour day month weekday command
            cron_line = f"{minute} {hour} * * {days_str} {cmd}"
            
            # Validate cron syntax
            try:
                croniter(f"{minute} {hour} * * {days_str}")
            except ValueError as e:
                logger.error(f"Invalid cron syntax for job {job.id}: {e}")
                return None
            
            return cron_line
            
        except Exception as e:
            logger.error(f"Error converting job {job.id} to cron line: {e}")
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
                    current_lines[:begin_idx] + 
                    new_cron_lines + 
                    current_lines[end_idx + 1:]
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
            hour, minute = time.split(':')
            hour = int(hour)
            minute = int(minute)
            
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


# Global instance - will be initialized when Flask app is created
cron_manager: Optional[CronManager] = None 