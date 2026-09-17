# Docker

Copy the environment template and fill in the Telegram and secret values:

```sh
cp .env.example .env
docker compose up --build
```

The web app is available at <http://localhost:8080>. Compose starts PostgreSQL,
runs Alembic migrations, and then starts the API, Telegram bot, and frontend.
Change `APP_PORT` in `.env` to expose a different host port.

Useful commands:

```sh
docker compose logs -f
docker compose down
docker compose down --volumes  # also deletes the local PostgreSQL data
```

## Database restore

Start PostgreSQL, then run the restore helper. It asks for confirmation before
replacing existing database objects:

```sh
docker compose up -d db
./scripts/restore_backup.sh
```

You can also provide a different custom-format dump:

```sh
./scripts/restore_backup.sh backups/another.dump
```


## Migrations

Create a migration:

```sh
alembic revision --autogenerate -m "YOUR_COMMENT_HERE"
```

Run migrations:

```sh
alembic upgrade head
```

## Admin

Apply the migrations before creating the first superuser:

```sh
alembic upgrade head
python scripts/create_superuser.py
```

The script asks for the Telegram ID (`tg_id`) of an existing user, then a username,
password, and password confirmation. It promotes that user to superuser; no new
user is created. Telegram IDs are unique. Password input is hidden. With Docker Compose running, use the API container instead:

```sh
docker compose exec api python scripts/create_superuser.py
```

Then open <http://localhost:8080/admin> and sign in with those credentials.
If `APP_PORT` is configured in `.env`, replace `8080` with that port.



```sh
PGPASSWORD='postgres' psql -U postgres -d courier -h localhost
```


restore db
./scripts/restore_backup.sh backups/vvildan_20260902_cities.dump


### Telegram authentication

- Set the bot's Mini App/webapp button URL to `https://labhealth.pro/webapp/`
  (no trailing dot). It must be a Telegram Web App button, not a plain URL button.
  The Mini App SDK loads before React and supplies `initData`; the API verifies
  its signature and age, then logs the user in automatically without a login button.
- Set `WEBAPP_URL=https://labhealth.pro/webapp/` in the backend environment. Match
  notification buttons use this value and add `?tab=matches` automatically.
- Browser visitors to `https://labhealth.pro/` see **Log in with Telegram**.
  Browser visits to `/webapp/` use the same login screen.
  The current [Telegram Login SDK](https://core.telegram.org/bots/telegram-login)
  opens a popup and returns an ID token. The API verifies Telegram's RS256 signature,
  issuer, audience, expiry, issue time and the session-bound nonce before using the
  profile `id` to find the registered bot user. An OIDC `sub` is not a Bot API user ID.
- Users must first register through the bot, regardless of the login entry point.

In BotFather, select your bot, open **Login Widget**, add `https://labhealth.pro`
to **Allowed URLs**, and copy its **Client ID** to `TELEGRAM_LOGIN_CLIENT_ID` in `.env`.
Keep the default **RS256** signing algorithm. This popup SDK flow does not need a
Client Secret or a redirect callback URL. The previous legacy widget `/setdomain`
setup alone is not the configuration for this flow.

Rebuild the API and frontend together: `docker compose up -d --build api frontend`.
The production frontend is built with `/webapp/` as its public asset base.
The frontend Nginx supports both preserved and stripped `/webapp/` proxy prefixes,
and serves the app at `/` as well. The public reverse proxy must route the homepage
to this frontend instead of the default Nginx welcome page. See
[`deploy/nginx/labhealth-locations.conf`](deploy/nginx/labhealth-locations.conf) for
the location block to install in your existing HTTPS server configuration.
Do not use `Cross-Origin-Opener-Policy: same-origin`; Telegram's popup needs
`same-origin-allow-popups` or no COOP header.
