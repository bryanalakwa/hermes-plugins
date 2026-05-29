#!/bin/bash
# hermes-imagenv plugin installer

set -e

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_DEST="$HERMES_HOME/plugins/hermes-imagenv"

echo "📦 Installing hermes-imagenv plugin..."

# Check for required dependencies
check_import() {
    python3 -c "import $1" 2>/dev/null || return 1
}

# Validate dependencies
missing_deps=()
for dep in diffusers transformers accelerate safetensors; do
    if ! check_import "$dep"; then
        missing_deps+=("$dep")
    fi
done

if [ ${#missing_deps[@]} -gt 0 ]; then
    echo "Missing dependencies: ${missing_deps[*]}"
    echo "Installing diffusers and dependencies..."
    pip install diffusers transformers accelerate safetensors --quiet
fi

# Check for torch
if ! check_import "torch"; then
    echo "Installing PyTorch..."
    pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet
fi

# Create directories
mkdir -p "$PLUGIN_DEST/scripts"
mkdir -p "$PLUGIN_DEST/dashboard"
mkdir -p "$HERMES_HOME/cache/ImGen/models"

# Copy plugin files
cp -r scripts/* "$PLUGIN_DEST/scripts/" 2>/dev/null || true
cp -r dashboard/* "$PLUGIN_DEST/dashboard/" 2>/dev/null || true
cp SKILL.md "$PLUGIN_DEST/" 2>/dev/null || true

echo "✅ hermes-imagenv installed to $PLUGIN_DEST"
echo "Models should be placed in $HERMES_HOME/cache/ImGen/models/"
