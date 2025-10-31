#!/bin/sh
set -e

# If DEV=1 and the command is uvicorn, add --reload for development hot-reload.
if [ "${DEV}" = "1" ] && [ "$1" = "uvicorn" ]; then
  echo "Starting uvicorn with --reload (DEV=1)"
  exec "$@" --reload
fi

# Otherwise exec whatever was requested
exec "$@"


