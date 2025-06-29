#!/usr/bin/env bash
set -e

echo "Building AirCron.app..."

# Clean previous builds
rm -rf dist/ build/

# Create PyInstaller build
pyinstaller \
    --windowed \
    --onefile \
    --name "AirCron" \
    --add-data "templates:templates" \
    --add-data "static:static" \
    --hidden-import "app" \
    --hidden-import "app.api" \
    --hidden-import "app.views" \
    --hidden-import "app.cronblock" \
    --hidden-import "app.speakers" \
    --hidden-import "app.jobs_store" \
    main.py

echo "Build complete: dist/AirCron.app"
echo "Size: $(du -sh dist/AirCron.app | cut -f1)"

# Optional: codesign for local use
if command -v codesign >/dev/null 2>&1; then
    echo "Code signing..."
    codesign --force --deep --sign - dist/AirCron.app
    echo "Code signing complete"
fi

echo "AirCron.app is ready for distribution" 