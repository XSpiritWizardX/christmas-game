## Summary

Explain the player-facing or engineering change and why it is needed.

## Linked issue

Closes #

## Validation

- [ ] Multiplayer regression tests pass (`python -m unittest discover -s tests -v`)
- [ ] Python source compilation passes
- [ ] React production build passes (`npm run build`)
- [ ] Production Docker image builds
- [ ] Relevant create/join/reconnect/round flow was smoke-tested when affected

## Review checklist

- [ ] Server-authoritative game rules remain enforced on the server
- [ ] New multiplayer/game-state behavior includes automated coverage where practical
- [ ] Reconnect, host transfer, capacity, and client contract implications were considered
- [ ] No credentials, production database URLs, or user data are committed
- [ ] README/docs/changelog are updated when behavior or workflow changes
- [ ] Gameplay/UI changes include screenshots or short video when useful

## Release impact

Patch / minor feature / breaking major / no release impact.
