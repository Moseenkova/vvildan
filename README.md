sudo -i -u postgres

psql --username=postgres -c "drop database if exists courier;"
psql --username=postgres -c "create database courier;"


Create Migration
alembic revision --autogenerate -m "Added account table"

Running Migration
alembic upgrade head
