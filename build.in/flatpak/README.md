# Flatpak packaging for Task Coach

Files here build Task Coach as a Flatpak, alongside the AppImage. Full
documentation is in [docs/FLATPAK.md](../../docs/FLATPAK.md).

| File | Purpose |
|------|---------|
| `io.github.taskcoach.TaskCoach.yaml` | Flatpak manifest (GNOME runtime) |
| `io.github.taskcoach.TaskCoach.metainfo.xml` | AppStream metadata (required by Flathub) |
| `io.github.taskcoach.TaskCoach.desktop` | Desktop entry (named by app ID) |
| `io.github.taskcoach.TaskCoach.mime.xml` | MIME definition so `.tsk` files open Task Coach |
| `generate-pip-sources.sh` | Generates the pinned pip sources the manifest includes (run before building) |
| `python3-sources.json`, `python3-build-deps.json` | Generated, git-ignored; the pinned pip sources the manifest includes |
| `shared-modules/` | Git submodule: Flathub's maintained libappindicator (tray) chain |

## Quick local build

```bash
# 1. Fetch the shared-modules submodule (tray chain) and the runtime + SDK.
git submodule update --init build.in/flatpak/shared-modules
flatpak install -y flathub org.gnome.Platform//50 org.gnome.Sdk//50

# 2. Generate the pinned pip sources the manifest includes (needs the SDK above
#    for --runtime ABI detection). This is the only step that uses the network.
build.in/flatpak/generate-pip-sources.sh

# 3. Build and install for the current user -- the build itself is offline.
flatpak-builder --user --install --force-clean \
    build/flatpak build.in/flatpak/io.github.taskcoach.TaskCoach.yaml

# 4. Run.
flatpak run io.github.taskcoach.TaskCoach
```

Or use `scripts/build-flatpak.sh`, which wraps these steps and also produces a
single-file `.flatpak` bundle.

## Known open items

- **wxPython** is built from the sdist, letting it compile its own bundled
  wxWidgets (so the version matches its bindings). It compiles slowly; CI reuses
  the cached stage across commits. See [docs/FLATPAK.md](../../docs/FLATPAK.md).
- **System tray** uses Flathub's maintained `shared-modules` libappindicator
  (git submodule at `shared-modules/`); run `git submodule update --init` before
  building locally. See [docs/FLATPAK.md](../../docs/FLATPAK.md).
- **Idle detection** is enabled via bundled `dbus-python`.
- For **Flathub**: commit the generated `python3-*.json` and swap the `taskcoach`
  module's `type: dir` for a pinned `git`/`archive` source. See
  [docs/FLATPAK.md](../../docs/FLATPAK.md).
