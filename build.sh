#!/bin/bash
#
# Build script for RanobeDB Light Novels Calibre plugin
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$SCRIPT_DIR/src/ranobedb_light_novels"
OUTPUT_FILE="$SCRIPT_DIR/RanobeDB-Light-Novels.zip"

echo "Building RanobeDB Light Novels plugin..."

# Remove old build
if [ -f "$OUTPUT_FILE" ]; then
    rm "$OUTPUT_FILE"
    echo "Removed old build"
fi

# Create ZIP file
cd "$PLUGIN_DIR"
zip -r "$OUTPUT_FILE" \
    __init__.py \
    plugin-import-name-ranobedb_light_novels.txt

cd "$SCRIPT_DIR"

echo ""
echo "Plugin built successfully: $OUTPUT_FILE"
echo "Size: $(ls -lh "$OUTPUT_FILE" | awk '{print $5}')"
echo ""
echo "To install:"
echo "  calibre-customize -a $OUTPUT_FILE"
