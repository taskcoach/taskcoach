# TaskCoach AppImage Build System

This document describes the GitHub Actions workflow and local build script for creating TaskCoach AppImage packages.

## Overview

The AppImage build system creates a portable, self-contained Linux executable that bundles:
- Python 3.11 interpreter
- All Python dependencies (wxPython, etc.)
- Required shared libraries (libjpeg, libpng, etc.)
- TaskCoach application code

The resulting AppImage runs on most Linux distributions with glibc 2.28+ (Debian Bookworm, Ubuntu 22.04+, Fedora 37+, etc.).

## How It Works

### 1. Base Image
Uses pre-built Python AppImages from [python-appimage](https://github.com/niess/python-appimage) project. These provide a complete Python environment built against `manylinux_2_28` for broad compatibility.

### 2. Dependency Installation
Installs wxPython and all TaskCoach dependencies using pip:
- wxPython is installed from the [wxPython extras repository](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04) for pre-built wheels
- Other dependencies from PyPI

### 3. Library Bundling
Copies system libraries that wxPython needs but aren't included in the Python AppImage:
- `libjpeg.so.8` - JPEG image support
- `libpng16.so.16` - PNG image support
- `libtiff.so.5` - TIFF image support
- `libwebp.so.7` - WebP image support
- `libSDL2-2.0.so.0` - SDL2 for multimedia

### 4. Custom AppRun
Creates a launcher script that:
- Sets `PYTHONHOME` to the bundled Python
- Configures `PYTHONPATH` to include TaskCoach
- Sets `LD_LIBRARY_PATH` to find bundled libraries
- Launches `taskcoach.py`

### 5. Packaging
Uses `appimagetool` to compress everything into a single executable `.AppImage` file.

## Files

### GitHub Actions Workflow
`.github/workflows/build-appimage.yml`

Triggers:
- Push to `main`, `master`, or `claude/**` branches
- Push of tags matching `v*`
- Pull requests to `main` or `master`
- Manual workflow dispatch

Jobs:
1. **build-appimage**: Builds the AppImage on Ubuntu 22.04
2. **test-appimage**: Tests on Debian Bookworm, Ubuntu 22.04/24.04, Fedora 39

### Local Build Script
`scripts/build-appimage.sh`

For building locally on Debian Bookworm or similar systems:
```bash
./scripts/build-appimage.sh
```

Requires: `wget`, `file`, `patchelf`, and optionally `libfuse2`

## Creating a Release

1. Update version in `taskcoachlib/meta/data.py`:
   ```python
   version_patch = "52"  # Increment this
   ```

2. Commit and push changes

3. Create and push a tag:
   ```bash
   git tag v1.6.1.52
   git push origin v1.6.1.52
   ```

4. GitHub Actions will automatically:
   - Build the AppImage
   - Create a GitHub Release
   - Attach the AppImage as a release asset

## Troubleshooting

### Missing shared libraries
If the AppImage fails with "cannot open shared object file", the library needs to be added to the `LIBS_TO_BUNDLE` list in the workflow.

### Python path issues
The AppRun script sets up the environment. Key variables:
- `PYTHONHOME`: Points to bundled Python in `opt/python3.11`
- `PYTHONPATH`: Includes TaskCoach source and site-packages
- `LD_LIBRARY_PATH`: Includes bundled libraries in `usr/lib`

### YAML heredoc issues
GitHub Actions YAML has issues with heredocs that start at column 0. Use `echo` statements or `printf` instead.

### AppRun symlink
The python-appimage's AppRun is a symlink. Must remove it before creating custom AppRun, otherwise writing goes to the symlink target.

## Architecture Notes

### python-appimage Structure
```
TaskCoach.AppDir/
├── AppRun              # Custom launcher script
├── taskcoach.desktop   # Desktop entry
├── taskcoach.png       # App icon
├── opt/
│   └── python3.11/     # Bundled Python
│       ├── bin/
│       │   └── python3.11  # Actual Python binary
│       └── lib/
│           └── python3.11/
│               └── site-packages/  # Installed packages
└── usr/
    ├── lib/            # Bundled shared libraries
    └── share/
        └── taskcoach/  # TaskCoach source code
            ├── taskcoach.py
            └── taskcoachlib/
```

### Why not use the original AppRun?
The python-appimage's AppRun/wrapper scripts construct paths dynamically. When you set `PYTHONHOME` externally, they get confused and create doubled paths like `/usr/bin/opt/python3.11/bin/python3.11`. Using the actual Python binary directly with proper environment variables is more reliable.
