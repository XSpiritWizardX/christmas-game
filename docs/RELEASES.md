# Release Process

Snow Dash uses semantic-version tags and GitHub Releases so multiplayer features and reliability work have a visible shipment history.

## Release checklist

1. The work is linked to a GitHub issue and merged through a pull request.
2. CI is green on `main`.
3. `CHANGELOG.md` records notable player-facing or engineering changes.
4. Multiplayer changes include appropriate game-state or integration coverage.
5. The create/join/reconnect/round flow is smoke-tested when affected.
6. The production Docker image builds successfully.
7. Persistence/configuration changes are verified against the intended deployment environment.

## Versioning

- Patch: compatible fixes, reliability/security improvements, small polish.
- Minor: backward-compatible game modes, multiplayer features, substantial content/polish.
- Major: intentionally breaking network protocol, persistence, or deployment behavior.

## Publishing

Push a `vMAJOR.MINOR.PATCH` tag from the intended `main` commit. `.github/workflows/release.yml` reruns server tests, Python compilation, the client production build, and the production Docker build. Only after those checks succeed does the workflow create a GitHub Release with generated notes.

## Deployment

The GitHub Release is the versioned software record. Render deployment remains a separate operational step. After deployment, verify `/health` plus a focused multiplayer smoke test and capture any remediation in a follow-up issue or PR.
