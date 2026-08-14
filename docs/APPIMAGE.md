# AppImage Packaging for Task Coach

- **AppImage:** [python-appimage](https://github.com/niess/python-appimage) | [wxPython extras](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04) | [AppImage docs](https://docs.appimage.org/)
- **Project files:** [`build-appimage.yml`](../.github/workflows/build-appimage.yml)

The AppImage build system creates a portable, self-contained Linux executable that bundles Python, wxPython, and all dependencies into a single file.

## What's Included

| Component | Version | Source |
|-----------|---------|--------|
| Python | 3.11.x (latest from the python3.11 release tag, resolved at build time) | python-appimage (manylinux_2_28) |
| wxPython | 4.2.2 (pinned, newest cp311 wheel in extras) | wxPython extras (Ubuntu 22.04) |
| wxWidgets | 3.2.6 | Bundled with wxPython |
| Image libs | libjpeg, libpng, libtiff, libjbig, libwebp | Copied from build system |

The resulting AppImage runs on most Linux distributions with glibc 2.28+ (Debian Bookworm, Ubuntu 22.04+, Fedora 40+).

## Bundled Libraries

The AppImage bundles specific shared libraries to ensure compatibility across distributions. These are copied from the Ubuntu 22.04 build system into `usr/lib/` inside the AppImage.

### Why Bundle Libraries?

Different distributions ship different library versions with incompatible ABIs:

| Library | Ubuntu 22.04 | Fedora 43 | Issue |
|---------|--------------|-----------|-------|
| libjbig | libjbig.so.0 | libjbig.so.2.1 | ABI break |
| libtiff | libtiff.so.5 | libtiff.so.6 | ABI break |
| libwebp | libwebp.so.7 | libwebp.so.7 | Compatible |

By bundling these libraries, the AppImage works on both old and new distributions.

### Currently Bundled

```
LIBS_TO_BUNDLE=(
  libjpeg.so.8      # JPEG image support
  libpng16.so.16    # PNG image support
  libtiff.so.5      # TIFF image support
  libjbig.so.0      # JBIG compression (required by libtiff)
  libwebp.so.7      # WebP image support
  libSDL2-2.0.so.0  # SDL2 (optional, for some wx features)
)
```

### How Library Loading Works

The AppRun script sets `LD_LIBRARY_PATH` to prioritize bundled libraries:

```bash
export LD_LIBRARY_PATH="$PYTHONHOME/lib:$APPDIR/usr/lib:$LD_LIBRARY_PATH"
```

This means:
1. Bundled libraries in `$APPDIR/usr/lib/` are found first
2. If a bundled library exists, it's used instead of the system version
3. System libraries are used as fallback for non-bundled dependencies

### Adding New Libraries

If users report "cannot open shared object file" errors on specific distributions:

1. Identify the missing library from the error message
2. Add it to `LIBS_TO_BUNDLE` in `.github/workflows/build-appimage.yml`
3. The library will be copied from Ubuntu 22.04 during the build

## Design Decisions

### Why Python 3.11 (not 3.12 or 3.13)?

| Factor | Python 3.11 | Python 3.12/3.13 |
|--------|-------------|------------------|
| wxPython wheels | Pre-built available | May require compilation |
| Stability | Mature, well-tested | Newer, less tested with wx |
| Compatibility | Broad library support | Some packages may lag |

**Primary reason:** The wxPython extras repository provides pre-built wheels for Python 3.11 on Ubuntu 22.04 (the build platform). Using pre-built wheels:
- Avoids lengthy compilation during CI builds
- Ensures consistent, tested binaries
- Reduces build failures

**Future consideration:** When wxPython wheels are reliably available for Python 3.12+, upgrading is straightforward - just change the URL in `build-appimage.yml`.

### Why wxPython is pinned to 4.2.2

The wxPython extras repository for Ubuntu 22.04 provides cp311 wheels only up to 4.2.2, and PyPI ships no Linux wheels at all. An unpinned `pip install wxPython` therefore resolves to the newest PyPI sdist (4.3+) and tries to compile wxWidgets from source, which fails on the bundled AppImage Python (no python-config or headers) after several minutes. The build pins `wxPython==4.2.2` with `--only-binary wxPython` so it always installs the pre-built wheel and fails fast if that wheel ever disappears. To upgrade wxPython, check the extras repository for a newer cp311 wheel first and bump the pin.

### Why manylinux_2_28?

The Python AppImage is built on a `manylinux_2_28` base (CentOS/RHEL with glibc 2.28). This ensures compatibility with older distributions. The "(Red Hat 14.2.1-7)" in the Python version string refers to the GCC version used to compile Python on the manylinux build system.

### Bundled vs System Libraries

| Component | Bundled | System |
|-----------|:-------:|:------:|
| Python interpreter | ✓ | |
| wxPython/wxWidgets | ✓ | |
| Image libraries | ✓ | |
| GTK 3 | | ✓ |
| Graphics drivers | | ✓ |
| Fonts | | ✓ |
| glibc | | ✓ |

**Note:** GTK is NOT bundled because it's tightly integrated with the display server, themes, and graphics stack. This means GTK-related issues may still be system-specific.

## How It Works

1. **Base Image** - Downloads pre-built Python AppImage from python-appimage project
2. **Dependencies** - Installs wxPython from extras repository and other deps from PyPI
3. **Library Bundling** - Copies required shared libraries (libjpeg, libpng, libtiff, libjbig, etc.)
4. **Custom AppRun** - Creates launcher script setting PYTHONHOME, PYTHONPATH, LD_LIBRARY_PATH
5. **Packaging** - Uses `appimagetool` to create the final `.AppImage` file

## Directory Structure

```
TaskCoach.AppDir/
├── AppRun              # Custom launcher script
├── taskcoach.desktop   # Desktop entry
├── taskcoach.png       # App icon
├── opt/
│   └── python3.11/     # Bundled Python
│       ├── bin/python3.11
│       └── lib/python3.11/site-packages/
└── usr/
    ├── lib/            # Bundled shared libraries
    │   ├── libjpeg.so.8
    │   ├── libpng16.so.16
    │   ├── libtiff.so.5
    │   ├── libjbig.so.0
    │   └── libwebp.so.7
    └── share/taskcoach/
        ├── taskcoach.py
        └── taskcoachlib/
```

## Building

### Local Build

```bash
./scripts/build-appimage.sh
```

Requires: `wget`, `file`, `patchelf`, and optionally `libfuse2`

### GitHub Actions

The workflow builds automatically on:
- Push to main/master
- Version tags (v*)
- Pull requests

Tests run on Debian Bookworm, Ubuntu 22.04/24.04, and Fedora 43.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "cannot open shared object file: libXXX.so" | Add library to `LIBS_TO_BUNDLE` in workflow |
| Python path issues | Check PYTHONHOME, PYTHONPATH, LD_LIBRARY_PATH in AppRun |
| YAML heredoc issues | Use `echo` statements instead of heredocs in workflow |
| AppRun symlink | Remove original symlink before creating custom AppRun |
| GTK theme issues | System-specific, try different GTK theme |
| Wayland issues | Try running with `GDK_BACKEND=x11` |

### Common Library Issues by Distribution

| Distribution | Potential Issues | Solution |
|--------------|------------------|----------|
| Fedora 43+ | libjbig.so.0 missing | Bundled in AppImage |
| Arch Linux | Various library versions | Usually works with bundled libs |
| Debian Bookworm | None known | Works out of the box |
| Ubuntu 22.04+ | None known | Works out of the box |

## Minimum Requirements

- **glibc**: 2.28 or newer
- **GTK**: 3.x (system)
- **X11 or Wayland**: Display server
- **libfuse2** (optional): For mounting AppImage without extraction

Distributions meeting these requirements:
- Debian 12 (Bookworm) and newer
- Ubuntu 22.04 and newer
- Fedora 40 and newer
- Arch Linux (rolling)
- Most distributions released after 2020
