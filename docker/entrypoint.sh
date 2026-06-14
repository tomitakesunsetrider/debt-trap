#!/bin/sh
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"

echo "Waiting for database at ${DB_HOST}:${DB_PORT} ..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "Database is up."

python manage.py migrate --noinput

# migrate 後にデモデータを投入（SEED_DEMO=false で無効化可能）。
# seed_demo は冪等なため、再起動で重複投入されない。
if [ "${SEED_DEMO:-true}" = "true" ]; then
  echo "Seeding demo data ..."
  python manage.py seed_demo
fi

python manage.py collectstatic --noinput

exec "$@"
