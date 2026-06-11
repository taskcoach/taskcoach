# Flathub submission reference

These files are a **reference** for submitting Task Coach to
[Flathub](https://flathub.org). They are **not** built by this repo's CI - the
CI builds the dev manifest at `../io.github.taskcoach.TaskCoach.yaml` (which uses
a local `type: dir` source). For Flathub the app source must be a pinned
`type: git`, which is the only difference in the manifest here.

Full step-by-step is in [docs/FLATPAK.md](../../../docs/FLATPAK.md); this is the
quick checklist.

> **Postponed (2026).** Flathub blanket-rejects submissions it deems "AI slop"
> and **rejected this one** (prior review notes:
> <https://github.com/flathub/flathub/pull/8938>), so complying with its required
> changes is no longer relevant; the `.flatpak` is distributed **directly from
> this project's GitHub releases** instead. The external `flathub/…` fork has been
> removed; these files are kept as a reference for if/when it is revisited. The
> main blocker Flathub pushed for — the `--filesystem=home` → portal migration —
> is documented in [docs/FLATPAK.md](../../../docs/FLATPAK.md) (File access) and
> will likely resolve automatically with wxPython 3.3. The automated dev-vs-Flathub
> manifest parity check was removed; if revived, keep the two manifests in sync
> manually (see "Keeping it in sync" below).

## What goes in the Flathub repo

The submission is a PR to [`flathub/flathub`](https://github.com/flathub/flathub)
against the **`new-pr`** branch. At the **root** of your branch, place:

| File | Where it comes from |
|------|---------------------|
| `io.github.taskcoach.TaskCoach.yaml` | this dir (fill in the `commit:` SHA) |
| `python3-sources.json` | the `flatpak-pip-sources` CI artifact |
| `python3-build-deps.json` | the `flatpak-pip-sources` CI artifact |
| `shared-modules/` | `git submodule add https://github.com/flathub/shared-modules.git` |

The metainfo, desktop file, MIME definition and icons are **not** copied here -
the manifest installs them from the pinned app source (`type: git`) during the
build.

## Steps

1. Tag the release on `master` and note the commit:

   ```bash
   git tag v2.0.2.18 && git push origin v2.0.2.18
   git rev-parse v2.0.2.18
   ```

2. In `io.github.taskcoach.TaskCoach.yaml` here, replace
   `REPLACE_WITH_v2.0.2.18_COMMIT_SHA` with that SHA.

3. Download the latest **`flatpak-pip-sources`** artifact from the Flatpak CI run
   and extract `python3-sources.json` + `python3-build-deps.json`.

4. Fork `flathub/flathub`, branch off `new-pr`, add the four items above at the
   repo root, and open a PR titled `Add io.github.taskcoach.TaskCoach`.

   > Flathub bans AI-generated submission PRs - write the PR text and all review
   > replies yourself.

5. Prove ID ownership: sign in to flathub.org with the `github.com/taskcoach`
   account (2FA required).

6. Likely review points (justifications in
   [docs/FLATPAK.md](../../../docs/FLATPAK.md)): the **X11-only** display (runs via
   XWayland on Wayland); the idle `--talk-name` grants
   (`org.freedesktop.ScreenSaver` / `org.gnome.Mutter.IdleMonitor`) — there is no
   idle portal; and **`--filesystem=home`** (the portal migration that would drop
   it is postponed — see the File access section in docs/FLATPAK.md).

## Updates after the first submission (automated)

The initial submission above is a one-time manual step (Flathub bans automated
submission PRs). **Every release after that is automated by Flathub**, so there
is no GitHub Action to build on our side.

The `type: git` source carries an `x-checker-data` block (a `git` checker with
`tag-pattern: '^v([\d.]+)$'`). Flathub runs
[flatpak-external-data-checker](https://github.com/flathub-infra/flatpak-external-data-checker)
hourly against the app repo; when it sees a newer `v*` tag here, `flathubbot`
opens an update PR in the Flathub repo with the new tag + commit. So the release
flow is just:

1. Push a new `vX.Y.Z` tag in this repo (the existing release workflow does the
   GitHub release + bundle).
2. `flathubbot` opens the update PR in the Flathub repo within the hour.
3. Merge it (or set `automerge-flathubbot-prs: true` in the Flathub repo's
   `flathub.json` to skip the click). Flathub builds and publishes.

If the **pip dependencies** changed (a new dep or version, not just app code),
regenerate `python3-sources.json` / `python3-build-deps.json` (download them from
the release build's `flatpak-pip-sources` artifact) and include them in that PR;
for code-only releases the checker's app-source bump is enough.

## Keeping it in sync

If the dev manifest (`../io.github.taskcoach.TaskCoach.yaml`) changes, re-copy it
over the manifest here and re-apply the `type: git` source block (with its
`x-checker-data`), so this reference does not drift.
