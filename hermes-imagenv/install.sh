#!/bin/bash
# hermes-imagenv plugin installer

set -e

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PLUGIN_DEST="$HERMES_HOME/plugins/hermes-imagenv"

echo "📦 Installing hermes-imagenv plugin..."

# Handle update - remove existing plugin if present
if [ -d "$PLUGIN_DEST" ]; then
    echo "🔄 Updating existing plugin..."
    rm -rf "$PLUGIN_DEST"
fi

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
    echo "Installing PyTorch (CPU)..."
    pip install torch --index-url https://download.pytorch.org/whl/cpu --quiet
fi

# Create directories
mkdir -p "$PLUGIN_DEST/scripts"
mkdir -p "$PLUGIN_DEST/dashboard"
mkdir -p "$HERMES_HOME/cache/ImGen/models"
mkdir -p "$HERMES_HOME/cache/ImGen/output"

# Copy plugin files
cp -r scripts/* "$PLUGIN_DEST/scripts/" 2>/dev/null || true
cp -r dashboard/* "$PLUGIN_DEST/dashboard/" 2>/dev/null || true
cp SKILL.md "$PLUGIN_DEST/" 2>/dev/null || true

# Validate plugin_api.py syntax if present
if [ -f "$PLUGIN_DEST/dashboard/plugin_api.py" ]; then
    if ! python3 -m py_compile "$PLUGIN_DEST/dashboard/plugin_api.py" 2>/dev/null; then
        echo "⚠️ plugin_api.py has syntax errors"
    fi
fi

# Verify imports
echo "Verifying imports..."
for imp in diffusers torch; do
    if ! check_import "$imp"; then
        echo "❌ Failed to import $imp"
        exit 1
    fi
done

echo "✅ hermes-imagenv installed to $PLUGIN_DEST"
echo ""
echo "📝 Next steps:"
echo "   1. Place LCM model in: $HERMES_HOME/cache/ImGen/models/lcm_dreamshaper/"
echo "   2. Models <1.5GB recommended for CPU inference"
echo "   3. Use /img <prompt> in Telegram to generate images"