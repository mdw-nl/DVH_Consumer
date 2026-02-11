#!/bin/sh
set -e

# Environment variables
HOST="${POSTGRES_HOST}"
PORT="${POSTGRES_PORT:-5432}"
USER="${POSTGRES_USER}"

# Sanity checks
if [ -z "$HOST" ]; then
  echo "ERROR: POSTGRES_HOST is not set."
  exit 1
fi

if [ -z "$USER" ]; then
  echo "ERROR: POSTGRES_USER is not set."
  exit 1
fi

echo "Waiting for PostgreSQL at $HOST:$PORT as user $USER..."

# Wait until Postgres is ready
until pg_isready -h "$HOST" -p "$PORT" -U "$USER"; do
  sleep 2
done

echo "PostgreSQL is ready."

# Run DB initialization
echo "Running DB initialization..."
python -m DICOM_solver.PostrgresDVHdb

# Run main application
echo "Starting main.py..."
exec python main.py
