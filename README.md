sudo -i -u postgres

psql --username=postgres -c "drop database if exists courier;"
psql --username=postgres -c "create database courier;"


Create Migration
alembic revision --autogenerate -m "YOUR_COMMENT_HERE"

Running Migration
alembic upgrade head



PGPASSWORD='postgres' psql -U postgres -d courier -h localhost


refresh airports
poetry run python scripts/import_airports.py


has no localization
no matching airports found, try to write in english 
search by airport, city, or country


comment safe text max 512
