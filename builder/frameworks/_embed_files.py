# Simplified _embed_files.py for CircuitMess ESP32 (Arduino-only, no ESP-IDF)

from os.path import basename, isfile, join
from SCons.Script import Builder

Import("env")

board = env.BoardConfig()


def extract_files(cppdefines, files_type):
    result = []
    files = env.GetProjectOption("board_build.%s" % files_type, "").splitlines()
    if files:
        result.extend([join("$PROJECT_DIR", f.strip()) for f in files if f])
    else:
        files_define = "COMPONENT_" + files_type.upper()
        for define in cppdefines:
            if files_define not in define:
                continue
            value = define[1]
            if not isinstance(define, tuple):
                return []
            if not isinstance(value, str):
                return []
            for f in value.split(":"):
                if f:
                    result.append(join("$PROJECT_DIR", f))
    return result


def remove_config_define(cppdefines, files_type):
    for define in cppdefines:
        if files_type in define:
            env.ProcessUnFlags("-D%s" % "=".join(str(d) for d in define))
            return


env.Append(
    BUILDERS=dict(
        TxtToBin=Builder(
            action=env.VerboseAction(
                " ".join([
                    "xtensa-esp32-elf-objcopy",
                    "--input-target", "binary",
                    "--output-target", "elf32-xtensa-le",
                    "--binary-architecture", "xtensa",
                    "--rename-section", ".data=.rodata.embedded",
                    "$SOURCE", "$TARGET",
                ]),
                "Converting $TARGET",
            ),
            suffix=".txt.o",
        ),
    )
)


def embed_files(files, files_type):
    import shutil
    from os import SEEK_CUR, SEEK_END

    for f in files:
        filename = basename(f) + ".txt.o"
        file_target = env.TxtToBin(join("$BUILD_DIR", filename), f)
        env.Depends("$PIOMAINPROG", file_target)
        env.AppendUnique(PIOBUILDFILES=[env.File(join("$BUILD_DIR", filename))])


flags = env.get("CPPDEFINES")
for files_type in ("embed_txtfiles", "embed_files"):
    if (
        "COMPONENT_" + files_type.upper() not in env.Flatten(flags)
        and "build." + files_type not in board
    ):
        continue
    files = extract_files(flags, files_type)
    if files:
        embed_files(files, files_type)
        remove_config_define(flags, files_type)
