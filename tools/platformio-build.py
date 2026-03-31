# Copyright 2014-present PlatformIO <contact@platformio.org>
# Adapted for CircuitMess Arduino-ESP32 v1.8.3 fork
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Arduino framework build script for CircuitMess Arduino-ESP32 v1.8.3 fork.

This script configures the PlatformIO build environment to compile against
the CircuitMess Arduino-ESP32 framework, including:
  - ESP-IDF 3.x precompiled SDK libraries
  - Arduino core (cores/esp32)
  - Board variant (variants/<board>)
  - Partition tables
"""

import os
import sys
from os.path import isdir, isfile, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()

FRAMEWORK_DIR = platform.get_package_dir("framework-arduinoespressif32-cm")
assert isdir(FRAMEWORK_DIR)

board = env.BoardConfig()
build_mcu = board.get("build.mcu", "esp32")
variant = board.get("build.variant", "esp32")

# ---------------------------------------------------------------------------
# Locate SDK directories
# ---------------------------------------------------------------------------
# CircuitMess fork structure:
#   tools/sdk/include/<component>/   — ESP-IDF headers
#   tools/sdk/lib/                   — precompiled .a libraries
#   tools/sdk/ld/                    — linker scripts
#   cores/esp32/                     — Arduino core sources

SDK_DIR = join(FRAMEWORK_DIR, "tools", "sdk")

# Enumerate all subdirectories under tools/sdk/include/ for CPPPATH
sdk_include_base = join(SDK_DIR, "include")
sdk_include_dirs = []
if isdir(sdk_include_base):
    for d in sorted(os.listdir(sdk_include_base)):
        component_dir = join(sdk_include_base, d)
        if isdir(component_dir):
            sdk_include_dirs.append(component_dir)
            # Some components have a nested include/ dir
            nested = join(component_dir, "include")
            if isdir(nested):
                sdk_include_dirs.append(nested)

# Also check for tools/sdk/include directly (flat layout variant)
if not sdk_include_dirs and isdir(sdk_include_base):
    sdk_include_dirs.append(sdk_include_base)

# Enumerate precompiled .a libraries
sdk_lib_dir = join(SDK_DIR, "lib")
sdk_libs = []
if isdir(sdk_lib_dir):
    for f in sorted(os.listdir(sdk_lib_dir)):
        if f.endswith(".a"):
            # Strip "lib" prefix and ".a" suffix for linker
            name = f
            if name.startswith("lib"):
                name = name[3:]
            name = name[:-2]
            sdk_libs.append(name)

# ---------------------------------------------------------------------------
# Partition table
# ---------------------------------------------------------------------------
# Resolve partition table CSV:
#   1. User-specified in platformio.ini via board_build.partitions
#   2. Default from the framework's tools/partitions/ directory

partitions_csv = board.get("build.partitions", "default.csv")
# If it's a bare filename (not absolute), look in the framework's partitions dir
if not os.path.isabs(partitions_csv) and not isfile(partitions_csv):
    framework_partitions = join(FRAMEWORK_DIR, "tools", "partitions", partitions_csv)
    if isfile(framework_partitions):
        partitions_csv = framework_partitions

env.Replace(PARTITIONS_TABLE_CSV=partitions_csv)

# ---------------------------------------------------------------------------
# Linker script resolution
# ---------------------------------------------------------------------------

ld_dir = join(SDK_DIR, "ld")
ldscript = board.get("build.arduino.ldscript", "esp32_out.ld")

# ---------------------------------------------------------------------------
# Build flags
# ---------------------------------------------------------------------------

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],

    CFLAGS=[
        "-std=gnu99",
        "-Wno-old-style-declaration"
    ],

    CCFLAGS=[
        "-Os",
        "-g3",
        "-Wall",
        "-nostdlib",
        "-Wpointer-arith",
        "-Wno-error=unused-but-set-variable",
        "-Wno-error=unused-variable",
        "-mlongcalls",
        "-ffunction-sections",
        "-fdata-sections",
        "-fstrict-volatile-bitfields",
        "-Wno-error=deprecated-declarations",
        "-Wno-error=unused-function",
        "-Wno-unused-parameter",
        "-Wno-sign-compare",
        "-fstack-protector",
        "-fexceptions",
        "-Wreorder"
    ],

    CXXFLAGS=[
        "-fno-rtti",
        "-fno-exceptions",
        "-std=gnu++14"
    ],

    CPPDEFINES=[
        "ESP32",
        "ESP_PLATFORM",
        ("F_CPU", "$BOARD_F_CPU"),
        "HAVE_CONFIG_H",
        ("ARDUINO", 10812),
        ("ARDUINO_VARIANT", '\\"%s\\"' % variant),
        ("ARDUINO_BOARD", '\\"%s\\"' % board.get("name", "").replace('"', "")),
        "ARDUINO_ARCH_ESP32",
        "ESP_PLATFORM",
        ("MBEDTLS_CONFIG_FILE", '\\"mbedtls/esp_config.h\\"'),
        "HAVE_CONFIG_H",
        ("GCC_NOT_5_2_0", 0),
        "WITH_POSIX",
        "_GNU_SOURCE",
        ("IDF_VER", '\\"v3.3.5-1-g85c43024c\\"'),
    ],

    CPPPATH=[
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "config"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "app_trace"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "app_update"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "asio"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "bootloader_support"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "bt"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "coap"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "console"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "driver"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "efuse"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp-tls"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp32"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_adc_cal"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_event"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_http_client"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_http_server"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_https_ota"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_https_server"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_ringbuf"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp_websocket_client"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "ethernet"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "expat"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "fatfs"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "freemodbus"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "freertos"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "heap"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "idf_test"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "jsmn"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "json"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "libsodium"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "log"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "lwip"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "mbedtls"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "mdns"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "micro-ecc"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "mqtt"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "newlib"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "nghttp"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "nvs_flash"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "openssl"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "protobuf-c"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "protocomm"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "pthread"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "sdmmc"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "smartconfig_ack"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "soc"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "spi_flash"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "spiffs"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "tcp_transport"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "tcpip_adapter"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "ulp"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "unity"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "vfs"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "wear_levelling"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "wifi_provisioning"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "wpa_supplicant"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "xtensa-debug-module"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp-face"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp32-camera"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "esp-face"),
        join(FRAMEWORK_DIR, "tools", "sdk", "include", "fb_gfx"),
        join(FRAMEWORK_DIR, "cores", "esp32"),
        join(FRAMEWORK_DIR, "variants", variant),
    ],

    LIBPATH=[
        join(SDK_DIR, "lib"),
        join(SDK_DIR, "ld"),
    ],

    LIBS=sdk_libs + [
        "stdc++", "gcc", "m", "c", "pthread",
    ],

    LIBSOURCE_DIRS=[
        join(FRAMEWORK_DIR, "libraries"),
    ],

    LINKFLAGS=[
        "-nostdlib",
        "-Wl,-static",
        "-u", "call_user_start_cpu0",
        "-u", "ld_include_panic_highint_hdl",
        "-u", "esp_app_desc",
        "-Wl,--undefined=uxTopUsedPriority",
        "-Wl,--gc-sections",
        "-Wl,--noinhibit-exec",
        "-Wl,--no-check-sections",
        "-Wl,--start-group",
        "-Wl,-EL",
        "-Wl,--no-check-sections",
        "-T", "esp32_out.ld",
        "-T", "esp32.common.ld",
        "-T", "esp32.rom.ld",
        "-T", "esp32.peripherals.ld",
        "-T", "esp32.rom.libgcc.ld",
        "-T", "esp32.rom.spiram_incompatible_fns.ld",
        "-u", "__cxa_guard_dummy",
        "-u", "__cxx_fatal_exception",
    ],

    FLASH_EXTRA_IMAGES=[
        ("0x1000", join(FRAMEWORK_DIR, "tools", "sdk", "bin", "bootloader_dio_40m.bin")),
        ("0x8000", join(env.subst("$BUILD_DIR"), "partitions.bin")),
        ("0xe000", join(FRAMEWORK_DIR, "tools", "partitions", "boot_app0.bin")),
    ],
)

# ---------------------------------------------------------------------------
# Dynamic: scan SDK include dirs that actually exist
# ---------------------------------------------------------------------------
# The static CPPPATH list above covers the standard Arduino-ESP32 1.0.x layout.
# For safety, also add any directories that exist but might have been missed:
for inc_dir in sdk_include_dirs:
    if inc_dir not in env["CPPPATH"]:
        env.Append(CPPPATH=[inc_dir])

# ---------------------------------------------------------------------------
# Bootloader binary selection based on flash mode/speed
# ---------------------------------------------------------------------------
flash_mode = board.get("build.flash_mode", "dio")
f_flash = board.get("build.f_flash", "40000000L")
flash_freq = str(int(f_flash.replace("L", "")) // 1000000)

bootloader_name = "bootloader_%s_%sm.bin" % (flash_mode, flash_freq)
bootloader_path = join(FRAMEWORK_DIR, "tools", "sdk", "bin", bootloader_name)
if isfile(bootloader_path):
    env["FLASH_EXTRA_IMAGES"][0] = ("0x1000", bootloader_path)

# ---------------------------------------------------------------------------
# Build the partition table from CSV
# ---------------------------------------------------------------------------
partition_table = env.Command(
    join("$BUILD_DIR", "partitions.bin"),
    "$PARTITIONS_TABLE_CSV",
    env.VerboseAction(
        '"$PYTHONEXE" "%s" -q $SOURCE $TARGET'
        % join(FRAMEWORK_DIR, "tools", "gen_esp32part.py"),
        "Generating partitions $TARGET",
    ),
)
env.Depends("$BUILD_DIR/$PROGNAME$PROGSUFFIX", partition_table)

# ---------------------------------------------------------------------------
# Build the Arduino core library
# ---------------------------------------------------------------------------

# Source filter: compile everything in cores/esp32/
# except libb64 files which are sometimes already in the SDK
src_filter = ["+<*>", "-<.git/>", "-<.svn/>"]

env.BuildSources(
    join("$BUILD_DIR", "FrameworkArduino"),
    join(FRAMEWORK_DIR, "cores", "esp32"),
)
