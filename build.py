#!/usr/bin/env python3
"""
Build script for RanobeDB Light Novels Calibre plugin.

Creates a ZIP file that can be installed in Calibre.
"""

import os
import zipfile
from pathlib import Path


def build_plugin():
    """Build the plugin ZIP file."""
    # Paths
    project_root = Path(__file__).parent
    plugin_dir = project_root / "src" / "ranobedb_light_novels"
    output_file = project_root / "RanobeDB-Light-Novels.zip"

    # Remove old build if exists
    if output_file.exists():
        output_file.unlink()
        print(f"Removed old build: {output_file}")

    # Files to include in the plugin
    files_to_include = [
        "__init__.py",
        "plugin-import-name-ranobedb_light_novels.txt",
    ]

    # Create ZIP file
    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in files_to_include:
            filepath = plugin_dir / filename
            if filepath.exists():
                zf.write(filepath, filename)
                print(f"Added: {filename}")
            else:
                print(f"Warning: {filename} not found, skipping")

    print(f"\nPlugin built successfully: {output_file}")
    print(f"Size: {output_file.stat().st_size} bytes")
    print("\nTo install:")
    print(f"  calibre-customize -a {output_file}")

    return output_file


if __name__ == "__main__":
    build_plugin()
