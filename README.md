# Messenger

## One-time bootstrap of first admin

Registration endpoint is admin-only, so the first administrator must be created with a separate bootstrap command.

1. Set bootstrap env vars (see `/home/runner/work/messenger/messenger/.env.example`):
   - `FIRST_ADMIN_EMAIL`
   - `FIRST_ADMIN_PASSWORD`
   - `FIRST_ADMIN_NAME`
   - `FIRST_ADMIN_SURNAME`
   - `FIRST_ADMIN_PATRONYMIC` (optional)
2. Ensure DB is up and migrations are applied.
3. Run bootstrap command once:

```bash
python -m app.bootstrap.create_first_admin
```

Behavior:
- Command fails if at least one admin already exists (strict idempotency).
- Password is hashed via Argon2.
- On success, an audit log event is written without exposing password.

### Docker Compose one-time run

There is a dedicated profile-only service:

```bash
docker compose --profile bootstrap run --rm bootstrap-admin
```

This service does not run with regular `docker compose up` unless the `bootstrap` profile is enabled.