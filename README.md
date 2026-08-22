restore db
PGPASSWORD='postgres' pg_restore \
  --host=localhost \
  --username=postgres \
  --dbname=courier \
  --clean --if-exists \
  --no-owner --no-acl \
  --exit-on-error \
  backups/vvildan_20260822_184104.dump



sudo -i -u postgres

psql --username=postgres -c "drop database if exists courier;"
psql --username=postgres -c "create database courier;"


Create Migration
alembic revision --autogenerate -m "YOUR_COMMENT_HERE"

Running Migration
alembic upgrade head



PGPASSWORD='postgres' psql -U postgres -d courier -h localhost
