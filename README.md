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
│   └── platformio.ini         # Ready-to-use Chatter 2.0 project config
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
lib_ldf_mode = deep+
build_unflags = -Os -std=gnu++14

board_build.partitions = no_ota.csv
board_build.flash_mode = dio
board_build.f_flash = 80000000L
board_build.f_cpu = 240000000L

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
    -Wno-error=reorder
    -std=gnu++17
    -DARDUINO_CM_CHATTER
    -DCORE_DEBUG_LEVEL=0
    -O2
```

See `examples/platformio.ini` for a complete working config including `lib_ignore`.

## Critical: Display Configuration (ST7735S White Screen Fix)

> **If you're here because your Chatter 2.0 display stays white under PlatformIO
> while working fine in Arduino IDE — this section is for you.**

The CircuitMess framework ships **two** Chatter libraries side by side:

| Library | Header | Used by | Display init |
|---|---|---|---|
| `Chatter-Library` | `<Chatter.h>` | Arduino IDE | Calls `setPanel(panel1())` with hardcoded SPI config **before** `display->begin()` |
| `Chatter2-Library` | `<Chatter2.h>` | (PIO default) | Calls `display->begin()` directly, relying on `-DLOVYAN_*` build flags |

Both expose a global `Chatter` object with the same API. The difference is entirely
in how they initialize the display panel.

### The problem

`Chatter2-Library` configures the ST7735S panel via LovyanGFX build flags
(`-DLOVYAN_*`), but the constructor in `LovyanGFX_setup.h` uses default values
that **don't match the Chatter 2.0 hardware**:

| Setting | `Chatter-Library` panel1() (working) | `LovyanGFX_setup.h` default (broken) |
|---|---|---|
| `offset_rotation` | **2** | 0 |
| `readable` | **false** | true |
| `bus_shared` | **false** | true |

With `offset_rotation = 0`, the display controller maps its framebuffer to
physical pixels incorrectly — writes go to memory addresses outside the visible
area, and you see an unwritten (white) screen.

### The fix (two parts)

**1. Use `Chatter-Library` instead of `Chatter2-Library`.**

In your `main.cpp`:
```cpp
#include <Chatter.h>    // NOT <Chatter2.h>
```

In your `platformio.ini` `lib_ignore` section, block `Chatter2-Library`
(not `Chatter-Library`):
```ini
lib_ignore =
    ...
    Chatter2-Library
    ...
```

This gives PIO the same init path as Arduino IDE: `setPanel(panel1())` is called
with the correct hardcoded config before `display->begin()`.

**2. Patch `LovyanGFX_setup.h` in your local `lib/CircuitOS/`.**

If you have a local copy of CircuitOS in your project's `lib/` directory,
find `src/Display/LovyanGFX_setup.h` and change the panel config section:

```cpp
cfg.offset_rotation = 2;    // was 0
cfg.readable = false;        // was true
cfg.bus_shared = false;      // was true
```

This ensures the LGFX constructor has the correct values regardless of which
library's init path runs.

### What we ruled out (so you don't have to)

Over ~7 hours of debugging, these hypotheses were **definitively eliminated**:

- **Wrong bootloader/flash layout** — flashing Arduino IDE's .bin at 0x10000 over PIO's bootloader worked fine
- **Wrong framework/toolchain** — same GCC 5.2.0, same CM fork (symlinked)
- **Flash frequency** — matched to 80MHz, no effect
- **Compile flag differences** — `-O2`/`-Os`, `-std=gnu++14`/`gnu++17`, board defines all tested, no effect
- **Arduino core (`core.a`) compilation** — swapped Arduino IDE's precompiled `core.a` into PIO build, still white
- **LovyanGFX platform objects** — swapped all 6 Arduino IDE `.o` files into PIO build, still white
- **SPI peripheral misconfiguration** — register dump post-init showed correct values for GPIO matrix, DMA channel, SPI clock
- **`__has_include(<SPI.h>)` failing** — diagnostic confirmed SPI HAL path active
- **Post-init `setPanel()` + `init()`** — calling `tft->setPanel()` and `tft->init()` after `Chatter.begin()` did not recover; the first `display->begin()` with wrong config leaves the display in an unrecoverable state

The root cause is specifically that `Chatter2-Library` calls `display->begin()`
without first calling `setPanel()` with the hardware-correct panel configuration,
and `LovyanGFX_setup.h` defaults don't match the Chatter 2.0's ST7735S.

## Project Structure

Your PlatformIO project should look like this:

```
your-project/
├── platformio.ini
├── src/
│   └── main.cpp              # #include <Chatter.h> (NOT Chatter2.h)
├── lib/
│   ├── CircuitOS/            # Patched: LovyanGFX_setup.h with correct panel values
│   ├── LovyanGFX/
│   └── RadioLib/
```

`Chatter-Library` is **not** in `lib/` — it comes from the framework
(`~/.arduino15/packages/cm/hardware/esp32/1.8.3/libraries/Chatter-Library/`).
The `lib_ignore` list in `platformio.ini` blocks `Chatter2-Library` and all
other unneeded CM libraries to prevent conflicts and speed up builds.

## Chatter 2.0 Hardware Reference

| Component | Detail |
|---|---|
| MCU | ESP32-D0WD rev v1.1, 4MB flash, DIO, 80MHz flash clock |
| Display | ST7735S 160×128 color TFT (landscape) |
| Display SPI | VSPI: MOSI=26, SCK=27, DC=33, RST=15, CS=-1 |
| Backlight | GPIO 32 (PWM, active-low: 0=bright, 255=off) |
| Input | 74HC165 shift register: DATA=23, CLK=22, LOAD=21 |
| Radio | SX1262 (LLCC68) LoRa on HSPI |
| Buzzer | Piezo on GPIO 19 (LEDC ch 0) |
| Serial | /dev/ttyUSB0, 115200 baud |

## Troubleshooting

### Display stays white

See [Critical: Display Configuration](#critical-display-configuration-st7735s-white-screen-fix) above. The two most common causes:

1. Your code includes `<Chatter2.h>` instead of `<Chatter.h>`
2. Your `lib_ignore` blocks `Chatter-Library` instead of `Chatter2-Library`

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

### Missing include directories

The `platformio-build.py` enumerates SDK includes from `tools/sdk/include/`.
If you get missing header errors, check what actually exists:

```bash
ls ~/.arduino15/packages/cm/hardware/esp32/1.8.3/tools/sdk/include/
```

And compare against the CPPPATH list in `tools/platformio-build.py`.

### Comparing builds

If something else is wrong, compare PIO and Arduino IDE builds:

```bash
# Arduino IDE build (known-good)
arduino-cli compile --fqbn cm:esp32:chatter2 --build-path /tmp/arduino-build .

# Compare sections
xtensa-esp32-elf-size /tmp/arduino-build/*.elf
xtensa-esp32-elf-size .pio/build/chatter2/firmware.elf
```

Check that `.text` and `.rodata` sizes are in the same ballpark — if the PIO
build is dramatically larger or smaller, the wrong SDK libs are being linked.

## License

Platform scaffolding: Apache-2.0 (based on platformio/platform-espressif32 v3.5.0)
CircuitMess Arduino-ESP32 fork: LGPL-2.1 (upstream)
