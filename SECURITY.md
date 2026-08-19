# Security Policy

## Reporting

Do not publish an unpatched vulnerability, exposed credential, account/data leak, injection vector, or multiplayer abuse path in a public issue. Use GitHub private vulnerability reporting / Security Advisories when available and include reproduction steps, impact, and the affected event/route/component.

## Security and trust boundaries

The server is authoritative for room membership, round/game state, scoring, movement rules, item/cosmetic ownership, and persistence. Client input must be treated as untrusted and validated server-side.

Player names and other user-controlled display strings must remain normalized before use in non-React overlays or announcements. Database credentials and production configuration belong in deployment environment variables rather than source control.

Changes involving Socket.IO events, reconnect/resume tokens, account or store data, persistence, scoring, or server-authoritative rules require explicit review and regression coverage where practical.

## Supported version

The actively maintained `main` branch is the supported version. Security fixes should pass CI and be released promptly with clear release notes.
