"""Handlers for diaper-change Baby Buddy commands."""

import logging

from .client import BabyBuddyClient

logger = logging.getLogger(__name__)


def diaper_change_wet_solid(client: BabyBuddyClient, child_id: int) -> dict:
    """Record a wet+solid diaper change tagged with hass."""
    now = client._now()
    logger.debug("diaper_change_wet_solid: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/changes/",
        {
            "child": child_id,
            "time": now,
            "wet": True,
            "solid": True,
            "tags": ["hass"],
        },
    )


def diaper_change_solid(client: BabyBuddyClient, child_id: int) -> dict:
    """Record a solid-only diaper change tagged with hass."""
    now = client._now()
    logger.debug("diaper_change_solid: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/changes/",
        {
            "child": child_id,
            "time": now,
            "wet": False,
            "solid": True,
            "tags": ["hass"],
        },
    )
