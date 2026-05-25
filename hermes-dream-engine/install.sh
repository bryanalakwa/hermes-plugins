#!/bin/bash
# Dream Engine — install script
set -e

HERMES_PLUGINS="${HERMES_HOME:-$HOME/.hermes}/plugins"
DEST="$HERMES_PLUGINS/hermes-dream-engine"

echo "Installing hermes-dream-engine to $DEST"

# Remove existing installation
if [ -d "$DEST" ]; then
    echo "Removing existing installation..."
    rm -rf "$DEST"
fi

# Copy plugin files
mkdir -p "$DEST"
cp -r "$(dirname "$0")"/* "$DEST/"

# Clean up install artifacts
rm -f "$DEST/install.sh"
rm -rf "$DEST/__pycache__"

echo "Installed hermes-dream-engine to $DEST"
echo "Restart the gateway to activate: hermes gateway restart"
