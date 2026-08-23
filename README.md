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

```sh
PGPASSWORD='postgres' pg_restore \
  --host=localhost \
  --username=postgres \
  --dbname=courier \
  --clean --if-exists \
  --no-owner --no-acl \
  --exit-on-error \
  backups/vvildan_20260822_184104.dump
```



```sh
sudo -i -u postgres

psql --username=postgres -c "drop database if exists courier;"
psql --username=postgres -c "create database courier;"
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



```sh
PGPASSWORD='postgres' psql -U postgres -d courier -h localhost
```
