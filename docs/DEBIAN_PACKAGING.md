# Debian Packaging Guide for Task Coach

This document describes the preparation and requirements for submitting Task Coach to the official Debian repositories.

## Current Status

| Item | Status |
|------|--------|
| License | GPL-3+ (Debian-compatible) |
| Source format | 3.0 (quilt) |
| debian/ directory | Complete |
| Lintian compliance | Not yet tested |
| ITP bug filed | No |

## Directory Structure

```
debian/
├── changelog                                         # Version history
├── compat                                            # Debhelper compat (13)
├── control                                           # Package metadata
├── copyright                                         # DEP-5 license info
├── patches/
│   └── series                                        # Empty (see note below)
├── rules                                             # Build instructions
├── source/
│   └── format                                        # 3.0 (quilt)
├── taskcoach.install                                 # Installation notes
└── watch                                             # Upstream version tracking
```

**Note on patches:** The wxPython hypertreelist fix is NOT applied via quilt patches.
The file `wx/lib/agw/hypertreelist.py` belongs to `python3-wxgtk4.0`, not Task Coach.
Instead, we bundle a pre-patched copy at `patches/wxpython/hypertreelist.py` and
install it via `debian/rules` to `/usr/share/taskcoach/lib/`.

### Files Status

| File | Purpose | Status |
|------|---------|--------|
| `debian/control` | Package metadata and dependencies | Done |
| `debian/rules` | Build instructions | Done |
| `debian/changelog` | Version history (Debian format) | Done |
| `debian/copyright` | License info (DEP-5 format) | Done |
| `debian/compat` | Debhelper compatibility level (13) | Done |
| `debian/watch` | Upstream version tracking | Done |
| `debian/taskcoach.install` | File installation notes | Done |
| `debian/taskcoach.desktop` | Desktop entry | Uses build.in/ |
| `debian/taskcoach.manpages` | Man page list | Skipped (optional) |

## wxPython Patch Strategy

Task Coach requires a patch to wxPython's `hypertreelist.py` for correct background coloring. Since the Debian package cannot modify the system `python3-wxgtk4.0` package, we use a bundling approach:

### The Problem

- wxPython < 4.2.4 has bugs in `TR_FULL_ROW_HIGHLIGHT` and `TR_FILL_WHOLE_COLUMN_BACKGROUND`
- Fix merged upstream in wxPython 4.2.4 (October 28, 2025)
- Current Debian versions:
  - Bookworm: 4.2.0 (patch required)
  - Trixie: 4.2.3 (patch required)
  - Sid: 4.2.3 (patch required)

### The Solution

1. **Bundle the patched file** in Task Coach at `/usr/share/taskcoach/lib/hypertreelist.py`
2. **Import hook** in Task Coach intercepts `wx.lib.agw.hypertreelist` imports
3. **Redirects** to the bundled patched version
4. System wxPython remains unmodified

### Patch Files

- Source patch: `patches/wxpython/hypertreelist.py` (full patched file)
- Quilt patch: `debian/patches/fix-hypertreelist-background-coloring.patch` (diff with DEP-3 headers)

### When to Remove

The patch can be removed when Debian ships wxPython >= 4.2.4. The `debian/control` file should include version-conditional logic or the patch should be maintained until all supported Debian releases have the fix.

## Dependencies

### Runtime Dependencies

From `setup.py`, Task Coach requires:

```
python3 (>= 3.8)
python3-wxgtk4.0 (>= 4.2.0)
python3-six (>= 1.16.0)
python3-pubsub
python3-watchdog (>= 3.0.0)
python3-chardet (>= 5.2.0)
python3-dateutil (>= 2.9.0)
python3-pyparsing (>= 3.1.3)
python3-lxml
python3-xdg
python3-keyring
python3-numpy
python3-lockfile (>= 0.12.2)
python3-gntp (>= 1.0.3)
python3-zeroconf (>= 0.50.0)
python3-squaremap (>= 1.0.5)
libxss1
xdg-utils
```

### Build Dependencies

```
debhelper-compat (= 13)
dh-python
python3-all
python3-setuptools
```

## Build System

Task Coach uses `setup.py` with setuptools. The `debian/rules` file should use:

```makefile
#!/usr/bin/make -f
%:
	dh $@ --with python3 --buildsystem=pybuild
```

## Submission Process

### 1. File an ITP (Intent To Package) Bug

```bash
reportbug --severity=wishlist --package=wnpp --subject="ITP: taskcoach -- Personal task manager"
```

### 2. Complete debian/ Directory

Create all required files listed above.

### 3. Build and Test

```bash
# Build source package
dpkg-buildpackage -us -uc -S

# Build binary package
dpkg-buildpackage -us -uc -b

# Run lintian
lintian --info --display-info *.changes
```

### 4. Fix Lintian Warnings

Address all errors and warnings from lintian.

### 5. Request Sponsorship

New packages require a Debian Developer sponsor:
- debian-mentors mailing list
- mentors.debian.net

## Existing Build Infrastructure

Task Coach has existing (but outdated) Debian build support:

- `buildlib/bdist_deb.py` - Custom distutils command for .deb building
- `build.in/debian/` - Legacy Debian files
- `Makefile` targets: `make deb`, `make ubuntu`

These need modernization:
- Update from `cdbs` to `dh` (debhelper)
- Update compat level from 9 to 13
- Update Standards-Version to 4.6.2+
- Remove Python 2 references

## Standards Compliance

### Required Updates

| Standard | Current | Required |
|----------|---------|----------|
| Debhelper compat | 9 | 13+ |
| Standards-Version | 4.1.1 | 4.6.2+ |
| Build system | cdbs | dh |
| Python | 2/3 mixed | Python 3 only |

### DEP-5 Copyright

The `debian/copyright` file must use machine-readable format:

```
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: taskcoach
Upstream-Contact: https://github.com/taskcoach/taskcoach
Source: https://github.com/taskcoach/taskcoach

Files: *
Copyright: 2004-2025 Task Coach developers
License: GPL-3+

Files: debian/*
Copyright: 2025 Package maintainer
License: GPL-3+

License: GPL-3+
 [Full license text or reference]
```

## References

- [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/)
- [DEP-3: Patch Tagging Guidelines](https://dep-team.pages.debian.net/deps/dep3/)
- [DEP-5: Machine-readable copyright](https://dep-team.pages.debian.net/deps/dep5/)
- [Python Policy](https://www.debian.org/doc/packaging-manuals/python-policy/)

## Related Documentation

- [CRITICAL_WXPYTHON_PATCH.md](CRITICAL_WXPYTHON_PATCH.md) - Detailed patch information
- [patches/wxpython/README.md](../patches/wxpython/README.md) - Patch installation methods
- [DEBIAN_BOOKWORM_SETUP.md](DEBIAN_BOOKWORM_SETUP.md) - Development setup on Bookworm
