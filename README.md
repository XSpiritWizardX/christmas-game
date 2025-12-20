# Christmas Multiplayer Prototype

This is a mobile-first, real-time prototype using Flask-SocketIO and React.

## Features
- Real-time rooms (up to 16 players)
- Lobby movement with virtual joystick + snowball throw
- 5 rounds scaffolded (survival, snowball fight, maze, carry light, bonus tap)
- Live leaderboard + host-controlled rounds

## Local setup

### Server
```
cd server
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Client
```
cd client
npm install
npm run dev
```

Open http://localhost:5173 on your phone or desktop browser.

## Config
- Set `VITE_SERVER_URL` if your server runs on a different host or port.

## Next steps
- Replace UI copy, colors, and add your Christmas assets
- Tune round durations, maps, and scoring
- Add sound effects and music once assets are ready
