#!/bin/sh
set -e

HOST="$POSTGRES_HOST"
PORT="${POSTGRES_PORT:-5432}"

if [ -z "$HOST" ]; then
  echo "ERROR: POSTGRES_HOST is not set."
  exit 1
fi

if [ -z "$POSTGRES_USER" ]; then
  echo "ERROR: POSTGRES_USER is not set."
  exit 1
fi

echo "Waiting for PostgreSQL at $HOST:$PORT as user $POSTGRES_USER..."

until pg_isready -h "$HOST" -p "$PORT" -U "$POSTGRES_USER"; do
  sleep 2
done

echo "PostgreSQL is ready."

exec "$@"
