"""Handlers for tummy-time Baby Buddy commands."""

import logging

from .client import BabyBuddyClient

logger = logging.getLogger(__name__)


def tummy_time_start(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Start a tummy-time session (start=end=now) tagged with hass, unless one is already in progress."""
    logger.debug("tummy_time_start: child_id=%d checking for existing unfinished hass tummy time", child_id)
    existing = client.find_unfinished("/api/tummy-times/", child_id, tags=["hass"])
    if existing is not None:
        logger.warning(
            "tummy_time_start: unfinished hass tummy time id=%s already exists for child_id=%d; doing nothing",
            existing["id"],
            child_id,
        )
        return None

    now = client._now()
    logger.debug("tummy_time_start: no existing unfinished entry, creating new time=%s", now)
    return client._post(
        "/api/tummy-times/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "tags": ["hass"],
        },
    )


def tummy_time_finish(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Finish the latest unfinished hass-tagged tummy-time session, or warn if none found."""
    logger.debug("tummy_time_finish: child_id=%d", child_id)
    entry = client.find_unfinished("/api/tummy-times/", child_id, tags=["hass"])
    if entry is None:
        logger.warning(
            "tummy_time_finish: no unfinished hass tummy time found for child_id=%d; doing nothing",
            child_id,
        )
        return None

    now = client._now()
    logger.debug("tummy_time_finish: patching entry id=%s with end=%s", entry["id"], now)
    return client._patch(f"/api/tummy-times/{entry['id']}/", {"end": now})
