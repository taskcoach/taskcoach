# Linux Packaging Guide for Task Coach

This document describes the packaging setup for Task Coach on various Linux distributions including Debian, Ubuntu, Linux Mint, Arch Linux, Manjaro, and Fedora.

## Table of Contents

- [Dependency Installation Strategy](#dependency-installation-strategy)
- [Install Overview by Build Target](#install-overview-by-build-target)
- [Estimated Desktop User Base](#estimated-desktop-user-base-by-distribution)
- [Upstream vs Debian Packaging](#important-upstream-vs-debian-packaging)
- [Directory Structure](#directory-structure)
- [Building Locally](#building-locally)
- [wxPython Patch Strategy](#wxpython-patch-strategy)
- [Dependencies](#dependencies)
- [Ubuntu PPA Publishing](#ubuntu-ppa-publishing)
- [Official Debian Packaging](#official-debian-packaging-for-debian-maintainers)
- [GitHub Actions CI](#github-actions-ci)
- [Arch Linux / Manjaro Packaging](#arch-linux--manjaro-packaging)
- [Fedora Packaging](#fedora-packaging)
- [AppImage Packaging](#appimage-packaging)
- [Windows Packaging](#windows-packaging)
- [References](#references)

## Dependency Installation Strategy

All build scripts follow the same simple strategy:

1. **Distro packages first**: Install all available dependencies from distro repos
2. **Pip fallback**: Only use pip for packages not in distro repos or with version issues
3. **Version requirements**: Some packages have minimum version requirements

### Minimum Version Requirements

| Package | Min Version | Why Required | Distros with Old Versions |
|---------|-------------|--------------|---------------------------|
| Python | >=3.8 | Type hints, f-strings, walrus operator | — |
| wxPython | >=4.2.0 | HyperTreeList stability | — |
| wxPython | >=4.2.4 | hypertreelist row background fix (PR #2088) | All current (Bookworm 4.2.0, Trixie 4.2.3) |
| pyparsing | >=3.1.3 | `pp.Tag()` API | Debian Bookworm (3.0.9) |
| watchdog | >=3.0.0 | File monitoring API | Debian Bookworm (2.2.1) |
| fasteners | >=0.19 | File locking API | — |

**Note**: wxPython 4.2.4 was released October 28, 2025 but is not yet packaged for any distro.
Until then, a bundled patch in `taskcoachlib/patches/` is used (see [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md)).

**Handled automatically**: Build scripts bundle newer versions for distros with old packages.
No manual steps required for users installing from packages.

### What This Means for Each Distro

| Distro | From Distro Repos | From pip (bundled at build) |
|--------|-------------------|----------|
| Debian Bookworm | Most deps | pyparsing, watchdog (version issues) |
| Debian Trixie/Ubuntu Noble | All dependencies | None |
| Arch/Manjaro | All except pypubsub (AUR), squaremap | squaremap |
| Fedora 39/40 | Most deps | squaremap, pyparsing (version issues) |

### How setup.py Works

The `setup.py` file lists core dependencies with version requirements where needed:
- Packages with API requirements have version specs (pyparsing, watchdog, etc.)
- Optional features in `extras_require` (e.g., `squaremap`, `gntp`)

### Platform-Specific Dependencies

| Package | Platform | Notes |
|---------|----------|-------|
| gntp | Windows/macOS only | Growl notifications |
| WMI | Windows only | System information |

## Install Overview by Build Target

This table shows how dependencies are handled in **built packages** and **setup scripts**.

| Package | debian12 | ubuntu22 | debian13 | ubuntu24 | arch | fedora39 | fedora40 | appimage | windows | macos |
|---------|:--------:|:--------:|:--------:|:--------:|:----:|:--------:|:--------:|:--------:|:-------:|:-----:|
| wxpython | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| pypubsub | distro | distro | distro | distro | AUR | distro | distro | bundled | pip | pip |
| pyparsing | **pip** | **pip** | distro | distro | distro | **pip** | **pip** | bundled | pip | pip |
| watchdog | **pip** | **pip** | distro | distro | distro | distro | distro | bundled | pip | pip |
| squaremap | distro | distro | distro | distro | **pip** | **pip** | **pip** | bundled | pip | pip |
| six | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| lxml | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| numpy | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| chardet | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| python-dateutil | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| keyring | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| pyxdg | distro | distro | distro | distro | distro | distro | distro | bundled | — | — |
| fasteners | distro | distro | distro | distro | distro | distro | distro | bundled | pip | pip |
| hypertreelist | **patch** | **patch** | **patch** | **patch** | **patch** | **patch** | **patch** | bundled | **patch** | **patch** |
| gntp | — | — | — | — | — | — | — | — | pip | pip |
| WMI | — | — | — | — | — | — | — | — | pip | — |

**Key:**
- `distro` = Installed from distribution repos (required dependency)
- `pip` = Bundled via pip in package build (version too old or not in repos)
- `patch` = Bundled patch in `taskcoachlib/patches/` (wxPython hypertreelist fix)
- `bundled` = Bundled in package (thirdparty/ for .deb/.rpm, or inside AppImage)
- `AUR` = Arch User Repository (rolling release)
- `—` = Not applicable for this platform

### Build Scripts and Workflows

| Target | ID | Python | wxPython | Setup Script | GitHub Workflow | Notes |
|--------|:--:|:------:|:--------:|--------------|-----------------|-------|
| Debian 12 Bookworm | debian12 | 3.11 | 4.2.0 | `setup_debian12_bookworm.sh` | `build-deb.yml` | pip: pyparsing, watchdog |
| Debian 13 Trixie | debian13 | 3.12 | 4.2.3 | `setup_debian13_trixie.sh` | `build-deb.yml` | Distro deps sufficient |
| Ubuntu 22.04 Jammy | ubuntu22 | 3.10 | 4.1.1 | `setup_ubuntu2204_jammy.sh` | `build-deb.yml` | pip: pyparsing, watchdog |
| Ubuntu 24.04 Noble | ubuntu24 | 3.12 | 4.2.1 | `setup_ubuntu2404_noble.sh` | `build-deb.yml` | Distro deps sufficient |
| Arch Linux | arch | latest | latest | `setup_arch.sh` | `build-arch.yml` | pip: squaremap; pypubsub from AUR |
| Manjaro | arch | latest | latest | `setup_arch.sh` | `build-arch.yml` | pip: squaremap; pypubsub from AUR |
| Fedora 39 | fedora39 | 3.12 | 4.2.1 | `setup_fedora.sh` | `build-rpm.yml` | pip: squaremap, pyparsing |
| Fedora 40 | fedora40 | 3.12 | 4.2.1 | `setup_fedora.sh` | `build-rpm.yml` | pip: squaremap, pyparsing |
| **AppImage** | appimage | **3.11** | **4.2.4** | — | `build-appimage.yml` | Bundles Python + all deps |
| **Windows** | windows | **3.11** | **4.2.x** | — | `build-windows.yml` | Python embed + Inno Setup |
| macOS | macos | — | — | — | — | Not currently building |

**AppImage note:** Uses Python 3.11 (not 3.12) for wxPython wheel availability. See [AppImage Packaging](#appimage-packaging) section for details.

**pip packages are bundled at build time** - users just install the package, no pip runs at install.

## Estimated Desktop User Base by Distribution

The following table provides rough estimates of desktop users for each supported distribution. These numbers help prioritize packaging efforts.

| Distribution | Est. Desktop Users | % of Linux Desktop | Priority | Notes |
|--------------|-------------------:|-------------------:|:--------:|-------|
| **Ubuntu** (all flavors) | 13-17 million | ~34% | High | Most popular desktop distro |
| **Debian** | 6-8 million | ~16% | High | Stability-focused users |
| **Linux Mint** | 4-6 million | ~10-12% | High | Uses Ubuntu/Debian `.deb` packages |
| **Arch Linux** | 1.5-2.5 million | ~4-5% | Medium | Power users, rolling release |
| **Manjaro** | 1-1.5 million | ~2-3% | Medium | Arch-based, user-friendly |
| **Fedora** | 0.8-1.2 million | ~2-3% | Medium | Cutting-edge, developer-focused |
| **Pop!_OS** | 0.5-1 million | ~1-2% | — | Uses Ubuntu `.deb` packages |

*Estimates as of Q4 2024. Based on ~40-50 million total Linux desktop users worldwide (4-4.5% of ~1 billion PCs).*

**Data sources:**
- [StatCounter Global Stats](https://gs.statcounter.com/os-market-share/desktop/worldwide/) - OS market share
- [Steam Hardware Survey](https://store.steampowered.com/hwsurvey?platform=linux) - Gaming distro breakdown
- [Enterprise Apps Today](https://www.enterpriseappstoday.com/stats/linux-statistics.html) - Linux statistics 2024

**Important caveats:**
- Linux users often block tracking, so actual numbers may be higher
- Steam data skews toward gaming-focused distros (Arch, SteamOS)
- Linux Mint and Pop!_OS users can use Ubuntu/Debian packages directly
- Numbers are approximate and vary by data source

## Important: Upstream vs Debian Packaging

This repository contains an **upstream** `debian/` directory for local builds only. This is **NOT** the official Debian package.

### The Two Types of debian/ Directories

| Type | Location | Purpose |
|------|----------|---------|
| **Upstream debian/** | This repo (`debian/`) | Local testing, convenience builds |
| **Official Debian packaging** | Separate `debian/*` branches | Debian archive submission |

Per [DEP-14](https://dep-team.pages.debian.net/deps/dep14/), official Debian packaging should use:
- `upstream/latest` - Contains release tarball contents (no `debian/`)
- `debian/master` - Derived from upstream, contains official `debian/` packaging

### Why the Separation?

1. **Different maintainers** - Upstream developers vs Debian packagers
2. **Different workflows** - git-buildpackage (gbp) vs direct development
3. **Patch management** - Debian uses quilt patches in `debian/patches/`
4. **Release tracking** - Debian tracks upstream releases via `debian/watch`

### This Repository's debian/

The `debian/` in this repository:
- Is for **local testing** and **convenience builds**
- Is **excluded from release tarballs** via `.gitattributes`
- Uses `UNRELEASED` distribution (not for archive upload)
- Does NOT include `debian/watch` (that's for Debian to track upstream)

## Directory Structure

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

## Building Locally

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

## wxPython Patch Strategy

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

## Dependencies

### Runtime Dependencies

```
python3 (>= 3.8)
python3-wxgtk4.0 (>= 4.2.0)
python3-six
python3-pubsub
python3-watchdog
python3-chardet
python3-dateutil
python3-pyparsing
python3-lxml
python3-xdg
python3-keyring
python3-numpy
python3-fasteners
libxss1
xdg-utils
```

### Optional Dependencies

```
python3-squaremap    # Hierarchical data visualization
python3-gntp         # Growl notifications (not in all distros)
```

### Build Dependencies

```
debhelper-compat (= 13)
dh-python
python3-all
python3-setuptools
python3-distro
```

## Ubuntu PPA Publishing

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
| Noble | 24.04 LTS | 4.2.1 | Patch required |
| Jammy | 22.04 LTS | 4.1.1 | Patch required |
| Oracular | 24.10 | 4.2.1 | Patch required |

## Official Debian Packaging (For Debian Maintainers)

If you're a Debian maintainer preparing an official package:

### 1. Set Up DEP-14 Branches

```bash
# Create upstream branch from release tarball
git checkout --orphan upstream/latest
# Import tarball contents (no debian/)

# Create debian branch
git checkout -b debian/master upstream/latest
# Add official debian/ directory
```

### 2. Configure gbp

Create `debian/gbp.conf`:
```ini
[DEFAULT]
debian-branch = debian/master
upstream-branch = upstream/latest
pristine-tar = True
```

### 3. Add debian/watch

```
version=4
opts=filenamemangle=s/.+\/v?(\d\S+)\.tar\.gz/taskcoach-$1\.tar\.gz/ \
  https://github.com/taskcoach/taskcoach/tags .*/v?(\d[\d.]+)\.tar\.gz
```

### 4. File ITP Bug

```bash
reportbug --severity=wishlist --package=wnpp \
  --subject="ITP: taskcoach -- Personal task manager"
```

### 5. Request Sponsorship

- [debian-mentors mailing list](https://lists.debian.org/debian-mentors/)
- [mentors.debian.net](https://mentors.debian.net/)

## GitHub Actions CI

### Automated .deb Builds

```yaml
name: Build Debian Package

on:
  push:
    tags: ['v*']
  workflow_dispatch:

jobs:
  build-deb:
    runs-on: ubuntu-latest
    container: debian:bookworm

    steps:
      - uses: actions/checkout@v4

      - name: Install build dependencies
        run: |
          apt-get update
          apt-get install -y build-essential debhelper dh-python \
            python3-all python3-setuptools python3-distro devscripts

      - name: Build package
        run: dpkg-buildpackage -us -uc -b

      - name: Run lintian
        run: |
          apt-get install -y lintian
          lintian --info ../*.changes || true

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: debian-package
          path: ../*.deb
```

### Multi-Distribution Matrix

```yaml
jobs:
  build:
    strategy:
      matrix:
        include:
          - distro: debian:bookworm
            name: bookworm
          - distro: debian:trixie
            name: trixie
          - distro: ubuntu:noble
            name: noble
    runs-on: ubuntu-latest
    container: ${{ matrix.distro }}
    # ... build steps
```

---

## Arch Linux / Manjaro Packaging

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

#### Runtime Dependencies (from official repos)

```
python (>= 3.8)
python-wxpython (>= 4.2.0)
python-six
python-pypubsub (AUR)
python-watchdog
python-chardet
python-dateutil
python-pyparsing
python-lxml
python-pyxdg
python-keyring
python-numpy
python-fasteners
libxss
xdg-utils
```

#### Optional Dependencies

```
python-squaremap    # Hierarchical data visualization (AUR)
python-gntp         # Growl notifications (AUR)
espeak-ng           # Spoken reminders
```

#### Build Dependencies

```
base-devel
python-setuptools
python-distro
```

### AUR Package

Some dependencies are only available from the AUR:
- `python-pypubsub` - Required for pub/sub messaging
- `python-squaremap` - Optional visualization
- `python-gntp` - Optional Growl support

Install using an AUR helper:
```bash
yay -S python-pypubsub python-squaremap python-gntp
# or
paru -S python-pypubsub python-squaremap python-gntp
```

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

### GitHub Actions CI

The repository includes automated Arch package builds via GitHub Actions:

```yaml
# .github/workflows/build-arch.yml
name: Build Arch/Manjaro Package

jobs:
  build-arch:
    runs-on: ubuntu-latest
    container: archlinux:latest
    steps:
      - name: Build package
        run: makepkg -sf
```

Features:
- Builds on every push to `main`, `master`, or `claude/**` branches
- Tests installation on clean Arch Linux container
- Tests installation on Manjaro Linux container
- Uploads packages as artifacts
- Creates GitHub releases on version tags

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

#### Runtime Dependencies (from official repos)

```
python3 (>= 3.8)
python3-wxpython4 (>= 4.2.0)
python3-six
python3-pypubsub
python3-watchdog
python3-chardet
python3-dateutil
python3-pyparsing
python3-lxml
python3-pyxdg
python3-keyring
python3-numpy
python3-fasteners
libXScrnSaver
xdg-utils
```

#### Optional Dependencies

```
espeak-ng            # Spoken reminders
```

#### Pip-installed Dependencies

The following are not in Fedora repos and are installed via pip during build:
```
squaremap           # Hierarchical data visualization
```

#### Build Notes

| Distro | Python | Notes |
|--------|--------|-------|
| Fedora 39 | 3.12 | Current stable release |
| Fedora 40 | 3.12 | Current stable release |

**Spec file approach:** We use `%py3_build` and `%py3_install` macros. While Fedora's newest guidelines prefer `%pyproject_wheel`/`%pyproject_install`, the older macros provide broader compatibility.

### GitHub Actions CI

The repository includes automated RPM builds via GitHub Actions:

```yaml
# .github/workflows/build-rpm.yml
name: Build RPM Package

jobs:
  build-rpm:
    strategy:
      matrix:
        include:
          - distro: fedora:39
          - distro: fedora:40
    runs-on: ubuntu-latest
    container: ${{ matrix.distro }}
    steps:
      - name: Build package
        run: rpmbuild -bb taskcoach.spec
```

Features:
- Builds on Fedora 39 and Fedora 40
- Tests installation on clean containers
- Uploads packages as artifacts
- Creates GitHub releases on version tags

### Supported Distributions

| Distribution | Version | Tested | Notes |
|--------------|---------|--------|-------|
| Fedora | 39, 40 | ✓ | Primary target |

---

## AppImage Packaging

The AppImage build system creates a portable, self-contained Linux executable that bundles Python, wxPython, and all dependencies into a single file.

### What's Included

| Component | Version | Source |
|-----------|---------|--------|
| Python | 3.11.14 | [python-appimage](https://github.com/niess/python-appimage) (manylinux_2_28) |
| wxPython | 4.2.4 | [wxPython extras](https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04) |
| wxWidgets | 3.2.8 | Bundled with wxPython |
| Image libs | libjpeg, libpng, libtiff, libwebp | Copied from build system |

The resulting AppImage runs on most Linux distributions with glibc 2.28+ (Debian Bookworm, Ubuntu 22.04+, Fedora 37+).

### Design Decisions

#### Why Python 3.11 (not 3.12 or 3.13)?

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

#### Why manylinux_2_28?

The Python AppImage is built on a `manylinux_2_28` base (CentOS/RHEL with glibc 2.28). This ensures compatibility with older distributions. The "(Red Hat 14.2.1-7)" in the Python version string refers to the GCC version used to compile Python on the manylinux build system.

#### Bundled vs System Libraries

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

### How It Works

1. **Base Image** - Downloads pre-built Python AppImage from python-appimage project
2. **Dependencies** - Installs wxPython from extras repository and other deps from PyPI
3. **Library Bundling** - Copies required shared libraries (libjpeg, libpng, etc.)
4. **Custom AppRun** - Creates launcher script setting PYTHONHOME, PYTHONPATH, LD_LIBRARY_PATH
5. **Packaging** - Uses `appimagetool` to create the final `.AppImage` file

### Directory Structure

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
    └── share/taskcoach/
        ├── taskcoach.py
        └── taskcoachlib/
```

### Building

#### GitHub Actions

`.github/workflows/build-appimage.yml`

Triggers on push to main/master, version tags, and PRs. Tests on Debian Bookworm, Ubuntu 22.04/24.04, and Fedora 39.

#### Local Build

```bash
./scripts/build-appimage.sh
```

Requires: `wget`, `file`, `patchelf`, and optionally `libfuse2`

### Creating a Release

1. Update version in `taskcoachlib/meta/data.py`
2. Commit and push changes
3. Create and push a tag:
   ```bash
   git tag v2.0.0.97
   git push origin v2.0.0.97
   ```
4. GitHub Actions will build the AppImage and create a GitHub Release

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "cannot open shared object file" | Add library to `LIBS_TO_BUNDLE` in workflow |
| Python path issues | Check PYTHONHOME, PYTHONPATH, LD_LIBRARY_PATH in AppRun |
| YAML heredoc issues | Use `echo` statements instead of heredocs in workflow |
| AppRun symlink | Remove original symlink before creating custom AppRun |

---

## Windows Packaging

Windows builds use Python's embeddable distribution + Inno Setup (same approach as [Thonny](https://github.com/thonny/thonny)).

### Available Builds

| Build | Python | Arch | Target |
|-------|--------|------|--------|
| `TaskCoach-X.Y.Z-windows-x64-setup.exe` | 3.11 | 64-bit | Most users |
| `TaskCoach-X.Y.Z-windows-x64-portable.zip` | 3.11 | 64-bit | Portable |
| `TaskCoach-X.Y.Z-windows-x86-py39-setup.exe` | 3.9 | 32-bit | VMs, older systems |
| `TaskCoach-X.Y.Z-windows-x86-py39-portable.zip` | 3.9 | 32-bit | Portable, compatibility |

### Why This Approach?

| Method | Issue |
|--------|-------|
| PyInstaller | Hangs at "Looking for dynamic libraries" on GitHub Actions |
| cx_Freeze | Produces executables that fail to run |
| **Python Embed + Inno Setup** | Reliable, proper installer, file associations |

### Build Workflow

See `.github/workflows/build-windows.yml`

### Reference Implementations

| Project | Approach | Notes |
|---------|----------|-------|
| [Thonny](https://github.com/thonny/thonny) | Python Embed + Inno Setup | 64-bit and 32-bit builds |
| [PixelFlasher](https://github.com/badabing2005/PixelFlasher) | PyInstaller | 64-bit only, wxPython app |

---

## References

### Debian Packaging
- [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/)
- [DEP-14: Git packaging layout](https://dep-team.pages.debian.net/deps/dep14/)
- [DEP-5: Machine-readable copyright](https://dep-team.pages.debian.net/deps/dep5/)
- [Python Policy](https://www.debian.org/doc/packaging-manuals/python-policy/)

### Git Workflows
- [PackagingWithGit - Debian Wiki](https://wiki.debian.org/PackagingWithGit)
- [git-buildpackage Manual](http://honk.sigxcpu.org/projects/git-buildpackage/manual-html/gbp.intro.html)

### Ubuntu
- [Launchpad PPA Documentation](https://help.launchpad.net/Packaging/PPA)
- [Ubuntu Packaging Guide](https://canonical-ubuntu-packaging-guide.readthedocs-hosted.com/)

### Arch Linux Packaging
- [Arch Wiki: Creating packages](https://wiki.archlinux.org/title/Creating_packages)
- [Arch Wiki: PKGBUILD](https://wiki.archlinux.org/title/PKGBUILD)
- [Arch Wiki: makepkg](https://wiki.archlinux.org/title/Makepkg)
- [Arch Wiki: AUR](https://wiki.archlinux.org/title/Arch_User_Repository)
- [Manjaro Wiki: Package Management](https://wiki.manjaro.org/index.php/Pacman_Overview)

### Fedora/RPM Packaging
- [Fedora Packaging Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/)
- [RPM Packaging Guide](https://rpm-packaging-guide.github.io/)
- [Fedora Python Packaging](https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/)

### Desktop Integration
- [XDG Desktop Entry Spec](https://specifications.freedesktop.org/desktop-entry-spec/latest/)
- [AppStream Metadata](https://www.freedesktop.org/software/appstream/docs/)

### Windows Packaging
- [Inno Setup](https://jrsoftware.org/isinfo.php) - Free installer builder (recommended)
- [Python Embeddable Package](https://www.python.org/downloads/windows/) - Portable Python distribution
- [Thonny](https://github.com/thonny/thonny) - Reference implementation for Python + Inno Setup

## Related Documentation

- [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md) - Detailed patch information
- [patches/wxpython/README.md](../patches/wxpython/README.md) - Patch installation methods
- [DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md) - Development setup on Bookworm
