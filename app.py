"""Flask entry point: loads config, wires up BabyBuddyClient, and exposes POST /command."""

import logging
import os

from flask import Flask, jsonify, request

from baby_buddy import BabyBuddyClient
from baby_buddy.registry import COMMANDS

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Config — fail fast on missing required env vars
# ------------------------------------------------------------------

BB_HOST = os.environ.get("BB_HOST")
BB_KEY = os.environ.get("BB_KEY")

if not BB_HOST:
    raise RuntimeError("Missing required environment variable: BB_HOST")
if not BB_KEY:
    raise RuntimeError("Missing required environment variable: BB_KEY")

PORT = int(os.environ.get("PORT", 8080))

client = BabyBuddyClient(BB_HOST, BB_KEY)
logger.debug("BabyBuddyClient ready; registered commands: %s", list(COMMANDS))

# ------------------------------------------------------------------
# Flask app
# ------------------------------------------------------------------

app = Flask(__name__)


@app.route("/command", methods=["POST"])
def handle_command():
    """Dispatch a named command for a given child to the Baby Buddy API."""
    body = request.get_json(silent=True) or {}
    logger.debug("Incoming request body: %s", body)

    command = body.get("command")
    child = body.get("child")

    if not command or not child:
        logger.debug("Bad request: missing 'command' or 'child' field")
        return jsonify({"error": "Both 'command' and 'child' are required"}), 400

    if command not in COMMANDS:
        logger.debug("Unknown command: %s", command)
        return jsonify({"error": f"Unknown command: '{command}'"}), 400

    try:
        child_id = client.resolve_child(child)
        logger.debug("Resolved child '%s' -> id=%d", child, child_id)
    except ValueError as exc:
        logger.warning("Child not found: %s", exc)
        return jsonify({"error": str(exc)}), 404

    try:
        logger.debug("Dispatching command '%s' for child_id=%d", command, child_id)
        result = COMMANDS[command](client, child_id)
        logger.debug("Command '%s' result: %s", command, result)
        return jsonify({"ok": True, "result": result}), 200
    except Exception as exc:
        logger.exception("Unexpected error executing command '%s': %s", command, exc)
        return jsonify({"error": "Internal server error", "detail": str(exc)}), 500


if __name__ == "__main__":
    logger.info("Starting Baby Buddy command service on port %d", PORT)
    app.run(host="0.0.0.0", port=PORT)
