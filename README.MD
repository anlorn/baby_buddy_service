# Baby Buddy HTTP Command Service

A lightweight Python HTTP service that translates simple named commands (sent via POST requests from Node-RED, Zigbee button automations, or any HTTP client) into Baby Buddy REST API calls. The service owns all Baby Buddy authentication and business logic so that upstream automations remain dumb — they send a command name and a child's first name, nothing else.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Configuration](#configuration)
- [Running the Service](#running-the-service)
  - [Docker (recommended)](#docker-recommended)
  - [Without Docker](#without-docker)
- [API](#api)
- [Commands](#commands)
  - [Feedings](#feedings)
  - [Diaper Changes](#diaper-changes)
  - [Sleep](#sleep)
- [Error Responses](#error-responses)
- [Code Structure](#code-structure)
  - [File Responsibilities](#file-responsibilities)
  - [Key Internals](#key-internals)
- [Adding a New Command](#adding-a-new-command)
- [Adding a New Activity Type](#adding-a-new-activity-type)

---

## Overview

[Baby Buddy](https://github.com/babybuddy/babybuddy) is a self-hosted infant care tracker. This service sits between Baby Buddy and physical/automated triggers (e.g. a Zigbee button pressed via Node-RED) and abstracts the Baby Buddy API into simple, named commands.

```
[Zigbee button] → [Node-RED] → POST /command {"command":"sleep_start","child":"Alice"}
                                       ↓
                          Baby Buddy Command Service
                                       ↓
                          Baby Buddy REST API (authenticated)
```

Responsibilities of this service:
- Hold the Baby Buddy API key (not exposed to Node-RED or button firmware)
- Translate command names to the correct Baby Buddy API endpoint + payload
- Implement the "start/finish" pattern: a "start" command creates an entry with `start=end=now` as an in-progress sentinel; a "finish" command finds that entry and patches `end=now`
- Cache child IDs per process lifetime to avoid repeated lookups
- Tag every created activity with `hass` for easy filtering in Baby Buddy

---

## How It Works

### Start / Finish pattern

Baby Buddy does not have a concept of a "pending" activity. This service uses the convention that an activity with `start == end` is in-progress. When a "start" command is received, the entry is created with `start=end=<current UTC time>`. When the corresponding "finish" command arrives, the service fetches the most recent entry of that type for the child, verifies `start == end`, then PATCHes `end=<current UTC time>`.

If a "finish" command arrives but no in-progress entry exists (already finished or never started), the service logs a warning and returns `{"ok": true, "result": null}` — it does not error, since a double-press or missed start is a normal operational condition.

### Child resolution

The child is identified by `first_name` in every request. On first use, the service looks up the child via `GET /api/children/?first_name=<name>` and caches the numeric ID for the remainder of the process lifetime. If no child matches, the service returns HTTP 404.

### Tagging

All activities created by this service are tagged with the slug `hass`. Baby Buddy automatically creates tags on first use — no tag pre-creation is required.

---

## Configuration

All configuration is via environment variables. The service **fails immediately at startup** if required variables are missing.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BB_HOST` | Yes | — | Base URL of the Baby Buddy instance, e.g. `http://192.168.1.10:8000`. No trailing slash. |
| `BB_KEY` | Yes | — | Baby Buddy API token. Find it in Baby Buddy under **Settings → API**. |
| `PORT` | No | `8080` | TCP port the service listens on. |

---

## Running the Service

### Docker (recommended)

**Build:**

```bash
docker build -t baby-buddy-service .
```

**Run:**

```bash
docker run -d \
  -e BB_HOST=http://192.168.1.10:8000 \
  -e BB_KEY=<your_api_token> \
  -p 8080:8080 \
  baby-buddy-service
```

With a custom port:

```bash
docker run -d \
  -e BB_HOST=http://192.168.1.10:8000 \
  -e BB_KEY=<your_api_token> \
  -e PORT=9090 \
  -p 9090:9090 \
  baby-buddy-service
```

### Without Docker

Python 3.10+ is required (uses `dict | None` union syntax).

Create and activate a virtual environment, then install dependencies:

```bash
cd baby_buddy_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Start:**

```bash
BB_HOST=http://192.168.1.10:8000 BB_KEY=<your_api_token> python app.py
```

With a custom port:

```bash
BB_HOST=http://192.168.1.10:8000 BB_KEY=<your_api_token> PORT=9090 python app.py
```

The service binds to `0.0.0.0` on the configured port and logs at DEBUG level to stdout. There is no authentication on the service itself — it is designed for deployment on a trusted internal network.

---

## API

### `POST /command`

**Request body** (JSON):

```json
{
  "command": "<command_name>",
  "child": "<first_name>"
}
```

Both fields are required. `child` is matched against the `first_name` field in Baby Buddy (case-sensitive).

**Success response** — HTTP 200:

```json
{
  "ok": true,
  "result": { ... }
}
```

`result` is the raw Baby Buddy API response object, or `null` when a "finish" command found no in-progress activity to close.

**Error responses** — see [Error Responses](#error-responses).

---

## Commands

### Feedings

#### `feeding_left_breast`

Records the start of a left-breast feeding session.

- Endpoint: `POST /api/feedings/`
- Fields: `type=breast milk`, `method=left breast`, `start=end=now`, `tags=["hass"]`

#### `feeding_right_breast`

Records the start of a right-breast feeding session.

- Endpoint: `POST /api/feedings/`
- Fields: `type=breast milk`, `method=right breast`, `start=end=now`, `tags=["hass"]`

#### `feeding_bottle_breast_milk`

Records the start of a bottle feeding using expressed breast milk.

- Endpoint: `POST /api/feedings/`
- Fields: `type=breast milk`, `method=bottle`, `start=end=now`, `tags=["hass"]`

#### `feeding_bottle_formula`

Records the start of a bottle feeding using formula.

- Endpoint: `POST /api/feedings/`
- Fields: `type=formula`, `method=bottle`, `start=end=now`, `tags=["hass"]`

#### `feeding_finish_last`

Closes the most recent unfinished feeding for the child by setting its end time to now. If no unfinished feeding exists, logs a warning and returns `null` result without error.

- Lookup: `GET /api/feedings/?limit=1&ordering=-start&child=<id>`
- Condition: entry is patched only if `start == end`
- Endpoint: `PATCH /api/feedings/<id>/`
- Fields: `end=now`

---

### Diaper Changes

Diaper changes are single-timestamp events — there is no start/finish pattern.

#### `diaper_change_wet_solid`

Records a diaper change that was both wet and solid.

- Endpoint: `POST /api/changes/`
- Fields: `wet=true`, `solid=true`, `time=now`, `tags=["hass"]`

#### `diaper_change_solid`

Records a diaper change that was solid only (not wet).

- Endpoint: `POST /api/changes/`
- Fields: `wet=false`, `solid=true`, `time=now`, `tags=["hass"]`

---

### Sleep

#### `sleep_start`

Records the start of a sleep session.

- Endpoint: `POST /api/sleep/`
- Fields: `start=end=now`, `tags=["hass"]`

#### `sleep_finish`

Closes the most recent unfinished sleep session by setting its end time to now. If no unfinished session exists, logs a warning and returns `null` result without error.

- Lookup: `GET /api/sleep/?limit=1&ordering=-start&child=<id>`
- Condition: entry is patched only if `start == end`
- Endpoint: `PATCH /api/sleep/<id>/`
- Fields: `end=now`

---

## Error Responses

| HTTP Status | Cause | Response body |
|-------------|-------|---------------|
| 400 | `command` or `child` field missing from request body | `{"error": "Both 'command' and 'child' are required"}` |
| 400 | `command` value not in the registered command list | `{"error": "Unknown command: '<name>'"}` |
| 404 | No Baby Buddy child found with the given `first_name` | `{"error": "No child found with first_name='<name>'"}` |
| 500 | Unexpected error (e.g. Baby Buddy unreachable, non-2xx from API) | `{"error": "Internal server error", "detail": "<exception message>"}` |

---

## Code Structure

```
baby_buddy_service/
├── app.py                    # Flask application entry point
├── requirements.txt          # Python dependencies
└── baby_buddy/
    ├── __init__.py           # Package entry point, exports BabyBuddyClient
    ├── client.py             # HTTP client, child cache, unfinished-activity lookup
    ├── feedings.py           # Feeding command handlers
    ├── sleep.py              # Sleep command handlers
    ├── changes.py            # Diaper change command handlers
    └── registry.py           # Master command → function dispatch table
```

### File Responsibilities

#### `app.py`

The Flask application. Responsibilities:

- Reads and validates environment variables (`BB_HOST`, `BB_KEY`, `PORT`) at import time — raises `RuntimeError` immediately if required vars are missing.
- Instantiates the single global `BabyBuddyClient`.
- Exposes `POST /command`: parses the request body, validates both required fields are present, dispatches to the correct handler via `COMMANDS`, maps exceptions to HTTP status codes, and returns a JSON response.
- Logs incoming requests, resolved child IDs, dispatched command names, and API responses at DEBUG level.

#### `baby_buddy/__init__.py`

Re-exports `BabyBuddyClient` so that `app.py` can import it as `from baby_buddy import BabyBuddyClient`.

#### `baby_buddy/client.py`

The core HTTP layer. Contains the `BabyBuddyClient` class:

- `__init__`: creates a `requests.Session` pre-configured with `Authorization: Token <key>` and `Content-Type: application/json` headers. Initialises an empty `_child_cache` dict.
- `resolve_child(name)`: looks up a child by `first_name`, caches the result, raises `ValueError` if not found.
- `_get(path, params)`: GET request, raises `HTTPError` on non-2xx.
- `_post(path, data)`: POST JSON, raises on non-2xx.
- `_patch(path, data)`: PATCH JSON, raises on non-2xx.
- `_now()`: returns the current UTC time as an ISO-8601 string.
- `find_unfinished(endpoint, child_id)`: fetches the latest entry for a child, returns it only if `start == end` (parsed as `datetime` objects for reliable comparison), otherwise returns `None`.

#### `baby_buddy/feedings.py`

Handler functions for all five feeding commands. Each function has the signature `(client: BabyBuddyClient, child_id: int) -> dict | None` and calls `client._post` or `client._patch` directly.

#### `baby_buddy/sleep.py`

Handler functions for `sleep_start` and `sleep_finish`. Same signature convention as feedings.

#### `baby_buddy/changes.py`

Handler functions for `diaper_change_wet_solid` and `diaper_change_solid`. Diaper changes use a `time` field (single timestamp) instead of `start`/`end`.

#### `baby_buddy/registry.py`

The single source of truth for command routing. Contains the `COMMANDS` dict mapping every command name string to its handler callable. Adding a command to this dict is the only change required in this file when extending the service.

---

## Adding a New Command

Adding a command to an existing activity type (e.g. a new feeding method) requires changes to two files.

**Step 1** — Add the handler function to the relevant module (e.g. `feedings.py`):

```python
def feeding_fortified_bottle(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a fortified bottle feeding session (start=end=now)."""
    now = client._now()
    logger.debug("feeding_fortified_bottle: child_id=%d time=%s", child_id, now)
    return client._post(
        "/api/feedings/",
        {
            "child": child_id,
            "start": now,
            "end": now,
            "type": "fortified breast milk",
            "method": "bottle",
            "tags": ["hass"],
        },
    )
```

**Step 2** — Register the command in `registry.py`:

```python
from .feedings import (
    ...
    feeding_fortified_bottle,
)

COMMANDS: dict[str, Callable] = {
    ...
    "feeding_fortified_bottle": feeding_fortified_bottle,
}
```

That is the complete change. No modifications to `app.py`, `client.py`, or any other file are needed.

---

## Adding a New Activity Type

Adding an entirely new activity type (e.g. tummy time, pumping) requires creating one new module and registering its handlers.

**Step 1** — Create `baby_buddy/tummy_time.py`:

```python
"""Handlers for tummy-time Baby Buddy commands."""

import logging
from .client import BabyBuddyClient

logger = logging.getLogger(__name__)


def tummy_time_start(client: BabyBuddyClient, child_id: int) -> dict:
    """Start a tummy time session (start=end=now)."""
    now = client._now()
    logger.debug("tummy_time_start: child_id=%d time=%s", child_id, now)
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
    """Finish the latest unfinished tummy time session."""
    logger.debug("tummy_time_finish: child_id=%d", child_id)
    entry = client.find_unfinished("/api/tummy-times/", child_id)
    if entry is None:
        logger.warning(
            "tummy_time_finish: no unfinished tummy time for child_id=%d; doing nothing",
            child_id,
        )
        return None
    now = client._now()
    return client._patch(f"/api/tummy-times/{entry['id']}/", {"end": now})
```

**Step 2** — Register in `registry.py`:

```python
from .tummy_time import tummy_time_start, tummy_time_finish

COMMANDS: dict[str, Callable] = {
    ...
    "tummy_time_start": tummy_time_start,
    "tummy_time_finish": tummy_time_finish,
}
```

No other files need to change. The new commands are immediately available via `POST /command`.
