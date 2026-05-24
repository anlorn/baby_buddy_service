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


def feeding_start_both_breasts(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a both-breasts feeding session (start=end=now)."""
    now = client._now()
    logger.debug("feeding_start_both_breasts: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/feedings/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "type": "breast milk",
            "method": "both breasts",
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


def _note_on_latest_if_compatible(
    client: BabyBuddyClient,
    child_id: int,
    text: str,
    allowed_methods: set[str],
    label: str,
) -> dict | None:
    """Append *text* to the latest feeding's notes only if its method is in *allowed_methods*.

    Looks at the latest feeding regardless of in-progress/finished state. If no feeding
    exists or its method is not compatible (e.g. Vitamin D on a breast feed, Left/Right
    on a bottle), logs a warning and returns ``None`` — never errors.
    """
    logger.debug("%s: child_id=%d allowed_methods=%s", label, child_id, sorted(allowed_methods))
    entry = client.find_latest("/api/feedings/", child_id)
    if entry is None:
        logger.warning("%s: no feeding found for child_id=%d; doing nothing", label, child_id)
        return None
    method = entry.get("method")
    if method not in allowed_methods:
        logger.warning(
            "%s: latest feeding id=%s has method=%r, not in %s; doing nothing",
            label, entry["id"], method, sorted(allowed_methods),
        )
        return None
    return client.append_notes("/api/feedings/", entry["id"], text)


_BREAST_METHODS = {"left breast", "right breast", "both breasts"}


def feeding_note_left(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Append 'Left breast' to the latest feeding's notes if it's a breast feed."""
    return _note_on_latest_if_compatible(
        client, child_id, "Left breast", _BREAST_METHODS, "feeding_note_left",
    )


def feeding_note_right(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Append 'Right breast' to the latest feeding's notes if it's a breast feed."""
    return _note_on_latest_if_compatible(
        client, child_id, "Right breast", _BREAST_METHODS, "feeding_note_right",
    )


def feeding_note_vitamin_d(client: BabyBuddyClient, child_id: int) -> dict | None:
    """Append 'Vitamin D' to the latest feeding's notes if it's a bottle feed."""
    return _note_on_latest_if_compatible(
        client, child_id, "Vitamin D", {"bottle"}, "feeding_note_vitamin_d",
    )
