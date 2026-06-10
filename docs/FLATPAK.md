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
| [`build.in/flatpak/io.github.taskcoach.TaskCoach.yaml`](../build.in/flatpak/io.github.taskcoach.TaskCoach.yaml) | Manifest |
| [`build.in/flatpak/io.github.taskcoach.TaskCoach.metainfo.xml`](../build.in/flatpak/io.github.taskcoach.TaskCoach.metainfo.xml) | AppStream metadata (required by Flathub) |
| [`build.in/flatpak/io.github.taskcoach.TaskCoach.desktop`](../build.in/flatpak/io.github.taskcoach.TaskCoach.desktop) | Desktop entry, named by app ID |
| [`build.in/flatpak/generate-pip-sources.sh`](../build.in/flatpak/generate-pip-sources.sh) | Generates the pinned pip sources the manifest includes (ABI-correct via the runtime): runtime deps + wxPython's build backends |
| [`build.in/flatpak/io.github.taskcoach.TaskCoach.mime.xml`](../build.in/flatpak/io.github.taskcoach.TaskCoach.mime.xml) | MIME definition so `.tsk` files open Task Coach |
| `build.in/flatpak/shared-modules/` | Git submodule: Flathub's maintained libappindicator (tray) chain |
| [`scripts/build-flatpak.sh`](../scripts/build-flatpak.sh) | Local build + bundle (generates sources, then builds offline) |
| [`.github/workflows/build-flatpak.yml`](../.github/workflows/build-flatpak.yml) | CI: generate sources, offline build, lint, release upload |

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
| `--socket=x11`, `--share=ipc`, `--device=dri`, `--env=GDK_BACKEND=x11` | Display and rendering. X11-only: wxPython's AUI docking is unusable on native Wayland ([AUI_WAYLAND_ISSUES.md](AUI_WAYLAND_ISSUES.md)), so Task Coach declares as an X11 app and runs via XWayland on Wayland sessions. Per Flathub, an app without native Wayland support uses `--socket=x11`; also granting `--socket=wayland` is a lint error (`finish-args-contains-both-x11-and-wayland`) and would not provide X11 on Wayland anyway. |
| `--filesystem=home` | Read/write `.tsk` task files anywhere; wx uses its own file dialogs, not the portal. Reviewers may push to narrow this. |
| `--talk-name=org.kde.StatusNotifierWatcher` | System-tray icon |
| `--talk-name=org.freedesktop.ScreenSaver`, `--talk-name=org.gnome.Mutter.IdleMonitor` | Optional idle detection ([IDLE.md](IDLE.md)) |
| `--talk-name=org.freedesktop.secrets` | keyring |

There is intentionally **no** `org.freedesktop.Notifications` grant: reminders
and idle alerts are in-app `wx` popups, so the app never calls the host
notification service. If real desktop notifications are added later, route them
through the freedesktop **notification portal** (which needs no `talk-name`),
not a direct grant.

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

The first instinct is to install a prebuilt wheel, but **there is no usable
prebuilt wxPython for the runtime**. wxPython does not publish manylinux wheels
on PyPI (manylinux ships a GTK too old for wxWidgets), and the distro-specific
wheels at extras.wxpython.org are built against a given distro's libraries and
break under the GNOME runtime from ABI skew (the classic `libSDL2`/`libffi`
import failures). So PyPI serves only the sdist for Linux, and we compile.

The second instinct (used by some Flathub apps like KiCad) is `--use_syswx`:
build wxWidgets as a separate module and link it. That only works when the
system wxWidgets is the **exact** version wxPython's pre-generated bindings
expect; building wxPython 4.2.5 against wxWidgets 3.2.6 fails with errors like
`wxWARN_UNUSED was not declared`, and pinning the precise snapshot per wxPython
release is fragile.

So we do **not** use `--use_syswx`. The wxPython sdist ships the matching
wxWidgets source (it is ~56MB for this reason), and we let `build.py` compile
that bundled wxWidgets and then Phoenix against it. The versions are guaranteed
to match. Offline, pip cannot fetch wxPython's PEP 518 build backends
(setuptools/cython/sip/requests), so they are pinned in
`python3-build-deps.json` (installed before wxPython) and the module
builds with `--no-build-isolation`.

