#!/bin/sh
set -e
if [ ! -f /app/storage-state/.initialized ]; then
  echo "Initializing Go.Data database..."
  node server/install/install.js init-database
  mkdir -p /app/storage-state && touch /app/storage-state/.initialized
fi
node server/install/install.js migrate-database
exec node .
