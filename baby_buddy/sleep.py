"""Handlers for sleep-related Baby Buddy commands."""

import logging

from .client import BabyBuddyClient

logger = logging.getLogger(__name__)


def sleep_start(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a sleep session (start=end=now) tagged with hass."""
    now = client._now()
    logger.debug("sleep_start: child_id=%d time=%s", child_id, now)
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
    """Finish the latest unfinished sleep session, or log a warning if none found."""
    logger.debug("sleep_finish: child_id=%d", child_id)
    entry = client.find_unfinished("/api/sleep/", child_id)
    if entry is None:
        logger.warning(
            "sleep_finish: no unfinished sleep found for child_id=%d; doing nothing",
            child_id,
        )
        return None

    now = client._now()
    logger.debug("sleep_finish: patching entry id=%s with end=%s", entry["id"], now)
    return client._patch(f"/api/sleep/{entry['id']}/", {"end": now})
