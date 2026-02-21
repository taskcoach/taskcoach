"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>

Task Coach is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Task Coach is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""Read-only settings shim. See docs/SETTINGS.md for design."""

from types import SimpleNamespace
from . import defaults
from taskcoachlib.meta.debug import log_step
from taskcoachlib import patterns

import wx

_LEGACY_DEBOUNCE_MS = 1000

# Sections monitored by the shim — add entries as code is migrated.
_SETTING_SECTIONS = {
    "icon",
    "iconpicker",
    "view",
    "window",
}

# Explicit type map — add entries as code is migrated to use this shim.
# Settings not listed here are returned as raw strings.
_TYPES_MAP = {
    ("view", "descriptionpopups"): bool,
    ("window", "hoverlinewidth"): int,
    ("icon", "legacystatusicons"): bool,
    ("iconpicker", "theme_nuvola"): bool,
    ("iconpicker", "theme_oxygen"): bool,
    ("iconpicker", "theme_papirus"): bool,
    ("iconpicker", "theme_breeze"): bool,
    ("iconpicker", "theme_noto_emoji"): bool,
    ("iconpicker", "theme_taskcoach"): bool,
    ("iconpicker", "search_include_theme"): bool,
    ("iconpicker", "search_include_context"): bool,
}


_SETTINGS2_CHANGED_EVENT_TYPE = "settings2.changed"


class _Settings2:
    """Singleton read-only settings shim."""

    _initialized = False
    _debounce_timer = None

    def schedule_refresh(self):
        """Reset debounce timer. No-op before init()."""
        if not self._initialized:
            return
        if self._debounce_timer is None:
            self._debounce_timer = wx.CallLater(_LEGACY_DEBOUNCE_MS, self._on_debounce)
        else:
            self._debounce_timer.Restart(_LEGACY_DEBOUNCE_MS)

    def _notify_changed(self):
        """Fire Publisher signal after refresh or recomputation."""
        patterns.Event(_SETTINGS2_CHANGED_EVENT_TYPE, self).send()

    def _on_debounce(self):
        """Debounce timer fired. Refresh snapshot and signal listeners."""
        self._refresh(build=False)
        self._notify_changed()

    def _on_system_theme_colour_changed(self, event):
        """System colour changed. Recompute display-dependent settings."""
        self._compute_settings_all()
        self._notify_changed()

    def _refresh(self, build=False):
        """Walk all ConfigParser sections and snapshot values.

        build=True  (init): create section namespaces and populate values.
        build=False (signal): update values on existing namespaces.
        """
        settings = self._settings
        for settings_section_id in _SETTING_SECTIONS:
            options = None
            if not settings.has_section(settings_section_id):
                log_step(
                    "ERROR: Section [%s] missing from ConfigParser"
                    % settings_section_id,
                    prefix="SETTINGS",
                )
            elif build:
                if hasattr(self, settings_section_id):
                    log_step(
                        "Duplicate section [%s] during build"
                        % settings_section_id,
                        prefix="SETTINGS",
                    )
                    options = None
                else:
                    options = SimpleNamespace()
                    setattr(self, settings_section_id, options)
            else:
                options = getattr(self, settings_section_id, None)
                if options is None:
                    log_step(
                        "Missing section [%s] during refresh"
                        % settings_section_id,
                        prefix="SETTINGS",
                    )
            if options is not None:
                for option_id in settings.options(settings_section_id):
                    option_exists = hasattr(options, option_id)
                    if build and option_exists:
                        log_step(
                            "ERROR: Duplicate option [%s] %s during build"
                            % (settings_section_id, option_id),
                            prefix="SETTINGS",
                        )
                    elif not build and not option_exists:
                        log_step(
                            "ERROR: New option [%s] %s during refresh"
                            % (settings_section_id, option_id),
                            prefix="SETTINGS",
                        )
                    else:
                        raw = settings.get(settings_section_id, option_id)
                        setattr(options, option_id, self._parse_value(settings_section_id, option_id, raw))
        self._compute_settings_all()


    def _compute_settings_all(self):
        """Compute all computed settings from snapshotted values."""
        self._compute_theme()

    def _compute_theme(self):
        """Compute window.theme_is_dark from window.theme."""
        window = getattr(self, "window", None)
        if window is not None:
            theme = getattr(window, "theme", "automatic")
            if theme == "dark":
                window.theme_is_dark = True
            elif theme == "light":
                window.theme_is_dark = False
            else:
                # "automatic" — detect from system
                from taskcoachlib.application.application import detect_dark_theme
                window.theme_is_dark = detect_dark_theme()


    def _get_default(self, settings_section_id, option_id):
        """Return the default value for a setting, converted to its mapped type."""
        raw = defaults.defaults[settings_section_id][option_id]
        typ = _TYPES_MAP.get((settings_section_id, option_id))
        if typ is bool:
            val = raw == "True"
        elif typ is int:
            val = int(raw)
        else:
            val = raw
        return val

    def _parse_value(self, settings_section_id, option_id, raw):
        """Type-convert a raw setting value, log bad values."""
        typ = _TYPES_MAP.get((settings_section_id, option_id))
        if typ is bool:
            if raw in ("True", "False"):
                val = raw == "True"
            else:
                val = self._get_default(settings_section_id, option_id)
                log_step(
                    "Bad bool for [%s] %s=%r, using default %r"
                    % (settings_section_id, option_id, raw, val),
                    prefix="SETTINGS",
                )
        elif typ is int:
            try:
                val = int(raw)
            except (ValueError, TypeError):
                val = self._get_default(settings_section_id, option_id)
                log_step(
                    "Bad int for [%s] %s=%r, using default %r"
                    % (settings_section_id, option_id, raw, val),
                    prefix="SETTINGS",
                )
        else:
            val = raw
        return val


_instance = _Settings2()


def __getattr__(name):
    """Module-level attribute access delegates to singleton (PEP 562)."""
    return getattr(_instance, name)


def init(settings):
    """Called once from application.py after Settings is created."""
    _instance._settings = settings
    _instance._refresh(build=True)
    _instance._initialized = True


def wx_ready():
    """Called once from application.py after wxApp is created.
    Re-refreshes snapshot including computed settings that need a display.
    Subscribes to system colour changes to keep theme_is_dark current."""
    _instance._refresh(build=False)
    patterns.Publisher().registerObserver(
        _instance._on_system_theme_colour_changed,
        eventType="system.theme_colour_changed",
    )

