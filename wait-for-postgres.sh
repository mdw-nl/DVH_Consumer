#!/bin/bash
set -e

host="$1"
shift
cmd="$@"

until pg_isready -h "$POSTGRES_HOST" -U "$POSTGRES_USER"; do
  echo "Waiting for PostgreSQL at $host..."
  sleep 2
done

echo "PostgreSQL is ready. Running command..."
exec $cmd