# Snow Dash — Christmas Multiplayer Game

[![CI](https://github.com/XSpiritWizardX/christmas-game/actions/workflows/ci.yml/badge.svg)](https://github.com/XSpiritWizardX/christmas-game/actions/workflows/ci.yml)

Snow Dash is a mobile-first real-time Christmas party game built with React/Vite and Flask-SocketIO. Players create or join rooms, compete through fast holiday-themed rounds, play alongside themed AI opponents, reconnect after short drops, and carry persistent account/store data through PostgreSQL or a local SQLite fallback.

This public repository is maintained as an engineering showcase as well as a game: work is tracked in GitHub issues, implemented on focused branches, validated in CI, reviewed through pull requests, and published through semantic-version GitHub Releases.

## Engineering highlights

- Server-authoritative multiplayer room and round state using Flask-SocketIO
- Server simulation tuned for responsive gameplay with lower-frequency world broadcasts to reduce network traffic
- 15-second reconnect grace period that preserves active player state through short disconnects or refreshes
- Automatic resume/rejoin support with host, inventory, score, position, and round continuity
- Room capacity and unique color allocation for up to 16 players
- Themed AI personalities with different movement/action cadence
- 3-2-1-GO synchronized starts and multiple round/game modes
- Server-side display-name normalization for safer non-React announcements and overlays
- PostgreSQL production persistence with local SQLite fallback
- Multi-stage Docker build that compiles the React client separately from the non-root Python runtime
- Automated multiplayer game-state regression tests
- GitHub Actions checks for server tests/compile, client production build, and the exact Docker image
- Dependabot, structured issues, PR Definition of Done, architecture/security docs, changelog, and verified tag-driven releases

## Player-facing polish

The production game includes faster party-game pacing, score popups, elimination feedback, screen shake, haptics on supported phones, round-result overlays, confetti, ambient snowfall, and reduced-motion support. Crown progression and store items are cosmetic so account progression does not create competitive movement advantages.

Holiday cosmetics include Ice Drift Skin, Sleigh Bell Aura, Candy Cane Trail, Elf Hat Badge, and Victory Sparkles. AI opponents include Krampus, Rudolph, Frosty, Ginger, Jingles, Tinsel, Coal, and Noel.

## Tech stack

| Layer | Technology |
| --- | --- |
| Client | React 18, Vite, Socket.IO Client |
| Realtime/API | Flask, Flask-SocketIO, Flask-CORS |
| Runtime | Gunicorn + Eventlet |
| Persistence | PostgreSQL production, SQLite local fallback |
| Testing | Python `unittest`, Python compilation, Vite production build |
| Delivery | Docker multi-stage build, Render Blueprint, GitHub Actions, GitHub Releases |

## Production architecture

Production runs as **one Docker web service**. Vite compiles the React client during the first Docker stage. The Python runtime then serves those assets and handles the HTTP API and Socket.IO connection from the same origin.

```text
React / Vite / Socket.IO client
              |
              | input + realtime events
              v
      Flask + Flask-SocketIO
              |
        authoritative rooms
        rounds / scoring / AI
        reconnect + persistence
              |
              v
   PostgreSQL / SQLite fallback
```

The production image runs as a non-root user and launches one Gunicorn Eventlet worker appropriate to the in-process realtime room state used by this project.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system boundaries and quality strategy.

## Repository layout

```text
client/                    React/Vite game client and public assets
server/
  app.py                   Flask-SocketIO events and simulation
  game_state.py            authoritative room/player/game state
  store.py                 persistence layer
  requirements.txt         Python runtime dependencies
web.py                     production composition and reliability/polish layer
tests/                     deterministic multiplayer regression tests
.github/
  workflows/ci.yml         PR/push quality gate
  workflows/release.yml    verified semantic-version releases
  ISSUE_TEMPLATE/          structured bug/feature intake
Dockerfile                 multi-stage production image
render.yaml                single-service Render Blueprint
CHANGELOG.md               notable product/engineering changes
docs/                      architecture and release documentation
```

## Multiplayer reliability layer

The production composition in `web.py` adds a dedicated party-game reliability layer around the core server:

- a 15-second reconnect/resume grace period
- player slot preservation during brief disconnects
- safe display-name normalization
- tuned round durations
- themed bot personalities
- cosmetic store definitions and fairness controls

Core room membership, player state, colors, host transfer, serialization, and related state rules live in `server/game_state.py` so they can be tested independently from Socket.IO transport behavior.

## Testing and CI

Install the server dependencies and run the multiplayer regression suite:

```bash
python -m pip install -r server/requirements.txt
python -m unittest discover -s tests -v
```

Compile the primary Python sources:

```bash
python -m py_compile web.py server/app.py server/game_state.py server/store.py
```

Build the production client:

```bash
npm --prefix client ci
npm --prefix client run build
```

Verify the deployable image:

```bash
docker build -t snow-dash .
```

GitHub Actions performs these checks on pull requests and pushes to `main`. The deterministic regression suite currently protects player-name identity rules, room creation, color uniqueness and Holly's reserved black color behavior, maximum player capacity, host transfer, and the room payload contract consumed by clients.

## Local development

### Server

```bash
cd server
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Client

```bash
cd client
npm ci
npm run dev
```

Local Vite development uses `http://localhost:5000` unless `VITE_SERVER_URL` is configured. Production uses the web service's own origin automatically.

## Docker

Build:

```bash
docker build -t snow-dash .
```

Run with the SQLite fallback:

```bash
docker run --rm -p 10000:10000 -e PORT=10000 snow-dash
```

Run with PostgreSQL:

```bash
docker run --rm -p 10000:10000 \
  -e PORT=10000 \
  -e DATABASE_URL="postgresql://..." \
  snow-dash
```

Open `http://localhost:10000`.

## Render deployment

`render.yaml` defines the single Docker web service. Production should provide `DATABASE_URL`; the application uses its existing `xmas` schema behavior. Render supplies `PORT` automatically.

Health check:

```text
/health
```

A separate static-site service is not required.

## Development workflow

1. Create or link a GitHub issue with acceptance criteria.
2. Work on a focused branch from `main`.
3. Add/update regression coverage for multiplayer or game-state changes.
4. Open a pull request using the repository checklist.
5. Merge only after CI is green and review concerns are resolved.
6. Update `CHANGELOG.md` for notable changes.
7. Publish semantic-version tags through the verified Release workflow.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [docs/RELEASES.md](docs/RELEASES.md).

## Release model

Tags matching `vMAJOR.MINOR.PATCH` trigger `.github/workflows/release.yml`. Before a GitHub Release is created, the workflow reruns the server regression suite, compiles Python, builds the React client, and builds the production Docker image. A failed quality gate prevents release publication.

## Security and fairness

The server is the authority for shared multiplayer outcomes; client input is treated as untrusted intent. Credentials and production database URLs belong in deployment environment variables, never source control. Security-sensitive reports should use GitHub private vulnerability reporting rather than public issues. See [SECURITY.md](SECURITY.md).
