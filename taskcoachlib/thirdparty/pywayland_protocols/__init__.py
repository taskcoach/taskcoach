"""Vendored pywayland protocol bindings.

The pywayland scanner generates Python bindings from Wayland protocol XML
files. Debian/Ubuntu's `python3-pywayland` 0.4.x only ships the core
`pywayland.protocol.wayland` module; staging protocols such as
ext-idle-notify-v1 are not included. Rather than depending on a newer
pywayland release or requiring users to run the scanner at install time,
we vendor pre-generated bindings here.

To regenerate (only needed when the upstream XML changes):

    python3 -m pywayland.scanner \\
        -o /tmp/pywl_gen \\
        -i /usr/share/wayland/wayland.xml \\
            /usr/share/wayland-protocols/staging/ext-idle-notify/ext-idle-notify-v1.xml

Then copy `ext_idle_notify_v1/` into this directory and patch the
`from ..wayland import WlSeat` line in `ext_idle_notifier_v1.py` to
import from `pywayland.protocol.wayland` instead (so we share the system
pywayland's wl_seat definition rather than vendoring our own).
"""
