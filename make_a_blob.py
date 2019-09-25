from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
buildOptions = dict(
    # Fix six, appdirs import bug
    packages = ["pkg_resources._vendor","win32ui","requests"],
    # Manual copy of files outside the package (MANIFEST.IN seems to be ignored ><)
    include_files = [("LICENSE", "lib/LICENSE"),
    ("cutevariant/", "lib/cutevariant/")

    ],
    optimize = 0,# lol
    include_msvcr = True,
	add_to_path = True
    )

import sys
# Use Console to have a console in the background
base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('cutevariant/__main__.py', base=base, targetName='cutevariant.exe', icon ="icon.ico")
]

setup(
    name='cutevariant',
    options = dict(build_exe = buildOptions),
    executables = executables
)
