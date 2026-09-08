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


### Browser Telegram login

Opening `/webapp/` in a browser shows Telegram login before the request forms.
The login widget uses the existing `BOT_TOKEN`; no frontend secret is needed.
In @BotFather, use `/setdomain` for that bot and link `labhealth.pro` (or the
hostname of your deployment). Rebuild/redeploy the API and frontend together.
Users must first register through the bot. Mini App launch authentication remains
supported. Browser login signatures and timestamps are verified by the API.
