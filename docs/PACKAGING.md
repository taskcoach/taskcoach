# Packaging Guide for Task Coach

This document describes the packaging setup for Task Coach on Linux (Debian, Ubuntu, Linux Mint, Arch Linux, Manjaro, Fedora, AppImage), Windows, and macOS.

## Table of Contents

**Quick Reference**
- [Minimum Version Requirements](#minimum-version-requirements)
- [Install Overview by Build Target](#install-overview-by-build-target)
- [Build Scripts and Workflows](#build-scripts-and-workflows)

**Packaging by Platform**
- [Debian/Ubuntu Packaging](#debianubuntu-packaging)
- [Arch Linux / Manjaro Packaging](#arch-linux--manjaro-packaging)
- [Fedora Packaging](#fedora-packaging)
- [AppImage Packaging](#appimage-packaging)
- [Windows Packaging](#windows-packaging)
- [macOS Packaging](#macos-packaging)

**Appendix**
- [Dependency Installation Strategy](#dependency-installation-strategy)
- [Creating a Release](#creating-a-release)

## Minimum Version Requirements

| Package | Min Version | Why Required | Distros with Old Versions |
|---------|-------------|--------------|---------------------------|
| Python | >=3.8 | Type hints, f-strings, walrus operator | — |
| wxPython | >=4.2.0 | HyperTreeList stability | — |
| wxPython | >=4.2.4 | hypertreelist row background fix (PR #2088) | All current (Bookworm 4.2.0, Trixie 4.2.3) |
| pyparsing | >=3.1.3 | `pp.Tag()` API | Debian Bookworm (3.0.9) |
| watchdog | >=3.0.0 | File monitoring API | Debian Bookworm (2.2.1) |
| fasteners | >=0.19 | File locking API | — |

**Note**: wxPython 4.2.4 was released October 28, 2025 but is not yet packaged for any distro. Until then, a bundled patch in `taskcoachlib/patches/` is used (see [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md)).

## Install Overview by Build Target

This table shows how dependencies are handled in **built packages** and **setup scripts**.

| Package | debian12 | ubuntu22 | debian13 | ubuntu24 | arch | fedora | appimage | windows | macos |
|---------|:--------:|:--------:|:--------:|:--------:|:----:|:------:|:--------:|:-------:|:-----:|
| wxpython | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| pypubsub | distro | distro | distro | distro | AUR | distro | bundled | pip | pip |
| pyparsing | **pip** | **pip** | distro | distro | distro | **pip** | bundled | pip | pip |
| watchdog | **pip** | **pip** | distro | distro | distro | distro | bundled | pip | pip |
| squaremap | distro | distro | distro | distro | **pip** | **pip** | bundled | pip | pip |
| six | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| lxml | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| numpy | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| chardet | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| python-dateutil | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| keyring | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| pyxdg | distro | distro | distro | distro | distro | distro | bundled | — | — |
| fasteners | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| ayatana-appindicator | distro | distro | distro | distro | distro | distro | host | — | — |
| hypertreelist | **patch** | **patch** | **patch** | **patch** | **patch** | **patch** | bundled | **patch** | **patch** |
| WMI | — | — | — | — | — | — | — | pip | — |

**Key:**
- `distro` = Installed from distribution repos (required dependency)
- `pip` = Bundled via pip in package build (version too old or not in repos)
- `patch` = Bundled patch in `taskcoachlib/patches/` (wxPython hypertreelist fix)
- `bundled` = Bundled in package (thirdparty/ for .deb/.rpm, or inside AppImage)
- `host` = Uses host system library (AppImage); install on host for Wayland tray support
- `AUR` = Arch User Repository (rolling release)
- `—` = Not applicable for this platform

## Build Scripts and Workflows

| Target | ID | Python | wxPython | Setup Script | GitHub Workflow | Notes |
|--------|:--:|:------:|:--------:|--------------|-----------------|-------|
| [Debian 12 Bookworm](#debianubuntu-packaging) | debian12 | 3.11 | 4.2.0 | `setup_debian12_bookworm.sh` | `build-deb.yml` | pip: pyparsing, watchdog |
| [Debian 13 Trixie](#debianubuntu-packaging) | debian13 | 3.12 | 4.2.3 | `setup_debian13_trixie.sh` | `build-deb.yml` | Distro deps sufficient |
| [Ubuntu 22.04 Jammy](#debianubuntu-packaging) | ubuntu22 | 3.10 | 4.1.1 | `setup_ubuntu2204_jammy.sh` | `build-deb.yml` | pip: pyparsing, watchdog |
| [Ubuntu 24.04 Noble](#debianubuntu-packaging) | ubuntu24 | 3.12 | 4.2.1 | `setup_ubuntu2404_noble.sh` | `build-deb.yml` | Distro deps sufficient |
| [Arch Linux](#arch-linux--manjaro-packaging) | arch | latest | latest | `setup_arch.sh` | `build-arch.yml` | pip: squaremap; pypubsub from AUR |
| [Manjaro](#arch-linux--manjaro-packaging) | arch | latest | latest | `setup_arch.sh` | `build-arch.yml` | pip: squaremap; pypubsub from AUR |
| [Fedora 43](#fedora-packaging) | fedora43 | 3.13 | 4.2.2 | `setup_fedora.sh` | `build-rpm.yml` | pip: squaremap, pyparsing |
| [**AppImage**](#appimage-packaging) | appimage | **3.11** | **4.2.4** | — | `build-appimage.yml` | Bundles Python + all deps |
| [**Windows**](#windows-packaging) | windows | **3.11** | **4.2.x** | — | `build-windows.yml` | Python embed + Inno Setup |
| [**macOS**](#macos-packaging) | macos | **3.11** | **4.2.x** | — | `build-macos.yml` | py2app + DMG (Intel & ARM64) |

**AppImage note:** Uses Python 3.11 (not 3.12) for wxPython wheel availability. See [AppImage Packaging](#appimage-packaging) section for details.

**pip packages are bundled at build time** - users just install the package, no pip runs at install.

### Estimated Desktop User Base

| Distribution | Est. Desktop Users | % of Linux Desktop | Priority |
|--------------|-------------------:|-------------------:|:--------:|
| **Ubuntu** (all flavors) | 13-17 million | ~34% | High |
| **Debian** | 6-8 million | ~16% | High |
| **Linux Mint** | 4-6 million | ~10-12% | High |
| **Arch Linux** | 1.5-2.5 million | ~4-5% | Medium |
| **Manjaro** | 1-1.5 million | ~2-3% | Medium |
| **Fedora** | 0.8-1.2 million | ~2-3% | Medium |

*Sources: [StatCounter](https://gs.statcounter.com/os-market-share/desktop/worldwide/), [Steam Survey](https://store.steampowered.com/hwsurvey?platform=linux)*

---

## Debian/Ubuntu Packaging

- **Debian:** [New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/) | [Policy Manual](https://www.debian.org/doc/debian-policy/) | [Python Policy](https://www.debian.org/doc/packaging-manuals/python-policy/) | [Releases](https://en.wikipedia.org/wiki/Debian_version_history#Release_table)
- **Ubuntu:** [Packaging Guide](https://canonical-ubuntu-packaging-guide.readthedocs-hosted.com/) | [Releases](https://en.wikipedia.org/wiki/Ubuntu_version_history#Releases)
- **Project files:** [DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md) | [`debian/control`](../debian/control) | [`build-deb.yml`](../.github/workflows/build-deb.yml)

**Note:** The `debian/` directory is for local builds only, not official Debian archive submission.

### Directory Structure

```
debian/
├── changelog          # Version history (UNRELEASED)
├── control            # Package metadata
├── copyright          # DEP-5 license info
├── gbp.conf           # git-buildpackage configuration
├── patches/
│   └── series         # Empty (see wxPython note below)
├── README.source      # Explains this is for local builds
├── rules              # Build instructions
├── source/
│   └── format         # 3.0 (quilt)
└── taskcoach.install  # Installation notes
```

**Note:** The `.gitattributes` file excludes `debian/` from `git archive` and GitHub release tarballs.

### Building Locally

### Quick Binary Build

```bash
# Install build dependencies
sudo apt install build-essential debhelper dh-python \
    python3-all python3-setuptools python3-distro devscripts

# Build binary package (no orig tarball needed)
dpkg-buildpackage -us -uc -b

# Package will be in parent directory
ls ../*.deb
```

### With Lintian Checks

```bash
dpkg-buildpackage -us -uc -b
lintian --info --display-info ../*.changes
```

### Building Source Package

Source packages (for PPA uploads) require an orig tarball:

```bash
# Get version from changelog
VERSION=$(dpkg-parsechangelog -S Version | cut -d- -f1)

# Create orig tarball (excludes debian/ and .git/)
tar --exclude='debian' --exclude='.git' \
    -czf ../taskcoach_${VERSION}.orig.tar.gz .

# Build source package
dpkg-buildpackage -us -uc -S

# Files created in parent directory:
# - taskcoach_X.Y.Z.orig.tar.gz (upstream source)
# - taskcoach_X.Y.Z-N.debian.tar.xz (debian/ directory)
# - taskcoach_X.Y.Z-N.dsc (source description)
```

### wxPython Patch Strategy

**Project files:** [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md) | [patches/wxpython/README.md](../patches/wxpython/README.md)

Task Coach requires a patch to wxPython's `hypertreelist.py` for correct background coloring. Since packages cannot modify system `python3-wxgtk4.0`, we bundle the patch.

### The Problem

- wxPython < 4.2.4 has bugs in `TR_FULL_ROW_HIGHLIGHT` and `TR_FILL_WHOLE_COLUMN_BACKGROUND`
- Fix merged upstream in wxPython 4.2.4 (October 28, 2025)
- Current Debian/Ubuntu versions ship older wxPython

### The Solution

1. **Bundled patch** at `taskcoachlib/patches/hypertreelist.py`
2. **Import hook** in `taskcoachlib/workarounds/monkeypatches.py`
3. **Redirects** `wx.lib.agw.hypertreelist` to bundled version
4. System wxPython remains unmodified

This works for all installation methods (Debian, Ubuntu, Fedora, pip, etc.).

### When to Remove

Remove when Debian/Ubuntu ship wxPython >= 4.2.4:
1. Remove import hook from `monkeypatches.py`
2. Remove `taskcoachlib/patches/` directory

### Dependencies

See `debian/control` (linked above) for runtime, build, and optional dependencies.

### Ubuntu PPA Publishing

**References:** [Launchpad PPA Documentation](https://help.launchpad.net/Packaging/PPA)

The same `debian/` packaging works for Ubuntu PPAs with minor changes.

### Version Naming

Ubuntu packages use a suffix to distinguish from Debian:

```
# Debian (hypothetical official)
taskcoach (1.6.1-1) unstable; urgency=medium

# Ubuntu PPA
taskcoach (1.6.1-1~ppa1) noble; urgency=medium
```

### Publishing to a PPA

1. **Create a Launchpad account** at https://launchpad.net

2. **Set up PPA**:
   ```bash
   # Create PPA via Launchpad web interface
   # https://launchpad.net/~YOUR_USERNAME/+activate-ppa
   ```

3. **Update changelog** for Ubuntu:
   ```bash
   # Change UNRELEASED to Ubuntu codename
   dch -D noble -v "1.6.1-1~ppa1" "PPA release for Ubuntu Noble"
   ```

4. **Create orig tarball** (required for quilt format):
   ```bash
   # Get version from changelog
   VERSION=$(dpkg-parsechangelog -S Version | cut -d- -f1)

   # Create tarball excluding debian/ directory
   tar --exclude='debian' --exclude='.git' \
       -czf ../taskcoach_${VERSION}.orig.tar.gz .
   ```

5. **Build source package**:
   ```bash
   dpkg-buildpackage -us -uc -S
   ```

6. **Sign and upload**:
   ```bash
   debsign ../*.changes
   dput ppa:YOUR_USERNAME/YOUR_PPA ../*_source.changes
   ```

### Supported Ubuntu Releases

| Codename | Version | wxPython | Status |
|----------|---------|----------|--------|
| Jammy | 22.04 LTS | 4.1.1 | Patch required |
| Noble | 24.04 LTS | 4.2.1 | Patch required |
| Oracular | 24.10 | 4.2.1 | Patch required |
| Plucky | 25.04 | 4.2.2 | Patch required |
| Questing | 25.10 | 4.2.x | Patch required |

---

## Arch Linux / Manjaro Packaging

- **Arch:** [Creating packages](https://wiki.archlinux.org/title/Creating_packages) | [PKGBUILD](https://wiki.archlinux.org/title/PKGBUILD) | [Python guidelines](https://wiki.archlinux.org/title/Python_package_guidelines) | [makepkg](https://wiki.archlinux.org/title/Makepkg) | [AUR](https://wiki.archlinux.org/title/Arch_User_Repository)
- **Manjaro:** [Package Management](https://wiki.manjaro.org/index.php/Pacman_Overview)
- **Project files:** [`PKGBUILD`](../build.in/arch/PKGBUILD) | [`build-arch.yml`](../.github/workflows/build-arch.yml)

Task Coach includes native packaging support for Arch Linux and Manjaro using the standard PKGBUILD system.

### Directory Structure

```
build.in/arch/
├── PKGBUILD           # Arch package build script
└── taskcoach.install  # Post-install hooks
```

### Building Locally

#### Quick Build

```bash
# Install build dependencies
sudo pacman -S base-devel python python-setuptools python-distro

# Build package using the build script
./scripts/build-arch.sh

# Package will be in build-area/
ls build-area/*.pkg.tar.zst
```

#### Build and Install

```bash
./scripts/build-arch.sh --install
```

#### Manual Build with makepkg

```bash
cd build.in/arch

# Create source tarball (from project root)
VERSION=$(python3 -c "from taskcoachlib.meta import data; print(data.version_full)")
tar -czf "taskcoach-$VERSION.tar.gz" --transform "s,^,taskcoach-$VERSION/," \
    --exclude='.git' --exclude='build-area' -C ../.. .

# Update PKGBUILD version and checksums
updpkgsums

# Build package
makepkg -sf

# Install
sudo pacman -U taskcoach-*.pkg.tar.zst
```

### Dependencies

See `PKGBUILD` (linked above) for runtime, build, and optional dependencies. Some packages require AUR (`python-pypubsub`, `python-squaremap`).

### Setup Script

For development or running from source:

```bash
# Auto-detect and set up (redirects to setup_arch.sh on Arch systems)
./setup.sh

# Or directly use the Arch setup script
./setup_arch.sh
```

The setup script:
1. Installs packages from official Arch repos via pacman
2. Prompts for AUR packages if yay/paru is available
3. Creates a virtual environment with system site-packages
4. Tests the installation

### Supported Distributions

| Distribution | Tested | Notes |
|--------------|--------|-------|
| Arch Linux | ✓ | Primary target |
| Manjaro | ✓ | Fully supported |
| EndeavourOS | ✓ | Uses Arch setup |
| Garuda Linux | ✓ | Uses Arch setup |
| Artix Linux | ✓ | Uses Arch setup |
| ArcoLinux | ✓ | Uses Arch setup |

---

## Fedora Packaging

- **Fedora:** [Packaging Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/) | [RPM Packaging Guide](https://rpm-packaging-guide.github.io/) | [Python Packaging](https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/) | [Releases](https://en.wikipedia.org/wiki/Fedora_Linux)
- **Project files:** [`taskcoach.spec`](../build.in/fedora/taskcoach.spec) | [`build-rpm.yml`](../.github/workflows/build-rpm.yml)

Task Coach includes native RPM packaging support for Fedora using the standard spec file format.

### Directory Structure

```
build.in/fedora/
└── taskcoach.spec     # RPM spec file
```

### Building Locally

#### Quick Build

```bash
# Install build dependencies
sudo dnf install rpm-build rpmdevtools python3-devel python3-setuptools

# Set up RPM build tree
rpmdev-setuptree

# Copy spec file
cp build.in/fedora/taskcoach.spec ~/rpmbuild/SPECS/

# Create source tarball
VERSION=$(python3 -c "from taskcoachlib.meta import data; print(data.version_full)")
tar -czf ~/rpmbuild/SOURCES/taskcoach-$VERSION.tar.gz \
    --transform "s,^,taskcoach-main/," --exclude='.git' .

# Build RPM
rpmbuild -bb ~/rpmbuild/SPECS/taskcoach.spec

# Package will be in ~/rpmbuild/RPMS/noarch/
ls ~/rpmbuild/RPMS/noarch/*.rpm
```

#### Install

```bash
sudo dnf install ~/rpmbuild/RPMS/noarch/taskcoach-*.rpm
```

### Dependencies

See `taskcoach.spec` (linked above) for runtime, build, and optional dependencies.

#### Build Notes

| Distro | Python | Notes |
|--------|--------|-------|
| Fedora 43 | 3.13 | Current stable release |

**Fedora 42 (disabled):** Fedora 42 and 43 builds are identical (same dependencies, same spec file). The noarch RPM built on Fedora 43 works on both. To reactivate Fedora 42 builds, uncomment the matrix entry in `.github/workflows/build-rpm.yml`.

**Spec file approach:** We use `%py3_build` and `%py3_install` macros. While Fedora's newest guidelines prefer `%pyproject_wheel`/`%pyproject_install`, the older macros provide broader compatibility.

### Supported Distributions

| Distribution | Version | Tested | Notes |
|--------------|---------|--------|-------|
| Fedora | 43 | ✓ | Primary target (noarch RPM works on 42 too) |

---

## AppImage Packaging

- **AppImage:** [python-appimage](https://github.com/niess/python-appimage) | [wxPython extras](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04) | [AppImage docs](https://docs.appimage.org/)
- **Project files:** [APPIMAGE.md](APPIMAGE.md) | [`build-appimage.yml`](../.github/workflows/build-appimage.yml)

The AppImage build creates a portable, self-contained Linux executable that bundles Python 3.11, wxPython 4.2.4, and all dependencies into a single file.

### Available Builds

| Build | Python | Architecture | Target |
|-------|--------|--------------|--------|
| `TaskCoach-X.Y.Z-x86_64.AppImage` | 3.11 | x86_64 | Most Linux users |

**Minimum requirements:** glibc 2.28+ (Debian Bookworm, Ubuntu 22.04+, Fedora 40+)

For detailed AppImage documentation including library bundling strategy, design decisions, build process, and troubleshooting, see **[APPIMAGE.md](APPIMAGE.md)**.

---

## Windows Packaging

- **Windows:** [Inno Setup](https://jrsoftware.org/isinfo.php) | [Python Embeddable Package](https://www.python.org/downloads/windows/) | [Thonny](https://github.com/thonny/thonny) (reference implementation)
- **Project files:** [WINDOWS.md](WINDOWS.md) | [`build-windows.yml`](../.github/workflows/build-windows.yml)

Task Coach builds Windows installers using Python's embeddable distribution + Inno Setup (same approach as Thonny).

### Available Builds

| Build | Python | Arch | Target |
|-------|--------|------|--------|
| `TaskCoach-X.Y.Z-windows-x64-setup.exe` | 3.11 | 64-bit | Most users |
| `TaskCoach-X.Y.Z-windows-x64-portable.zip` | 3.11 | 64-bit | Portable |

For detailed Windows documentation including packaging options, Python embeddable configuration, DLL handling, shutdown behavior, and troubleshooting, see **[WINDOWS.md](WINDOWS.md)**.

---

## macOS Packaging

- **macOS:** [Apple Developer](https://developer.apple.com/documentation/) | [py2app](https://py2app.readthedocs.io/)
- **Project files:** [MACOS.md](MACOS.md) | [`build-macos.yml`](../.github/workflows/build-macos.yml)

Task Coach builds native macOS .app bundles using py2app for both Intel and Apple Silicon architectures.

### Available Builds

| Build | Architecture | Target | Runner |
|-------|--------------|--------|--------|
| `TaskCoach-X.Y.Z-macos-intel.dmg` | x86_64 | Intel Macs | `macos-15-intel` |
| `TaskCoach-X.Y.Z-macos-arm64.dmg` | arm64 | Apple Silicon M1/M2/M3/M4 | `macos-latest` |

**Minimum supported:** macOS 13 (Ventura)

### Build Process

1. Sets up Python 3.11 on macOS runner
2. Installs wxPython and dependencies via pip
3. Creates icns icon file using `iconutil`
4. Builds .app bundle with py2app
5. Creates DMG with Applications symlink

### Code Signing

**Current status:** Builds are unsigned. Users must clear quarantine:
```bash
xattr -cr "/Applications/Task Coach.app"
```

---

## Appendix

### Dependency Installation Strategy

All build scripts follow the same simple strategy:

1. **Distro packages first**: Install all available dependencies from distro repos
2. **Pip fallback**: Only use pip for packages not in distro repos or with version issues

### Creating a Release

This process applies to all build targets (AppImage, Windows, macOS, etc.):

1. Update version in `taskcoachlib/meta/data.py`
2. Commit and push changes
3. Create and push a version tag:
   ```bash
   git tag v2.0.1.23
   git push origin v2.0.1.23
   ```
4. GitHub Actions will automatically build all packages and create a GitHub Release

