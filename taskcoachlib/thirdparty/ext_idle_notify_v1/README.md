# Vendored: ext-idle-notify-v1 pywayland binding

These three modules are the `pywayland` bindings for the
`ext-idle-notify-v1` Wayland protocol, used by the `ext_idle_notify`
idle-detection backend (see `docs/IDLE.md`).

They are vendored because the distribution `python3-pywayland`
packages ship **only the core `wayland` protocol**; protocol
extensions are not included by design, so
`pywayland.protocol.ext_idle_notify_v1` never exists at runtime. This
is the standard Wayland practice (the C ecosystem commits
`wayland-scanner` output; Rust ships the `wayland-protocols` crate).

## Provenance

- Protocol XML: wayland-protocols, `staging/ext-idle-notify/ext-idle-notify-v1.xml`
  (protocol `ext_idle_notify_v1`, interfaces version 2).
- Generator: `pywayland-scanner` from pywayland 0.4.18 (the version
  packaged by Debian Trixie, Fedora and Arch; generated code is
  stable across the 0.4.x line).

## Regeneration

```
pywayland-scanner -i /usr/share/wayland/wayland.xml \
    /usr/share/wayland-protocols/staging/ext-idle-notify/ext-idle-notify-v1.xml \
    -o /tmp/out
cp /tmp/out/ext_idle_notify_v1/*.py taskcoachlib/thirdparty/ext_idle_notify_v1/
```

## Local modification

One line in `ext_idle_notifier_v1.py` is changed from the generated
output: the cross-protocol import

```
from ..wayland import WlSeat
```

is repointed to the installed core pywayland:

```
from pywayland.protocol.wayland import WlSeat
```

so the package is self-contained against the stock distribution
`python3-pywayland` (which provides `pywayland.protocol_core` and
`pywayland.protocol.wayland`) without vendoring the entire core
protocol. Re-apply this after any regeneration.