The cost is a long build (wxWidgets + wxPython compile, tens of minutes). To
avoid repeating it, CI caches the `.flatpak-builder` state-dir with
`actions/cache` rather than the builder action's own caching. The difference
matters: the builder action only uploads the cache **on success**, so a build
that fails partway (common while iterating) discards every compiled module and
the next run recompiles wxWidgets from scratch. `actions/cache` saves in a
post-job step that runs on failure too, so partial progress persists and
flatpak-builder rebuilds only what changed. The key is per-commit (so a fresh
cache is always saved) with a `flatpak-builder-x86_64-` prefix restore-key (so
the latest prior cache is restored). The builder action's own `cache` /
`restore-cache` are disabled to avoid double-managing the same directory.

A small **`glu`** module is built first because the GNOME SDK ships `libGL` but
not the legacy `GLU` (`glu.h`) that wxWidgets' OpenGL (glcanvas) support needs.
Checksums in the manifest are real (verified against the GLU and PyPI artifacts).

### `--ignore-installed` for the Python deps

The generated runtime-deps module (`python3-sources.json`) installs with
`pip3 ... --ignore-installed` (injected by `generate-pip-sources.sh`). The build
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

### One offline build, the way Flathub builds

There is a **single** manifest and it builds **offline**: no `--share=network`
in any module, exactly as Flathub requires. Every Python dependency is a pinned
source. `generate-pip-sources.sh` produces the two generated sub-manifests the
manifest includes -- `python3-sources.json` (runtime deps) and
`python3-build-deps.json` (wxPython's build backends) -- using
`flatpak-pip-generator` with `--runtime` so wheels pin the runtime's exact ABI.
Both JSON files are git-ignored: CI and `scripts/build-flatpak.sh` regenerate
them before each build. (Declared sources are still *downloaded* in the
source-prep phase; what is forbidden, and absent here, is network during the
build/compile phase.)

For the Flathub repo, generate the two JSON files and **commit** them (Flathub
does not generate at build time), and swap the app source as in step 1 below.

## Building locally

```bash
# 1. Runtime + SDK.
flatpak remote-add --user --if-not-exists flathub \
    https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user -y flathub org.gnome.Platform//50 org.gnome.Sdk//50

# 2. Generate the pinned pip sources the manifest includes (needs the SDK above
#    for --runtime ABI detection). This is the only step that uses the network.
build.in/flatpak/generate-pip-sources.sh

# 3. Build, install, run -- the build itself is offline.
flatpak-builder --user --install --force-clean \
    build/flatpak build.in/flatpak/io.github.taskcoach.TaskCoach.yaml
flatpak run io.github.taskcoach.TaskCoach
```

`scripts/build-flatpak.sh` wraps all of this (including step 2) and also exports
a single-file `.flatpak` bundle.

## CI

`.github/workflows/build-flatpak.yml` runs inside the
`flathub-infra/flatpak-github-actions:gnome-50` container (flatpak +
flatpak-builder + flatpak-builder-lint + SDK preinstalled). It generates the
pinned pip sources, builds the offline manifest with the official
`flatpak/flatpak-github-actions/flatpak-builder` action, runs
`flatpak-builder-lint` (manifest / appstream / repo), uploads the `.flatpak`
bundle plus the generated sources as artifacts, and attaches the bundle to the
GitHub Release on a `v*` tag. The build cache key is the action default so the
slow wxPython compile is reused across commits (see the wxPython section).

## Distribution

### Direct bundle (from a GitHub release)

The `.flatpak` bundle can be installed directly, no Flathub needed:

```bash
flatpak install ./TaskCoach-X.Y.Z.W-x86_64.flatpak
flatpak run io.github.taskcoach.TaskCoach
```

Caveats: the user needs `flatpak` installed; the bundle contains the app but
not the runtime, so the first install fetches `org.gnome.Platform` from Flathub
(the bundle records this via `--runtime-repo`); and a directly-installed bundle
does not auto-update (re-download to update).

### Flathub (managed, auto-updating)

Flathub builds, signs, and auto-updates the app for users. Publishing is a PR to
the [`flathub/flathub`](https://github.com/flathub/flathub) repo against the
`new-pr` branch; after merge, Flathub's buildbot builds and publishes and pushes
updates to the per-app repo. The concrete prerequisites are in
[Before submitting to Flathub](#before-submitting-to-flathub) below.

### Self-hosted remote

Because Flatpak is decentralized, you can instead host your own OSTree repo
(static, or via `flat-manager`) and have users `flatpak remote-add` it. This
keeps auto-updates without Flathub.

## Before submitting to Flathub

Submission is a pull request to
[`flathub/flathub`](https://github.com/flathub/flathub) against the **`new-pr`**
branch (PR title `Add io.github.taskcoach.TaskCoach`); a bot builds it and
volunteer reviewers check the build, permissions, metadata, and licensing. See
the Flathub
[submission](https://docs.flathub.org/docs/for-app-authors/submission) and
[requirements](https://docs.flathub.org/docs/for-app-authors/requirements) docs.

### Already satisfied

- **App ID** `io.github.taskcoach.TaskCoach`: valid `io.github.` code-hosting
  prefix with 4 components; matches the metainfo `<id>` and the desktop filename.
- **Offline, pinned build (no network).** The single manifest builds offline:
  no `--share=network` in any module. Runtime deps and wxPython's build backends
  are pinned (`generate-pip-sources.sh`), wxPython builds `--no-build-isolation`,
  and every other source carries a real `sha256`. CI builds it this way and runs
  `flatpak-builder-lint`.
- **Icon**: scalable SVG plus a real 256 PNG, installed under the app-id
  namespace in a proper `hicolor` theme dir.
- **Desktop file**: present, named by app ID, `StartupWMClass` matches wx's
  class; the `application/x-taskcoach` MIME type it declares is registered
  (`.mime.xml` + metainfo `<provides>`), so `.tsk` files open the app.
- **Metainfo**: id, license, developer, `content_rating`, `url`s, current 2.x
  screenshots, and a `<releases>` entry with notes.
- **Permissions**: no notification grant; only tray, idle, and keyring
  talk-names. Display is **X11-only** (`--socket=x11`, no wayland socket) so the
  `finish-args-contains-both-x11-and-wayland` lint error does not apply; see the
  finish-args table above. `--filesystem=home` is a deliberate, justified grant
  (item 2).
- **shared-modules**: pinned as a git submodule, as Flathub expects for deps.

### Required before submission

1. **Pin the app source.** In the Flathub repo's manifest, replace the
   `taskcoach` module's `type: dir` (local tree, used by our own CI) with a
   pinned `type: git` (tag plus commit) or `type: archive` (release tarball plus
   `sha256`) from `github.com/taskcoach/taskcoach`. Also commit the two generated
   `python3-*.json` files there (Flathub does not generate at build time).
2. **Justify `--filesystem=home` in review (decided: keep it).** The
   `finish-args-home-filesystem-access` lint error is not an auto-reject; it
   triggers reviewer discussion. We keep the grant because Task Coach is a
   file-centric app: users open/save `.tsk` files (plus attachments and
   HTML/CSV/iCal exports) at arbitrary paths, and wx uses its own file dialogs
   rather than the XDG file-chooser portal, so a narrowed grant (e.g.
   `--filesystem=xdg-documents`) would make any `.tsk` outside that folder
   unopenable. The portal route is an upstream wx change, not a packaging tweak.
   If a reviewer insists, narrowing is the fallback then.
3. **Remaining lint is understood.** CI runs the `manifest`, `appstream`, and
   `repo` checks (the same ones Flathub runs). After the X11-only change the
   open items are exactly two: `finish-args-home-filesystem-access` (intentional,
   item 2) and the `appstream` screenshot errors, which only fire because the
   metainfo screenshot URLs point at `master` where the images land on merge.
   Reproduce locally with:
   ```bash
   flatpak install -y flathub org.flatpak.Builder
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder \
       manifest build.in/flatpak/io.github.taskcoach.TaskCoach.yaml
   flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
   ```
4. **Verify ID ownership.** Ownership of `io.github.taskcoach.*` is proven by
   signing into Flathub with the GitHub account that controls
   `github.com/taskcoach`. That account needs **2FA** enabled (required to accept
   write access to the per-app repo after merge).

### Troubleshooting notes

- **wxPython** is the slow module (wxWidgets + Phoenix compile, tens of minutes).
  A cold CI cache pays that once; later runs reuse the cached stage. If it fails
  fetching build backends, confirm `python3-build-deps.json` was
  generated and is included before the wxPython module.
- **System tray**: if the app reports a missing `AppIndicator3` typelib at
  runtime, confirm the submodule was checked out and the `-introspection-`
  variant is referenced. If the tray shows a generic icon, confirm the icons
  landed under `/app/share/icons/hicolor/<size>/apps/` (a valid theme dir), not
  `/app/share/icons/<size>/`.

Sources: [Flathub submission](https://docs.flathub.org/docs/for-app-authors/submission),
[Flathub requirements](https://docs.flathub.org/docs/for-app-authors/requirements),
[flatpak-builder-lint](https://github.com/flathub-infra/flatpak-builder-lint).
