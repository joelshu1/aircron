import logging
from typing import Any, Dict, List

from ..speakers import speaker_discovery

logger = logging.getLogger(__name__)


def list_speakers() -> List[str]:
    logger.info("[speakers_service] Listing speakers")
    return speaker_discovery.get_available_speakers()


def refresh_speakers() -> Dict[str, Any]:
    logger.info("[speakers_service] Refreshing speakers")
    speakers = speaker_discovery.refresh_speakers()
    return {"speakers": speakers, "refreshed": True}
