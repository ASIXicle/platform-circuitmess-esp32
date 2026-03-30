#!/usr/bin/env bash
# =============================================================================
# install.sh — Set up the CircuitMess ESP32 PlatformIO platform
#
# Assumes:
#   - CircuitMess board package installed via Arduino IDE at:
#     ~/.arduino15/packages/cm/hardware/esp32/1.8.3/
#   - PlatformIO CLI available (pio)
#
# What this script does:
#   1. Verifies the CM Arduino IDE installation
#   2. Creates a symlink in PlatformIO's packages dir pointing to the CM fork
#   3. Injects platformio-build.py and package.json into the framework
#   4. Installs this platform into PlatformIO
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Paths ────────────────────────────────────────────────────────────────────
CM_FRAMEWORK_SRC="$HOME/.arduino15/packages/cm/hardware/esp32/1.8.3"
PIO_PACKAGES_DIR="$HOME/.platformio/packages"
FRAMEWORK_PKG_NAME="framework-arduinoespressif32-cm"
FRAMEWORK_PKG_DIR="$PIO_PACKAGES_DIR/$FRAMEWORK_PKG_NAME"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  CircuitMess ESP32 — PlatformIO Platform Installer          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Verify CM Arduino IDE installation ───────────────────────────────
echo "[1/4] Checking CircuitMess Arduino-ESP32 installation..."
if [ ! -d "$CM_FRAMEWORK_SRC" ]; then
    echo "  ERROR: CircuitMess board package not found at:"
    echo "    $CM_FRAMEWORK_SRC"
    echo ""
    echo "  Install it via Arduino IDE:"
    echo "    1. File → Preferences → Additional Board Manager URLs"
    echo "    2. Add: https://raw.githubusercontent.com/CircuitMess/Arduino-Packages/master/package_circuitmess.com_esp32_index.json"
    echo "    3. Tools → Board → Boards Manager → search 'CircuitMess'"
    echo "    4. Install 'CircuitMess ESP32 Boards'"
    echo ""
    echo "  Or via arduino-cli:"
    echo "    arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/CircuitMess/Arduino-Packages/master/package_circuitmess.com_esp32_index.json"
    echo "    arduino-cli core install cm:esp32"
    exit 1
fi

# Verify critical subdirectories exist
for subdir in "cores/esp32" "tools/sdk/lib" "tools/sdk/include" "tools/sdk/ld"; do
    if [ ! -d "$CM_FRAMEWORK_SRC/$subdir" ]; then
        echo "  ERROR: Expected directory missing: $CM_FRAMEWORK_SRC/$subdir"
        echo "  The CM board package may be corrupted. Reinstall it."
        exit 1
    fi
done

# Verify chatter2 variant exists
if [ ! -d "$CM_FRAMEWORK_SRC/variants/chatter2" ]; then
    echo "  WARNING: variants/chatter2/ not found."
    echo "  Available variants:"
    ls "$CM_FRAMEWORK_SRC/variants/" 2>/dev/null || echo "    (none)"
    echo ""
    echo "  The board definition expects variant 'chatter2'."
    echo "  Continuing anyway — you may need to adjust board_build.variant"
fi

echo "  ✓ Found CM framework at: $CM_FRAMEWORK_SRC"
echo ""

# ── Step 2: Create framework symlink ────────────────────────────────────────
echo "[2/4] Setting up framework package in PlatformIO..."
mkdir -p "$PIO_PACKAGES_DIR"

if [ -L "$FRAMEWORK_PKG_DIR" ]; then
    echo "  Removing existing symlink..."
    rm "$FRAMEWORK_PKG_DIR"
elif [ -d "$FRAMEWORK_PKG_DIR" ]; then
    echo "  WARNING: $FRAMEWORK_PKG_DIR exists as a directory."
    echo "  Backing up to ${FRAMEWORK_PKG_DIR}.bak"
    mv "$FRAMEWORK_PKG_DIR" "${FRAMEWORK_PKG_DIR}.bak"
fi

ln -s "$CM_FRAMEWORK_SRC" "$FRAMEWORK_PKG_DIR"
echo "  ✓ Symlinked: $FRAMEWORK_PKG_DIR → $CM_FRAMEWORK_SRC"
echo ""

# ── Step 3: Inject PlatformIO build files ───────────────────────────────────
echo "[3/4] Injecting PlatformIO build scripts into framework..."

# package.json
if [ ! -f "$CM_FRAMEWORK_SRC/package.json" ]; then
    cp "$SCRIPT_DIR/tools/framework-package.json" "$CM_FRAMEWORK_SRC/package.json"
    echo "  ✓ Created: package.json"
else
    echo "  ℹ package.json already exists, skipping"
fi

# platformio-build.py
mkdir -p "$CM_FRAMEWORK_SRC/tools"
if [ ! -f "$CM_FRAMEWORK_SRC/tools/platformio-build.py" ]; then
    cp "$SCRIPT_DIR/tools/platformio-build.py" "$CM_FRAMEWORK_SRC/tools/platformio-build.py"
    echo "  ✓ Created: tools/platformio-build.py"
else
    echo "  ℹ tools/platformio-build.py already exists"
    echo "  To force update: cp $SCRIPT_DIR/tools/platformio-build.py $CM_FRAMEWORK_SRC/tools/platformio-build.py"
fi

echo ""

# ── Step 4: Install the platform ────────────────────────────────────────────
echo "[4/4] Installing platform into PlatformIO..."

# Use pio pkg install if available (PIO 6+), fall back to pio platform install
if pio pkg install --help >/dev/null 2>&1; then
    pio pkg install --global --platform "file://$SCRIPT_DIR"
else
    pio platform install "file://$SCRIPT_DIR"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Installation complete!                                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Your platformio.ini should use:"
echo ""
echo "  [env:chatter2]"
echo "  platform = circuitmess-esp32"
echo "  board = chatter2"
echo "  framework = arduino"
echo "  monitor_speed = 115200"
echo "  upload_port = /dev/ttyUSB0"
echo "  upload_speed = 115200"
echo "  board_build.partitions = no_ota.csv"
echo ""
echo "Toolchain (xtensa-esp32 GCC 5.2.0) will be downloaded"
echo "automatically on first build."
echo ""
