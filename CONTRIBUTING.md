# Contributing

Snow Dash uses an issue-first, pull-request workflow so multiplayer and gameplay changes remain reviewable and the public engineering process stays easy to inspect.

## Workflow

1. Start from a GitHub issue with the desired outcome and acceptance criteria.
2. Create a focused branch from `main` using `feat/`, `fix/`, `test/`, `docs/`, or `chore/`.
3. Keep game-state tests and documentation with the behavior they protect.
4. Run the same checks used by CI.
5. Open a pull request that links the issue and explains multiplayer/release impact.
6. Merge only after automated checks pass and review concerns are resolved.

## Local quality checks

```bash
python -m pip install -r server/requirements.txt
python -m unittest discover -s tests -v
python -m py_compile web.py server/app.py server/game_state.py server/store.py
npm --prefix client ci
npm --prefix client run build
docker build -t snow-dash:local .
```

## Multiplayer Definition of Done

A multiplayer change is complete when server authority and fairness remain clear, important room/game-state behavior is covered by regression tests, reconnect/host/capacity implications are considered where relevant, the client still builds, the production container builds, documentation is current, and the PR identifies release impact.

Never commit database credentials, production connection strings, real account data, or `.env` files.
