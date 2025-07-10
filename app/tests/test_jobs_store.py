"""Tests for jobs store functionality."""

import tempfile
import unittest
from pathlib import Path

from flask import Flask

from app import cronblock

from ..jobs_store import Job, JobsStore


class TestJobsStore(unittest.TestCase):
    """Test cases for JobsStore."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.app.config["APP_SUPPORT_DIR"] = self.temp_dir

    def test_job_creation(self) -> None:
        """Test job creation and serialization, including service field."""
        job = Job(
            job_id="test123",
            zone="Kitchen",
            days=[1, 2, 3, 4, 5],
            time="07:30",
            action="play",
            args={"uri": "spotify:playlist:123"},
            label="Morning Jazz",
            service="spotify",
        )
        job_dict = job.to_dict()
        self.assertEqual(job_dict["id"], "test123")
        self.assertEqual(job_dict["zone"], "Kitchen")
        self.assertEqual(job_dict["action"], "play")
        self.assertEqual(job_dict["label"], "Morning Jazz")
        self.assertEqual(job_dict["service"], "spotify")
        # Test Apple Music job
        am_job = Job(
            job_id="am1",
            zone="Living Room",
            days=[1],
            time="09:00",
            action="play",
            args={"playlist": "Chill Mix"},
            label="Apple Music Job",
            service="applemusic",
        )
        am_dict = am_job.to_dict()
        self.assertEqual(am_dict["service"], "applemusic")
        # Test round-trip
        restored_job = Job.from_dict(job_dict)
        self.assertEqual(restored_job.id, job.id)
        self.assertEqual(restored_job.zone, job.zone)
        self.assertEqual(restored_job.days, job.days)
        self.assertEqual(restored_job.label, job.label)
        self.assertEqual(restored_job.service, job.service)
        # Test migration of legacy job dict (no service field)
        legacy = job_dict.copy()
        legacy.pop("service")
        migrated = Job.from_dict(legacy)
        self.assertEqual(migrated.service, "spotify")

    def test_jobs_store_basic_operations(self) -> None:
        """Test basic CRUD operations for both services."""
        with self.app.app_context():
            store = JobsStore()
            # Spotify job
            job = Job(
                "test1",
                "Kitchen",
                [1, 2],
                "08:00",
                "pause",
                {},
                label="Pause Job",
                service="spotify",
            )
            store.add_job(job)
            # Apple Music job
            am_job = Job(
                "am2",
                "Living Room",
                [3],
                "10:00",
                "play",
                {"playlist": "AM Mix"},
                label="AM Play",
                service="applemusic",
            )
            store.add_job(am_job)
            # Test getting jobs
            jobs = store.get_jobs_for_zone("Kitchen")
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].service, "spotify")
            am_jobs = store.get_jobs_for_zone("Living Room")
            self.assertEqual(len(am_jobs), 1)
            self.assertEqual(am_jobs[0].service, "applemusic")
            # Test deleting jobs
            store.delete_job("Kitchen", "test1")
            store.delete_job("Living Room", "am2")
            self.assertEqual(len(store.get_jobs_for_zone("Kitchen")), 0)
            self.assertEqual(len(store.get_jobs_for_zone("Living Room")), 0)

    def test_conflict_validation(self) -> None:
        """Test that conflicting jobs are rejected, regardless of service."""
        with self.app.app_context():
            store = JobsStore()
            # Add first job
            job1 = Job(
                "test1",
                "Kitchen",
                [1, 2],
                "08:00",
                "play",
                {"uri": "test"},
                label="Play Job",
                service="spotify",
            )
            store.add_job(job1)
            # Try to add conflicting job (same time, overlapping days, different service)
            job2 = Job(
                "test2",
                "Kitchen",
                [2, 3],
                "08:00",
                "pause",
                {},
                label="Pause Job 2",
                service="applemusic",
            )
            with self.assertRaises(ValueError):
                store.add_job(job2)

    def test_invalid_service(self) -> None:
        """Test that invalid service values are handled."""
        # Should default to spotify if missing
        d = {
            "id": "x",
            "zone": "z",
            "days": [1],
            "time": "00:00",
            "action": "pause",
            "args": {},
            "label": "",
        }
        job = Job.from_dict(d)
        self.assertEqual(job.service, "spotify")
        # Should accept only 'spotify' or 'applemusic'
        d2 = d.copy()
        d2["service"] = "notarealservice"
        job2 = Job.from_dict(d2)
        self.assertEqual(job2.service, "notarealservice")  # Model doesn't validate, but API should


class TestCronLineGeneration(unittest.TestCase):
    def setUp(self) -> None:
        self.cron_manager = cronblock.CronManager()

    def test_spotify_cron_line(self) -> None:
        job = Job(
            job_id="test1",
            zone="Kitchen",
            days=[1, 2],
            time="08:00",
            action="play",
            args={"uri": "spotify:playlist:123"},
            label="Test",
            service="spotify",
        )
        line = self.cron_manager._job_to_cron_line(job)
        self.assertIsNotNone(line)
        assert line is not None  # For mypy
        self.assertIn("aircron_run.sh", line)
        self.assertIn("play", line)
        self.assertIn("spotify:playlist:123", line)
        self.assertNotIn("applemusic", line)

    def test_applemusic_cron_line(self) -> None:
        job = Job(
            job_id="am1",
            zone="Living Room",
            days=[3],
            time="09:30",
            action="play",
            args={"playlist": "Chill Mix"},
            label="AM",
            service="applemusic",
        )
        line = self.cron_manager._job_to_cron_line(job)
        self.assertIsNotNone(line)
        assert line is not None  # For mypy
        self.assertIn("aircron_run.sh", line)
        self.assertIn("play", line)
        self.assertIn("Chill Mix", line)
        self.assertIn("applemusic", line)


if __name__ == "__main__":
    unittest.main()
