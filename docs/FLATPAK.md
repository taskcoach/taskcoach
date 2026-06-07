# Flatpak Packaging

This document covers the Flatpak build for Task Coach: the design decisions,
how to build locally, the CI workflow, distribution options, and the known
open items. It complements the high-level entry in [PACKAGING.md](PACKAGING.md).

Flatpak is offered **in addition to** the AppImage, not as a replacement. The
two solve different problems:

- **AppImage**: one self-contained file, no install, no prerequisites; you own
  the library-bundling fragility (see [APPIMAGE.md](APPIMAGE.md)).
- **Flatpak**: runs against a shared, versioned **runtime**, so the GTK / glib /
  PyGObject / gobject-introspection stack is one consistent set provided by the
  platform. The AppImage's ABI/bundling problems do not exist here, at the cost
  of needing `flatpak` installed and (on first install) fetching the runtime.

## Project files

| File | Purpose |
|------|---------|
| [`build.in/flatpak/org.taskcoach.TaskCoach.yaml`](../build.in/flatpak/org.taskcoach.TaskCoach.yaml) | Manifest |
| [`build.in/flatpak/org.taskcoach.TaskCoach.metainfo.xml`](../build.in/flatpak/org.taskcoach.TaskCoach.metainfo.xml) | AppStream metadata (required by Flathub) |
| [`build.in/flatpak/org.taskcoach.TaskCoach.desktop`](../build.in/flatpak/org.taskcoach.TaskCoach.desktop) | Desktop entry, named by app ID |
| [`build.in/flatpak/generate-pip-sources.sh`](../build.in/flatpak/generate-pip-sources.sh) | Generates pinned Python sources |
| `build.in/flatpak/shared-modules/` | Git submodule: Flathub's maintained libappindicator (tray) chain |
| [`scripts/build-flatpak.sh`](../scripts/build-flatpak.sh) | Local build + bundle |
| [`.github/workflows/build-flatpak.yml`](../.github/workflows/build-flatpak.yml) | CI build + release upload |

## Design decisions

### Runtime: GNOME, not freedesktop

The manifest uses `org.gnome.Platform` rather than `org.freedesktop.Platform`
because the GNOME runtime bundles **GTK3, PyGObject, and gobject-introspection**.
Task Coach needs all three: wxPython is the gtk3 build, and the system-tray
backend in `taskcoachlib/gui/appindicator.py` is written against PyGObject. With
the GNOME runtime everything in the process shares a single GTK/glib/GObject
type system, which is exactly the property the AppImage cannot guarantee.

Bump `runtime-version` as runtimes reach end of life; Flathub will flag an EOL
runtime.

### Permissions (finish-args)

Each grant in the manifest is there for a reason; keep the set minimal for
Flathub review:

| Grant | Why |
|-------|-----|
| `--socket=wayland`, `--socket=fallback-x11`, `--share=ipc`, `--device=dri` | Display and rendering |
| `--filesystem=home` | Read/write `.tsk` task files anywhere; wx uses its own file dialogs, not the portal. Reviewers may push to narrow this. |
| `--talk-name=org.freedesktop.Notifications` | Reminders |
| `--talk-name=org.kde.StatusNotifierWatcher` | System-tray icon |
| `--talk-name=org.freedesktop.ScreenSaver`, `--talk-name=org.gnome.Mutter.IdleMonitor` | Optional idle detection ([IDLE.md](IDLE.md)) |
| `--talk-name=org.freedesktop.secrets` | keyring |

### System tray (via Flathub shared-modules)

