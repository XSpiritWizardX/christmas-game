import os
import sys

from flask import send_from_directory

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(ROOT_DIR, "server")
CLIENT_DIST = os.path.join(ROOT_DIR, "client", "dist")

# The existing server modules use local imports (game_state, store), so keep
# server/ on sys.path while exposing one production entrypoint at the repo root.
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from server.app import app, socketio  # noqa: E402


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_client(path):
    """Serve Vite's production build and fall back to index.html for the SPA."""
    if path:
        candidate = os.path.join(CLIENT_DIST, path)
        if os.path.isfile(candidate):
            return send_from_directory(CLIENT_DIST, path)
    return send_from_directory(CLIENT_DIST, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    socketio.run(app, host="0.0.0.0", port=port)
