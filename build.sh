#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="$SCRIPT_DIR/ukrainian_audio_generator.ankiaddon"

FILES=(
    __init__.py
    respeecher_client.py
    config.json
    README.md
    manifest.json
)

cd "$SCRIPT_DIR"

# Verify all source files exist
for f in "${FILES[@]}"; do
    if [[ ! -f "$f" ]]; then
        echo "ERROR: missing file: $f" >&2
        exit 1
    fi
done

zip -j "$OUTPUT" "${FILES[@]}"
echo "Built: $OUTPUT"
