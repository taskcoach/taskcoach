# Vendored: plasma-window-management pywayland binding

These modules are the `pywayland` bindings for KDE's
`org_kde_plasma_window_management` Wayland protocol, used by the
KDE-Wayland tray minimize/restore backend (`KdePlasmaController`; see
`docs/SYSTEM_TRAY.md`, "Window Show/Hide on Wayland").

Vendored for the same reason as `../ext_idle_notify_v1`: distribution
`python3-pywayland` ships only the core `wayland` protocol, so
`pywayland.protocol.plasma_window_management` never exists at runtime.
This is standard Wayland practice (commit the scanner output, like the
C ecosystem commits `wayland-scanner` output).

## Provenance

- Protocol XML: KDE `plasma-wayland-protocols`,
  `src/protocols/plasma-window-management.xml` (protocol
  `plasma_window_management`; `org_kde_plasma_window_management` and
  `org_kde_plasma_window` are interface version 20).
- Generator: `pywayland-scanner` from pywayland 0.4.18 (the version
  packaged by Debian Trixie, Fedora and Arch).

## Regeneration

```
curl -fsSL -o /tmp/pwm.xml \
  https://raw.githubusercontent.com/KDE/plasma-wayland-protocols/master/src/protocols/plasma-window-management.xml
pywayland-scanner -i /usr/share/wayland/wayland.xml /tmp/pwm.xml -o /tmp/out
cp /tmp/out/plasma_window_management/*.py \
  taskcoachlib/thirdparty/plasma_window_management/
```

Then re-apply the two local modifications below.

## Local modifications (re-apply after regeneration)

1. In `org_kde_plasma_window.py`, the two cross-protocol imports

   ```
   from ..wayland import WlOutput
   from ..wayland import WlSurface
   ```

   are repointed to the installed core pywayland:

   ```
   from pywayland.protocol.wayland import WlOutput
   from pywayland.protocol.wayland import WlSurface
   ```

   so the package is self-contained against the stock distribution
   `python3-pywayland` without vendoring the entire core protocol.

2. In `org_kde_plasma_window.py`, the `virtual_desktop_left` event's
   argument is literally named `is` in the protocol XML
   (`<arg name="is" .../>`), a Python keyword. pywayland-scanner
   0.4.18 does not sanitize it and emits invalid Python
   (`def virtual_desktop_left(self, is: str)`, `self._post_event(12,
   is)`). The parameter is renamed `is` to `is_` (signature,
   docstring and body). This is behavior-preserving: the wire
   argument is positional via the `Argument(ArgumentType.String)`
   decorator, so the Python parameter name is irrelevant to
   marshalling. This event is a server-to-client event Task Coach
   does not send, but the module must still be syntactically valid to
   import.
