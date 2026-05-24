"""HTTP client for the Baby Buddy API with child ID caching and unfinished-activity lookup."""

import logging
from datetime import datetime, timezone

import requests

logger = logging.getLogger(__name__)


class BabyBuddyClient:
    """Wraps the Baby Buddy REST API with a persistent session and child-ID cache."""

    def __init__(self, host: str, api_key: str) -> None:
        """Initialise session with auth headers and empty child cache."""
        self._host = host.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Token {api_key}",
                "Content-Type": "application/json",
            }
        )
        self._child_cache: dict[str, int] = {}
        logger.debug("BabyBuddyClient initialised for host %s", self._host)

    def resolve_child(self, name: str) -> int:
        """Return the Baby Buddy child ID for *name*, using cache when available."""
        if name in self._child_cache:
            logger.debug("Child '%s' resolved from cache: id=%d", name, self._child_cache[name])
            return self._child_cache[name]

        logger.debug("Looking up child '%s' via API", name)
        data = self._get("/api/children/", params={"first_name": name})
        results = data.get("results", [])
        if not results:
            raise ValueError(f"No child found with first_name='{name}'")

        child_id: int = results[0]["id"]
        self._child_cache[name] = child_id
        logger.debug("Child '%s' resolved: id=%d (cached)", name, child_id)
        return child_id

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Perform a GET request and raise HTTPError on non-2xx."""
        url = self._host + path
        logger.debug("GET %s params=%s", url, params)
        response = self._session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        logger.debug("GET %s -> %s", url, data)
        return data

    def _post(self, path: str, data: dict) -> dict:
        """Perform a POST request with JSON body and raise HTTPError on non-2xx."""
        url = self._host + path
        logger.debug("POST %s body=%s", url, data)
        response = self._session.post(url, json=data)
        response.raise_for_status()
        result = response.json()
        logger.debug("POST %s -> %s", url, result)
        return result

    def _patch(self, path: str, data: dict) -> dict:
        """Perform a PATCH request with JSON body and raise HTTPError on non-2xx."""
        url = self._host + path
        logger.debug("PATCH %s body=%s", url, data)
        response = self._session.patch(url, json=data)
        response.raise_for_status()
        result = response.json()
        logger.debug("PATCH %s -> %s", url, result)
        return result

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        """Return the current UTC time as an ISO-8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def find_unfinished(self, endpoint: str, child_id: int, tags: list[str] | None = None) -> dict | None:
        """Return the latest in-progress entry for *child_id* at *endpoint*, or None.

        An entry is considered in-progress when its ``start`` equals its ``end``
        (the sentinel value Baby Buddy uses for activities that haven't ended yet).
        Optionally filter by tag slugs via *tags*.
        """
        logger.debug("find_unfinished: endpoint=%s child_id=%d tags=%s", endpoint, child_id, tags)
        params: dict = {"limit": 1, "ordering": "-start", "child": child_id}
        if tags:
            params["tags"] = ",".join(tags)
        data = self._get(endpoint, params=params)
        results = data.get("results", [])
        if not results:
            logger.debug("find_unfinished: no entries found")
            return None

        entry = results[0]
        start = entry.get("start")
        end = entry.get("end")
        logger.debug("find_unfinished: latest entry id=%s start=%s end=%s", entry.get("id"), start, end)

        if start is None or end is None:
            logger.debug("find_unfinished: entry missing start/end fields")
            return None

        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            logger.warning("find_unfinished: could not parse start/end datetimes: %s / %s", start, end)
            return None

        if start_dt == end_dt:
            logger.debug("find_unfinished: entry id=%s is in-progress", entry.get("id"))
            return entry

        logger.debug("find_unfinished: entry id=%s already finished", entry.get("id"))
        return None

    def find_latest(
        self,
        endpoint: str,
        child_id: int,
        filters: dict | None = None,
    ) -> dict | None:
        """Return the most recent entry for *child_id* at *endpoint*, regardless of state.

        Unlike :meth:`find_unfinished`, this does not require ``start == end`` —
        it returns whatever entry sorts first by ``-start`` matching the optional
        *filters* (e.g. ``{"method": "bottle"}``).
        """
        logger.debug("find_latest: endpoint=%s child_id=%d filters=%s", endpoint, child_id, filters)
        params: dict = {"limit": 1, "ordering": "-start", "child": child_id}
        if filters:
            params.update(filters)
        data = self._get(endpoint, params=params)
        results = data.get("results", [])
        if not results:
            logger.debug("find_latest: no entries found")
            return None
        entry = results[0]
        logger.debug("find_latest: entry id=%s", entry.get("id"))
        return entry

    def append_notes(self, endpoint: str, entry_id: int, text: str) -> dict:
        """PATCH *entry_id* at *endpoint*, appending *text* to its ``notes`` field.

        Separator is ``"; "``. If the existing ``notes`` is empty or ``None``,
        the new value is just *text* (no leading separator).
        """
        logger.debug("append_notes: endpoint=%s id=%s text=%r", endpoint, entry_id, text)
        existing = self._get(f"{endpoint}{entry_id}/")
        prior = existing.get("notes") or ""
        new_notes = f"{prior}; {text}" if prior else text
        logger.debug("append_notes: prior=%r -> new=%r", prior, new_notes)
        return self._patch(f"{endpoint}{entry_id}/", {"notes": new_notes})
