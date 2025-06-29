"""Tests for jobs store functionality."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask

from ..jobs_store import Job, JobsStore


class TestJobsStore(unittest.TestCase):
    """Test cases for JobsStore."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.app = Flask(__name__)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.app.config["APP_SUPPORT_DIR"] = self.temp_dir
        
    def test_job_creation(self) -> None:
        """Test job creation and serialization."""
        job = Job(
            job_id="test123",
            zone="Kitchen",
            days=[1, 2, 3, 4, 5],
            time="07:30",
            action="play",
            args={"uri": "spotify:playlist:123"},
            label="Morning Jazz"
        )
        
        job_dict = job.to_dict()
        self.assertEqual(job_dict["id"], "test123")
        self.assertEqual(job_dict["zone"], "Kitchen")
        self.assertEqual(job_dict["action"], "play")
        self.assertEqual(job_dict["label"], "Morning Jazz")
        
        # Test round-trip
        restored_job = Job.from_dict(job_dict)
        self.assertEqual(restored_job.id, job.id)
        self.assertEqual(restored_job.zone, job.zone)
        self.assertEqual(restored_job.days, job.days)
        self.assertEqual(restored_job.label, job.label)
    
    def test_jobs_store_basic_operations(self) -> None:
        """Test basic CRUD operations."""
        with self.app.app_context():
            store = JobsStore()
            
            # Test adding job
            job = Job("test1", "Kitchen", [1, 2], "08:00", "pause", {}, label="Pause Job")
            store.add_job(job)
            
            # Test getting jobs
            jobs = store.get_jobs_for_zone("Kitchen")
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0].id, "test1")
            
            # Test deleting job
            store.delete_job("Kitchen", "test1")
            jobs = store.get_jobs_for_zone("Kitchen")
            self.assertEqual(len(jobs), 0)
    
    def test_conflict_validation(self) -> None:
        """Test that conflicting jobs are rejected."""
        with self.app.app_context():
            store = JobsStore()
            
            # Add first job
            job1 = Job("test1", "Kitchen", [1, 2], "08:00", "play", {"uri": "test"}, label="Play Job")
            store.add_job(job1)
            
            # Try to add conflicting job (same time, overlapping days)
            job2 = Job("test2", "Kitchen", [2, 3], "08:00", "pause", {}, label="Pause Job 2")
            with self.assertRaises(ValueError):
                store.add_job(job2)


if __name__ == "__main__":
    unittest.main() 