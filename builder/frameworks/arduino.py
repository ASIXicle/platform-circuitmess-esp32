# Copyright 2014-present PlatformIO <contact@platformio.org>
# Modifications for CircuitMess ESP32 platform
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0

"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.

http://arduino.cc/en/Reference/HomePage
"""

from os.path import join

from SCons.Script import DefaultEnvironment, SConscript

env = DefaultEnvironment()

SConscript("_embed_files.py", exports="env")

SConscript(
    join(DefaultEnvironment().PioPlatform().get_package_dir(
        "framework-arduinoespressif32-cm"), "tools", "platformio-build.py"))
