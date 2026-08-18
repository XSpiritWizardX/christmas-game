# Christmas Multiplayer Game

A mobile-first real-time Christmas party game using React/Vite, Flask-SocketIO, and PostgreSQL/SQLite persistence.

## Current game upgrades

The production build now includes a dedicated party-game polish and reliability layer:

- 15-second reconnect grace period that preserves player position, score, host status, inventory, and active-round state.
- Automatic rejoin after a short connection drop or browser refresh.
- Disconnected players stop moving immediately while their slot is held.
- 3-2-1-GO synchronized round starts.
- Shorter, faster-paced rounds for better party-game pacing.
- Server-authoritative 60 Hz simulation with world-state broadcasts reduced to roughly 30 Hz to lower multiplayer bandwidth.
- Client input deduplication/throttling to avoid redundant Socket.IO traffic.
- Christmas AI personalities including Krampus, Rudolph, Frosty, Ginger, Jingles, Tinsel, Coal, and Noel.
- AI personality differences in movement and action cadence.
- Score popups, elimination feedback, screen shake, haptics on supported phones, round-result overlays, confetti, and ambient snowfall.
- Reduced-motion support for players who disable motion effects at the OS/browser level.
- Crown progression is cosmetic-only; store purchases no longer create competitive movement advantages.
- Holiday cosmetics include Ice Drift Skin, Sleigh Bell Aura, Candy Cane Trail, Elf Hat Badge, and Victory Sparkles.
- Server-side player-name normalization for safe result/announcement presentation.
- GitHub Actions verification for the production Vite build and Python source compilation.

## Production architecture

Production runs as **one Docker web service**:

- Vite builds the React client during the Docker build.
- Flask serves the compiled React assets and the existing HTTP API.
- Flask-SocketIO handles the real-time game connection on the same origin.
- Gunicorn + Eventlet run the production web process.
- `DATABASE_URL` enables PostgreSQL persistence using the existing `xmas` schema.
- If `DATABASE_URL` is not set, the server falls back to SQLite for local/dev use.

No separate Render Static Site is required.

## Docker

Build:

```bash
docker build -t xmas-eve-game .
```

Run with SQLite fallback:

```bash
docker run --rm -p 10000:10000 -e PORT=10000 xmas-eve-game
```

Run with PostgreSQL:

```bash
docker run --rm -p 10000:10000 \
  -e PORT=10000 \
  -e DATABASE_URL="postgresql://..." \
  xmas-eve-game
```

Open `http://localhost:10000`.

## Render

The repository contains `render.yaml` configured for a single Docker web service named `xmas-eve-game`.

Required production environment variable:

- `DATABASE_URL` - PostgreSQL connection string. The app creates/uses the `xmas` schema automatically.

Render supplies `PORT` automatically.

Health check:

- `/health`

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
npm install
npm run dev
```

Local Vite development continues to use `http://localhost:5000` unless `VITE_SERVER_URL` is set. Production builds use the web service's own origin automatically.
