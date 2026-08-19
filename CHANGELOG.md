# Changelog

Notable Snow Dash product and engineering changes are recorded here. Releases use semantic-version tags and GitHub generated release notes.

## Unreleased

### Engineering
- Add multiplayer room-state regression tests covering identity rules, room creation, color allocation, capacity, host transfer, and the serialized client contract.
- Expand GitHub Actions into separate server, client, and production Docker quality gates.
- Add tag-driven GitHub Release verification and publishing.
- Add structured issue forms, PR checklist, Dependabot, contribution guidance, security policy, architecture documentation, and release documentation.

### Documentation
- Present the repository publicly as **Snow Dash**, a real-time Christmas multiplayer engineering showcase.

## Versioning

- **Patch** (`vX.Y.Z`): compatible fixes, security/reliability improvements.
- **Minor** (`vX.Y.0`): backward-compatible game modes, multiplayer features, or substantial polish.
- **Major** (`vX.0.0`): intentionally breaking protocol, persistence, or platform changes.
