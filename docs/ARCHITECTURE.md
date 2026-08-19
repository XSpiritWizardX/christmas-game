# Architecture

Snow Dash is a real-time multiplayer party game delivered as one Docker web service. The browser renders the game and sends player intent; Flask-SocketIO owns the shared connection, while the server remains authoritative for room membership, round state, movement/game rules, scoring, bots, reconnect state, and persistence.

```text
Players / browsers
  └─ React + Vite + Socket.IO client
       ├─ rendering / input / effects
       └─ player intent
              |
              v
       Flask + Flask-SocketIO
              |
              ├─ authoritative GameState / rooms
              ├─ round simulation + AI
              ├─ reconnect/resume layer
              ├─ HTTP/store/account behavior
              └─ persistence
                    ├─ PostgreSQL in production
                    └─ SQLite fallback locally
```

## Runtime boundaries

**Client:** `client/` is the React/Vite application. Production uses same-origin Socket.IO and HTTP traffic; local Vite development can target the local server.

**Authoritative game state:** `server/game_state.py` owns room creation/joining, player/color allocation, host transfer, bots, serialized room state, and core game-state mutation.

**Realtime game service:** `server/app.py` defines Flask-SocketIO handlers and simulation behavior.

**Production upgrade layer:** `web.py` composes the server for deployment and adds reconnect/resume handling, player-name normalization, tuned round pacing, themed AI behavior, and other party-game production improvements.

**Persistence:** `server/store.py` abstracts persistent account/store data. `DATABASE_URL` selects PostgreSQL; local development can use SQLite.

## Networking and fairness

The client sends input rather than authoritative world state. Server-side rules determine shared outcomes. The production game runs a high-frequency server simulation while broadcasting world state at a lower rate to balance responsiveness with bandwidth. Reconnect handling preserves a player's slot for a short grace period rather than immediately destroying active-round state.

## Container architecture

The Dockerfile is multi-stage: Node 20 builds the Vite bundle, then a Python 3.12 runtime installs server dependencies, copies only the compiled client plus Python service code, creates a non-root `appuser`, and launches Gunicorn with the Eventlet worker. This keeps frontend toolchains out of the final runtime image and matches the single-service Render deployment.

## Quality strategy

`tests/test_game_state.py` protects deterministic multiplayer rules that can be validated without a browser: room setup, identity/color allocation, maximum capacity, host transfer, and the serialized contract consumed by clients. GitHub Actions additionally installs production Python dependencies, compiles server sources, builds the React client, and builds the exact production Docker image.

Future test layers can add Socket.IO integration coverage and browser-level end-to-end tests for create/join/reconnect/round flows without weakening the fast deterministic game-state suite.
