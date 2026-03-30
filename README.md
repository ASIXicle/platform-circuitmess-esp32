# platform-circuitmess-esp32

Custom PlatformIO platform for CircuitMess ESP32 devices (Chatter 2.0, etc.)
using the CircuitMess Arduino-ESP32 v1.8.3 fork with its ESP-IDF 3.x runtime.

## Why This Exists

PlatformIO's stock `espressif32` platform ships Arduino-ESP32 v2.0.17 (ESP-IDF 4.4+).
CircuitMess's fork is based on Arduino-ESP32 v1.0.x (ESP-IDF 3.x). The display
initialization in LovyanGFX v0.4.1 depends on ESP-IDF 3.x SPI/GPIO behavior — under
ESP-IDF 4.4+, the ST7735S display stays permanently white regardless of pin
configuration, init sequence, or bootloader choice.

**The problem is the compiled ESP-IDF runtime linked at build time**, not pins, not
init sequences, not the bootloader.

This platform solves the problem by wrapping the exact CircuitMess Arduino-ESP32
fork (with its ESP-IDF 3.x precompiled libraries) as a proper PlatformIO platform.

## Architecture

```
platform-circuitmess-esp32/
├── platform.json          # Manifest: declares framework + toolchain packages
├── platform.py            # Platform config class (package resolution)
├── boards/
│   └── chatter2.json      # Board def: ESP32-D0WD, 4MB, 240MHz, DIO
├── builder/
│   ├── main.py            # SCons build script (upload, erase, elf→bin)
│   ├── compat.py          # PIO Core backward compat shim
│   └── frameworks/
│       ├── arduino.py     # Delegates to framework's platformio-build.py
│       └── _embed_files.py
├── tools/
│   ├── platformio-build.py    # ← injected into CM fork tools/ dir
│   └── framework-package.json # ← injected into CM fork root as package.json
├── examples/
│   └── platformio.ini         # Ready-to-use CrowS project config
└── install.sh                 # Automated setup script
```

**Key package mapping:**

| PlatformIO Package | Source | Version |
|---|---|---|
| `framework-arduinoespressif32-cm` | Symlink to `~/.arduino15/packages/cm/hardware/esp32/1.8.3/` | 1.8.3 |
| `toolchain-xtensa32` | PlatformIO registry (auto-downloaded) | ~2.50200.0 (GCC 5.2.0) |
| `tool-esptoolpy` | PlatformIO registry (auto-downloaded) | ~1.30100.0 |

The GCC 5.2.0 toolchain (`1.22.0-80-g6c4433a-5.2.0`) is the **exact same version**
CircuitMess specifies in their Arduino board package index.

## Prerequisites

1. **CircuitMess board package** installed in Arduino IDE:
   - Board Manager URL: `https://raw.githubusercontent.com/CircuitMess/Arduino-Packages/master/package_circuitmess.com_esp32_index.json`
   - Or via `arduino-cli core install cm:esp32`

2. **PlatformIO CLI** available (`pio` command)

## Installation

```bash
git clone https://github.com/ASIXicle/platform-circuitmess-esp32.git
cd platform-circuitmess-esp32
./install.sh
```

The install script:
1. Verifies CM framework exists at `~/.arduino15/packages/cm/hardware/esp32/1.8.3/`
2. Symlinks it into `~/.platformio/packages/framework-arduinoespressif32-cm/`
3. Injects `platformio-build.py` and `package.json` (non-destructive, skips if present)
4. Registers the platform with PlatformIO

### Manual Installation

If you prefer to do it by hand:

```bash
# 1. Symlink the framework
ln -s ~/.arduino15/packages/cm/hardware/esp32/1.8.3 \
      ~/.platformio/packages/framework-arduinoespressif32-cm

# 2. Inject build files
cp tools/framework-package.json ~/.arduino15/packages/cm/hardware/esp32/1.8.3/package.json
cp tools/platformio-build.py    ~/.arduino15/packages/cm/hardware/esp32/1.8.3/tools/platformio-build.py

# 3. Install platform
pio pkg install --global --platform "file://$(pwd)"
```

## Usage

In your `platformio.ini`:

```ini
[env:chatter2]
platform = circuitmess-esp32
board = chatter2
framework = arduino
monitor_speed = 115200
upload_port = /dev/ttyUSB0
upload_speed = 115200
board_build.partitions = no_ota.csv

build_flags =
    -DCONFIG_ARDUINO_LOOP_STACK_SIZE=14000
    -DCIRCUITOS_FREERTOS
    -DCIRCUITOS_NVS
    -DCIRCUITOS_PIEZO_PWM
    -DCIRCUITOS_PIEZO_PWM_CHANNEL=15
    -DCIRCUITOS_LOVYANGFX
    -DLOVYAN_PANEL=Panel_ST7735S
    -DLOVYAN_FREQ=27000000
    -DLOVYAN_WIDTH=128
    -DLOVYAN_HEIGHT=160
    -DLOVYAN_MISO=-1
    -DLOVYAN_MOSI=26
    -DLOVYAN_SCK=27
    -DLOVYAN_CS=-1
    -DLOVYAN_DC=33
    -DLOVYAN_RST=15
    -DRADIOLIB_GODMODE
    -DLV_FONT_MONTSERRAT_8=1
    -DLV_FONT_MONTSERRAT_14=1
    -DLV_FONT_MONTSERRAT_10=1
    -DLV_FONT_UNSCII_8=1
    -DLV_USE_GIF=1
```

Libraries go in `lib/` as before:
```
CrowS-PIO/
├── platformio.ini
├── src/
│   └── main.cpp
├── lib/
│   ├── Chatter2-Library/
│   ├── CircuitOS/
│   ├── LovyanGFX/
│   └── RadioLib/
```

## Troubleshooting

### "Missing SConscript file platformio-build.py"
The `platformio-build.py` didn't get injected into the framework. Run:
```bash
cp tools/platformio-build.py ~/.arduino15/packages/cm/hardware/esp32/1.8.3/tools/
```

### Toolchain not found
PlatformIO should auto-download `toolchain-xtensa32` v2.50200.0 on first build.
If it doesn't, force it:
```bash
pio pkg install --global --tool "platformio/toolchain-xtensa32@~2.50200.0"
```

### Display still white
If the display stays white after building with this platform, compare the binary
output against an Arduino IDE build:
```bash
# Arduino IDE build (known-good)
arduino-cli compile --fqbn cm:esp32:chatter2 --build-path /tmp/arduino-build .

# Compare sections
xtensa-esp32-elf-size /tmp/arduino-build/*.elf
xtensa-esp32-elf-size .pio/build/chatter2/firmware.elf
```

Check that the `.text` and `.rodata` sizes are in the same ballpark — if the PIO
build is dramatically larger or smaller, the wrong SDK libs are being linked.

### Missing include directories
The `platformio-build.py` enumerates SDK includes from `tools/sdk/include/`.
If you get missing header errors, check what actually exists:
```bash
ls ~/.arduino15/packages/cm/hardware/esp32/1.8.3/tools/sdk/include/
```
And compare against the CPPPATH list in `tools/platformio-build.py`.

## License

Platform scaffolding: Apache-2.0 (based on platformio/platform-espressif32 v3.5.0)
CircuitMess Arduino-ESP32 fork: LGPL-2.1 (upstream)
CrowS project: MIT
