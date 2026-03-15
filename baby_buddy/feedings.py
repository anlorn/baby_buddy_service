"""Handlers for feeding-related Baby Buddy commands."""

import logging

from .client import BabyBuddyClient

logger = logging.getLogger(__name__)


def feeding_left_breast(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a left-breast feeding session (start=end=now)."""
    now = client._now()
    logger.debug("feeding_left_breast: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/feedings/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "type": "breast milk",
            "method": "left breast",
            "tags": ["hass"],
        },
    )


def feeding_right_breast(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a right-breast feeding session (start=end=now)."""
    now = client._now()
    logger.debug("feeding_right_breast: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/feedings/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "type": "breast milk",
            "method": "right breast",
            "tags": ["hass"],
        },
    )


def feeding_bottle_breast_milk(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a bottle (breast milk) feeding session (start=end=now)."""
    now = client._now()
    logger.debug("feeding_bottle_breast_milk: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/feedings/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "type": "breast milk",
            "method": "bottle",
            "tags": ["hass"],
        },
    )


def feeding_bottle_formula(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a bottle (formula) feeding session (start=end=now)."""
    now = client._now()
    logger.debug("feeding_bottle_formula: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/feedings/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "type": "formula",
            "method": "bottle",
            "tags": ["hass"],
        },
    )


def feeding_finish_last(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Finish the latest unfinished feeding for the child, or log a warning if none found."""
    logger.debug("feeding_finish_last: child_id=%d", child_id)
    entry = client.find_unfinished("/api/feedings/", child_id)
    if entry is None:
        logger.warning(
            "feeding_finish_last: no unfinished feeding found for child_id=%d; doing nothing",
            child_id,
        )
        return None

    now = client._now()
    logger.debug("feeding_finish_last: patching entry id=%s with end=%s", entry["id"], now)
    return client._patch(f"/api/feedings/{entry['id']}/", {"end": now})
