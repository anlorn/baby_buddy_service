"""Handlers for sleep-related Baby Buddy commands."""

import logging

from .client import BabyBuddyClient

logger = logging.getLogger(__name__)


def sleep_start(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Start a sleep session (start=end=now) tagged with hass, unless one is already in progress."""
    logger.debug("sleep_start: child_id=%d checking for existing unfinished hass sleep", child_id)
    existing = client.find_unfinished("/api/sleep/", child_id, tags=["hass"])
    if existing is not None:
        logger.warning(
            "sleep_start: unfinished hass sleep id=%s already exists for child_id=%d; doing nothing",
            existing["id"],
            child_id,
        )
        return None

    now = client._now()
    logger.debug("sleep_start: no existing unfinished sleep, creating new entry time=%s", now)
    return client._post(
        "/api/sleep/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "tags": ["hass"],
        },
    )


def sleep_finish(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Finish the latest unfinished hass-tagged sleep session, or log a warning if none found."""
    logger.debug("sleep_finish: child_id=%d", child_id)
    entry = client.find_unfinished("/api/sleep/", child_id, tags=["hass"])
    if entry is None:
        logger.warning(
            "sleep_finish: no unfinished hass sleep found for child_id=%d; doing nothing",
            child_id,
        )
        return None

    now = client._now()
    logger.debug("sleep_finish: patching entry id=%s with end=%s", entry["id"], now)
    return client._patch(f"/api/sleep/{entry['id']}/", {"end": now})
