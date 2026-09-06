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

SQLAdmin is available at `/admin`. Create an initial superuser after applying
migrations; the script prompts for a username and password without echoing it:

```sh
python scripts/create_superuser.py
```

With Docker Compose running, use:

```sh
docker compose exec api python scripts/create_superuser.py
```



```sh
PGPASSWORD='postgres' psql -U postgres -d courier -h localhost
```


restore db
./scripts/restore_backup.sh backups/vvildan_20260902_cities.dump
