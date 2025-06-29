"""Airfoil speaker discovery via AppleScript."""

import logging
import subprocess
from typing import List

logger = logging.getLogger(__name__)


class SpeakerDiscovery:
    """Handles discovery of connected Airfoil speakers."""
    
    def __init__(self) -> None:
        self.last_speakers: List[str] = []
    
    def get_available_speakers(self) -> List[str]:
        """Get list of all available speakers from Airfoil via AppleScript."""
        applescript = '''
        tell application "Airfoil"
            try
                set allSpeakers to (name of every speaker)
                return allSpeakers
            on error
                return {}
            end try
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse AppleScript list output: "{item1, item2, item3}"
                output = result.stdout.strip()
                if output and output != "{}":
                    # Remove braces and split by comma
                    speakers_str = output.strip("{}")
                    if speakers_str:
                        speakers = [s.strip() for s in speakers_str.split(",")]
                        # Always include "All Speakers" as first option
                        all_speakers = ["All Speakers"] + speakers
                        self.last_speakers = all_speakers
                        logger.info(f"Found {len(speakers)} available speakers")
                        return all_speakers
                
                # No speakers found
                self.last_speakers = ["All Speakers"]
                logger.warning("No available speakers found")
                return ["All Speakers"]
            
            else:
                logger.error(f"AppleScript error: {result.stderr}")
                # Return cached speakers if available
                if self.last_speakers:
                    logger.info("Using cached speaker list due to AppleScript error")
                    return self.last_speakers
                return ["All Speakers"]
                
        except subprocess.TimeoutExpired:
            logger.error("AppleScript timeout")
            return self.last_speakers or ["All Speakers"]
        except Exception as e:
            logger.error(f"Error getting speakers: {e}")
            return self.last_speakers or ["All Speakers"]
    
    def is_airfoil_running(self) -> bool:
        """Check if Airfoil application is running."""
        applescript = '''
        tell application "System Events"
            return (name of processes) contains "Airfoil"
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and "true" in result.stdout.lower()
        except Exception as e:
            logger.error(f"Error checking Airfoil status: {e}")
            return False
    
    def refresh_speakers(self) -> List[str]:
        """Force refresh of speaker list."""
        logger.info("Refreshing speaker list")
        if not self.is_airfoil_running():
            logger.warning("Airfoil is not running")
            # Still try to get speakers in case it starts
        
        return self.get_available_speakers()
    
    def get_connected_speakers(self) -> List[str]:
        """Get list of currently connected speakers from Airfoil via AppleScript."""
        applescript = '''
        tell application "Airfoil"
            try
                set connectedSpeakers to (name of speakers whose connected is true)
                return connectedSpeakers
            on error
                return {}
            end try
        end tell
        '''
        
        try:
            result = subprocess.run(
                ["osascript", "-e", applescript],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Parse AppleScript list output: "{item1, item2, item3}"
                output = result.stdout.strip()
                if output and output != "{}":
                    # Remove braces and split by comma
                    speakers_str = output.strip("{}")
                    if speakers_str:
                        speakers = [s.strip() for s in speakers_str.split(",")]
                        logger.info(f"Found {len(speakers)} connected speakers")
                        return speakers
                
                # No speakers found
                logger.warning("No connected speakers found")
                return []
            
            else:
                logger.error(f"AppleScript error: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logger.error("AppleScript timeout")
            return []
        except Exception as e:
            logger.error(f"Error getting connected speakers: {e}")
            return []


# Global instance
speaker_discovery = SpeakerDiscovery() 