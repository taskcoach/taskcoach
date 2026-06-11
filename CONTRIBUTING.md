# Contributing

## Code style

- **Format the files you touch with [black](https://github.com/psf/black)**,
  line-length 79 (configured in `pyproject.toml`, `[tool.black]`). black output
  is PEP 8 compliant; running it is the standard way to fix whitespace and
  wrapping.
- **Lint with flake8.** Some codes are expected and must NOT be "fixed" — e.g.
  `N802/N803/N812/N813` on wxPython's mixed-case method/argument names.

Rationale and the full fix-vs-ignore list:
[docs/PEP8_MIGRATION.md](docs/PEP8_MIGRATION.md).

## Building and packaging

Per-target build docs live in [docs/](docs/): [PACKAGING.md](docs/PACKAGING.md),
[FLATPAK.md](docs/FLATPAK.md), [APPIMAGE.md](docs/APPIMAGE.md), and the
platform notes (WINDOWS, MACOS, DEBIAN_*).