System-tray support comes from **Flathub's maintained
[`shared-modules`](https://github.com/flathub/shared-modules)**, referenced as a
git submodule at `build.in/flatpak/shared-modules`. The manifest pulls in one
file:

```
- shared-modules/libappindicator/libappindicator-gtk3-introspection-12.10.json
```

That single file bundles the whole `intltool` -> `dbus-glib` -> `libdbusmenu` ->
`libindicator` -> `libappindicator` chain, **with Flathub's patches** for the
exact build breakages a hand-rolled chain hits (e.g. libdbusmenu's
`HAVE_VALGRIND`/automake and `-Werror` issues). Flathub CI guarantees it builds
against current and oldstable Freedesktop/GNOME SDKs, so this is the robust,
maintained path rather than pinning fragile upstream tarballs ourselves.

The `-introspection-` variant ships the `AppIndicator3-0.1` typelib. The
PyGObject backend in `taskcoachlib/gui/appindicator.py` tries
`AyatanaAppIndicator3` first and then falls back to `AppIndicator3`, so it picks
this up with no app-code change (Flatpak puts `/app/lib/girepository-1.0` on the
GI path; PyGObject itself comes from the GNOME runtime).

CI checks out the submodule (`submodules: recursive`) and
`scripts/build-flatpak.sh` runs `git submodule update --init`. To update the
chain later, bump the submodule: `git -C build.in/flatpak/shared-modules pull`.

The desktop still needs an SNI host (e.g. the GNOME AppIndicator extension) for
the icon to actually appear; that is outside any package's control. Per the
[Flatpak docs](https://docs.flatpak.org/en/latest/desktop-integration.html) the
`--talk-name=org.kde.StatusNotifierWatcher` grant (present in `finish-args`) is
required, and libappindicator also provides an XEmbed fallback for shells
without SNI.

### wxPython: build from source, let it build its own wxWidgets

The first instinct is to install the binary wheel, but it may not match the
runtime GTK, so we build wxPython from the sdist instead. The second instinct
(used by some Flathub apps like KiCad) is `--use_syswx`: build wxWidgets as a
separate module and link it. That only works when the system wxWidgets is the
**exact** version wxPython's pre-generated bindings expect; building wxPython
4.2.5 against wxWidgets 3.2.6 fails with errors like `wxWARN_UNUSED was not
declared`, and pinning the precise snapshot per wxPython release is fragile.

So we do **not** use `--use_syswx`. The wxPython sdist ships the matching
wxWidgets source (it is ~56MB for this reason), and we let `build.py` compile
that bundled wxWidgets and then Phoenix against it. The versions are guaranteed
to match. The cost is a long build (wxWidgets + wxPython compile, several
minutes); the flatpak-builder cache makes reruns fast.

A small **`glu`** module is built first because the GNOME SDK ships `libGL` but
not the legacy `GLU` (`glu.h`) that wxWidgets' OpenGL (glcanvas) support needs.
Checksums in the manifest are real (verified against the GLU and PyPI artifacts).

### `--ignore-installed` for the Python deps

The `python3-deps` module installs with `pip3 ... --ignore-installed`. The build
runs against `org.gnome.Sdk`, which ships some of these modules (notably
`python3-lxml`). Without `--ignore-installed`, pip treats them as already
satisfied (from the SDK) and skips installing them into `/app`, so they are
**missing at runtime** against `org.gnome.Platform` (which does not include
them). This manifested as `ModuleNotFoundError: No module named 'lxml'` on first
launch even though the build succeeded.

The set also includes **`dbus-python`**, which enables the optional idle-time
detection feature (its D-Bus backend does `import dbus`); the matching
`org.freedesktop.ScreenSaver` / `org.gnome.Mutter.IdleMonitor` talk-name grants
are in `finish-args`.

### Network during build vs Flathub offline

Our own CI/local builds let the python modules use `--share=network` so pip can
fetch the wxPython/wxWidgets sources, build backends, and the pure-Python deps.
A **Flathub** submission must build fully offline: remove `--share=network` and
provide pinned sources with `generate-pip-sources.sh` (which uses
`flatpak-pip-generator` to produce a git-ignored `python3-sources.json`). The
helper is kept for exactly that path.

## Building locally

```bash
# 1. Runtime + SDK.
flatpak remote-add --user --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user -y flathub org.gnome.Platform//50 org.gnome.Sdk//50

# 2. Build, install, run. The python modules fetch their own sources over the
#    network (--share=network in the manifest); nothing to pre-generate.
flatpak-builder --user --install --force-clean \
    build/flatpak build.in/flatpak/org.taskcoach.TaskCoach.yaml
flatpak run org.taskcoach.TaskCoach
```

`scripts/build-flatpak.sh` wraps all of this and also exports a single-file
`.flatpak` bundle.

## CI

`.github/workflows/build-flatpak.yml` runs inside the
`flathub-infra/flatpak-github-actions:gnome-50` container (flatpak +
flatpak-builder + SDK preinstalled), builds with the official
`flatpak/flatpak-github-actions/flatpak-builder` action (the manifest's python
modules fetch their own sources via `--share=network`), uploads the `.flatpak`
bundle as an artifact, and attaches it to the GitHub Release on a `v*` tag.
This matches the AppImage workflow's trigger and release pattern.

## Distribution

### Direct bundle (from a GitHub release)

The `.flatpak` bundle can be installed directly, no Flathub needed:

```bash
flatpak install ./TaskCoach-X.Y.Z.W-x86_64.flatpak
flatpak run org.taskcoach.TaskCoach
```

Caveats: the user needs `flatpak` installed; the bundle contains the app but
not the runtime, so the first install fetches `org.gnome.Platform` from Flathub
(the bundle records this via `--runtime-repo`); and a directly-installed bundle
does not auto-update (re-download to update).

### Flathub (managed, auto-updating)

To publish on Flathub:

1. Pin everything: replace the `taskcoach` module's `type: dir` source with a
   pinned `git`/`archive`, and commit a generated `python3-sources.json` (plus
   pin any tray modules to commits if tray support has been added by then).
2. Replace the placeholder screenshots in the metainfo with real hosted images
   and validate with `appstreamcli validate`.
3. Open a PR adding the manifest to the
   [`flathub/flathub`](https://github.com/flathub/flathub) repo (`new-pr`
   branch). A bot builds it; reviewers check the build, permissions, metadata,
   and licensing.
4. After merge, Flathub's own buildbot builds and publishes; updates are pushed
   to the per-app Flathub repo.

### Self-hosted remote

Because Flatpak is decentralized, you can instead host your own OSTree repo
(static, or via `flat-manager`) and have users `flatpak remote-add` it. This
keeps auto-updates without Flathub.

## Known open items

This needs a real `flatpak-builder` pass to confirm, ideally in CI:

- **wxPython** uses the proven source-build pattern, so it should work, but the
  wxWidgets + wxPython compile is slow (several minutes) and is the most likely
  place for a first-build failure. The flatpak-builder cache makes reruns fast.
- **System tray** uses Flathub `shared-modules` (git submodule), so the
  appindicator build is the CI-maintained upstream one. If the app reports a
  missing `AppIndicator3` typelib at runtime, confirm the submodule was checked
  out and that the `-introspection-` variant is the one referenced.
- **Screenshots** in the metainfo are placeholders.
- For **Flathub**: drop `--share=network`, generate offline sources, and replace
  the `taskcoach` module's `type: dir` with a pinned source. (shared-modules is
  already submodule-pinned, which Flathub expects.)
