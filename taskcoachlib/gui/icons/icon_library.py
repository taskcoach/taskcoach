"""Icon library — Icon + IconCatalog classes, theme loading, init().

At runtime, imports icons_parsed.py (pre-computed by generate_icons_parsed_py.py)
which contains all icon metadata and pre-resolved file paths. No JSON or
index.theme parsing happens at runtime.

Legacy theme is the exception: no icons_parsed.py, icons are injected
programmatically from hardcoded definitions until fully deprecated.

The entire icon lifecycle is deferred to init(), called after wx.App exists.
All callers use icon_catalog.get_icon(icon_id).get_bitmap(size) directly — no
wx.ArtProvider middleman.
"""

import importlib
import json
import os
import sys

from taskcoachlib.meta.debug import log_step

# Module directory (taskcoachlib/gui/icons/)
_ICONS_DIR = os.path.dirname(os.path.abspath(__file__))

# Cache for loaded data
_theme_catalog = None
_theme_parsed = {}  # theme -> icons_parsed module data

_FALLBACK_ICON = "nuvola_mimetypes_core"
LIST_ICON_SIZE = 16
NOTIFICATION_ICON_SIZE = 32

# Deprecated icon names -> modern equivalents.
# Used by normalization hook points to migrate legacy icon names.
_DEPRECATED_ICONS = {
    "clock_alarm": "nuvola_apps_kalarm",
    "clock_alarm_icon": "nuvola_apps_kalarm",
    "clock_icon": "nuvola_apps_clock",
    "arrow_down_with_status_icon": "taskcoach_actions_arrow_down_with_status_icon",
    "arrow_up_with_status_icon": "taskcoach_actions_arrow_up_with_status_icon",
    "clock_menu_icon": "taskcoach_actions_clock_menu_icon",
    "clock_resume_icon": "taskcoach_actions_clock_resume_icon",
    "clock_stop_icon": "taskcoach_actions_clock_stop_icon",
    "led_grey_icon": "taskcoach_actions_led_grey_icon",
    "tree_collapse_all": "taskcoach_actions_tree_collapse_all",
    "tree_expand_all": "taskcoach_actions_tree_expand_all",
    "paste_subitem": "taskcoach_actions_paste_subitem",
    "newsub": "taskcoach_actions_newsub",
    "viewalltasks": "taskcoach_actions_viewalltasks",
    "activatepreviousviewer": "taskcoach_actions_tab-duplicate-left",
    "arrow_down_right": "taskcoach_actions_arrow_down_right",
    "checkall": "taskcoach_actions_checkall",
    "uncheckall": "taskcoach_actions_uncheckall",
    "timer_icon": "nuvola_apps_ktimer",
    "star_yellow_icon": "taskcoach_actions_star_yellow_icon",
    "folder_blue_light_icon": "taskcoach_actions_folder_blue_light_icon",
    "file_important_icon": "taskcoach_actions_file_important_icon",
    "file_locked_icon": "taskcoach_actions_file_locked_icon",
    "link_icon": "taskcoach_actions_link_icon",
    "folder_home_icon": "nuvola_places_user-home",
    "earth_green_icon": "taskcoach_actions_earth_green_icon",
    "next": "nuvola_actions_go-next-document",
    "prev": "nuvola_actions_go-previous-document",
    "newtmpl": "taskcoach_actions_newtmpl",
    "timelineviewer": "taskcoach_actions_timelineviewer",
    "taskcoach": "nuvola_apps_korganizer",
    "progress": "nuvola_actions_go-last",
    "clock_stopwatch_icon": "nuvola_apps_ktimer",
    "up": "nuvola_actions_arrow-up",
    "down": "nuvola_actions_arrow-down",
    "box_in_icon": "taskcoach_actions_box_in_icon",
    "box_out_icon": "taskcoach_actions_box_out_icon",
    "checkmark_green_icon": "nuvola_actions_ok",
    "checkmark_green_icon_multiple": "taskcoach_actions_checkmark_green_icon_multiple",
    "listview": "nuvola_actions_view-list-details",
    "windows": "nuvola_apps_window_list",
    "restore": "nuvola_apps_preferences-system-windows",
    "squaremapviewer": "taskcoach_actions_squaremapviewer",
    "magnifier_glass_dropdown_icon": "taskcoach_actions_magnifier_glass_dropdown_icon",
    "fileopen_red": "taskcoach_actions_fileopen_red",
    "exportashtml": "nuvola_mimetypes_text-html",
    "exportasvcal": "nuvola_mimetypes_text-vcalendar",
    "exportascsv": "nuvola_mimetypes_x-office-spreadsheet",
    "sort": "taskcoach_actions_sort",
    "cat_icon": "nuvola_categories_applications-toys",
    "sign_warning_icon": "nuvola_status_dialog-warning",
    "exclamation_icon": "nuvola_status_dialog-warning",
    "bell_icon": "nuvola_apps_preferences-desktop-notification-bell",
    "bomb_icon": "nuvola_apps_clanbomber",
    "bookmark_icon": "nuvola_apps_package_favorite",
    "cactus": "nuvola_apps_khangman",
    "heart_icon": "nuvola_apps_package_favorite",
    "hearts_icon": "nuvola_apps_amor",
    "folder_favorite_icon": "nuvola_places_folder-favorites",
    "energy_icon": "nuvola_apps_preferences-system-power-management",
    "lamp_icon": "nuvola_apps_ktip",
    "traffic_go_icon": "nuvola_places_start-here",
    "trafficlight_icon": "nuvola_apps_ksysv",
    "key_icon": "nuvola_status_key-single",
    "keys_icon": "nuvola_status_key-group",
    "music_piano_icon": "nuvola_actions_piano",
    "music_note_icon": "nuvola_actions_playsound",
    "cd_icon": "nuvola_devices_media-optical",
    "chat_icon": "nuvola_apps_chat",
    "cake_icon": "nuvola_apps_preferences-web-browser-cookies",
    "camera_icon": "nuvola_devices_camera-photo",
    "wrench_icon": "nuvola_actions_configure",
    "wizard_icon": "nuvola_actions_tools-wizard",
    "weather_umbrella_icon": "nuvola_apps_preferences-desktop-color",
    "weather_lightning_icon": "nuvola_apps_preferences-web-browser-cache",
    "weather_sunny_icon": "nuvola_apps_kweather",
    "tea_icon": "nuvola_apps_kteatime",
    "terminal_icon": "nuvola_apps_terminal",
    "remote_icon": "nuvola_devices_remote",
    "run_icon": "nuvola_mimetypes_application-x-executable",
    "password_icon": "nuvola_status_dialog-password",
    "bug_icon": "nuvola_apps_kbugbuster",
    "book_icon": "nuvola_apps_accessories-dictionary",
    "books_icon": "nuvola_apps_bookcase",
    "computer_laptop_icon": "nuvola_apps_laptop_pcmcia",
    "trashcan_icon": "nuvola_places_user-trash",
    "person_talking_icon": "nuvola_categories_applications-education-language",
    "pencil_icon": "nuvola_actions_draw-freehand",
    "palette_icon": "nuvola_apps_kcoloredit",
    "briefcase_icon": "nuvola_apps_preferences-desktop-user",
    "person_icon": "nuvola_apps_preferences-desktop-user",
    "persons_icon": "nuvola_apps_kuser",
    "person_id_icon": "nuvola_actions_contact-new",
    "contact_card_icon": "nuvola_mimetypes_text-x-vcard",
    "symbol_plus_icon": "nuvola_actions_list-add",
    "symbol_minus_icon": "nuvola_actions_list-remove",
    "star_red_icon": "nuvola_apps_mozilla",
    "sign_important_icon": "nuvola_status_dialog-warning",
    "science_icon": "nuvola_categories_applications-science",
    "arrow_down_icon": "nuvola_actions_go-down",
    "arrow_forward_icon": "nuvola_actions_go-next",
    "arrow_up_icon": "nuvola_actions_go-up",
    "arrows_looped_blue_icon": "nuvola_actions_kaboodleloop",
    "arrows_looped_green_icon": "nuvola_actions_view-refresh",
    "box_icon": "nuvola_apps_kpackage",
    "envelope_icon": "nuvola_apps_email",
    "envelopes_icon": "nuvola_actions_mail-queue",
    "paperclip_icon": "nuvola_status_mail-attachment",
    "attach_icon": "nuvola_status_mail-attachment",
    "fsview_icon": "nuvola_apps_fsview",
    "print": "nuvola_devices_printer",
    "undo": "nuvola_actions_edit-undo",
    "redo": "nuvola_actions_edit-redo",
    "save": "nuvola_devices_media-floppy",
    "mergedisk": "nuvola_actions_go-top",
    "fileopen": "nuvola_actions_document-open",
    "note_icon": "nuvola_apps_knotes",
    "lock_locked_icon": "nuvola_actions_decrypted",
    "lock_unlocked_icon": "nuvola_actions_encrypted",
    "charts_icon": "nuvola_apps_kchart",
    "cross_red_icon": "nuvola_status_dialog-error",
    "die_icon": "nuvola_apps_atlantik",
    "document_icon": "nuvola_mimetypes_application-x-dvi",
    "earth_blue_icon": "nuvola_categories_applications-internet",
    "folder_important_icon": "nuvola_places_folder-important",
    "folder_green_icon": "nuvola_places_folder-green",
    "folder_grey_icon": "nuvola_places_folder-grey",
    "folder_orange_icon": "nuvola_places_folder-orange",
    "folder_purple_icon": "nuvola_places_folder-violet",
    "folder_red_icon": "nuvola_places_folder-red",
    "folder_yellow_icon": "nuvola_places_folder-yellow",
    "folder_blue_icon": "nuvola_mimetypes_inode-directory",
    "folder_blue_arrow_icon": "nuvola_places_folder-downloads",
    "folder_blue_open_icon": "nuvola_mimetypes_inode-directory",
    "folder_green_open_icon": "nuvola_places_folder-green",
    "folder_grey_open_icon": "nuvola_places_folder-grey",
    "folder_orange_open_icon": "nuvola_places_folder-orange",
    "folder_purple_open_icon": "nuvola_places_folder-violet",
    "folder_red_open_icon": "nuvola_places_folder-red",
    "folder_yellow_open_icon": "nuvola_places_folder-yellow",
    "house_red_icon": "nuvola_places_user-home",
    "house_green_icon": "nuvola_actions_go-home",
    "led_blue_icon": "nuvola_actions_ledblue",
    "led_blue_light_icon": "nuvola_actions_ledlightblue",
    "led_green_icon": "nuvola_actions_ledgreen",
    "led_green_light_icon": "nuvola_actions_ledlightgreen",
    "led_yellow_icon": "nuvola_actions_ledyellow",
    "led_red_icon": "nuvola_actions_ledred",
    "led_purple_icon": "nuvola_actions_ledpurple",
    "led_orange_icon": "nuvola_actions_ledorange",
    "exit": "nuvola_actions_application-exit",
    "new": "nuvola_actions_document-new",
    "copy": "nuvola_actions_edit-copy",
    "paste": "nuvola_actions_edit-paste",
    "cut": "nuvola_actions_edit-cut",
    "saveas": "nuvola_actions_document-save-as",
    "close": "nuvola_actions_dialog-close",
    "delete": "nuvola_actions_edit-delete",
    "viewnewviewer": "nuvola_actions_tab-new-background",
    "activatenextviewer": "nuvola_actions_tab-duplicate",
    "edit": "nuvola_actions_edit",
    "incpriority": "nuvola_actions_arrow-up",
    "decpriority": "nuvola_actions_arrow-down",
    "maxpriority": "nuvola_actions_arrow-up-double",
    "minpriority": "nuvola_actions_arrow-down-double",
    "error_icon": "nuvola_status_dialog-error",
    "calendar_icon": "nuvola_apps_date",
    "graph_icon": "nuvola_apps_kchart",
    "computer_desktop_icon": "nuvola_devices_computer",
    "computer_handheld_icon": "nuvola_devices_pda",
    "cookie_icon": "nuvola_apps_preferences-web-browser-cookies",
    "cogwheels_icon": "nuvola_apps_kcmsystem",
    "cogwheel_icon": "nuvola_apps_preferences-system-session-services",
    "printer_icon": "nuvola_devices_printer",
    "led_blue_questionmark_icon": "nuvola_actions_help-about",
    "reload_icon": "nuvola_actions_view-refresh",
    "sticky_note_icon": "nuvola_apps_knotes",
    "magnifier_glass_icon": "nuvola_apps_xmag",
    "life_ring_icon": "nuvola_apps_help-browser",
    "led_blue_information_icon": "nuvola_status_dialog-information",
    "calculator_icon": "nuvola_apps_accessories-calculator",
    "banking": "papirus_apps_org.tabos.banking",
    "bitcoin": "papirus_apps_bitcoin",
    "bank_building": "oxygen_actions_view-bank",
    "bank_account": "oxygen_actions_view-bank",
    "homebank": "papirus_apps_homebank",
    "safeeyes": "papirus_apps_safeeyes",
    "safe_vault": "papirus_apps_accessories-safe",
    "money_expense": "papirus_apps_money-manager-ex",
    "money_manager": "papirus_apps_money-manager-ex",
    "taxes": "noto-emoji_symbols_u1f4b2",
    "wallet_closed": "oxygen_status_wallet-closed",
    "wallet_open": "oxygen_status_wallet-open",
    "wallet_keys": "oxygen_apps_kwalletmanager",
    "moneydance": "papirus_apps_moneydance",
    "kmymoney": "papirus_apps_kmymoney",
    "cryptomator": "papirus_apps_cryptomator",
    "uno_calculator": "papirus_apps_uno-calculator",
    "cointop": "papirus_apps_cointop",
    "gnome_calculator": "papirus_apps_gnome-calculator",
    "calculator_flat": "papirus_apps_accessories-calculator",
    "calculator_3d": "oxygen_apps_accessories-calculator",
    "wallet_flat": "papirus_apps_kwalletmanager",
    "money_budget": "papirus_apps_kmymoney",
    "currency_dollar": "papirus_actions_format-currency",
}


# ============================================================================
# Icon class
# ============================================================================

class Icon:
    """A single icon with metadata, path resolution, and bitmap loading."""

    def __init__(self, icon_id, label="", hints=None, theme="",
                 theme_label="", context="", context_label="",
                 file="", paths=None):
        self.icon_id = icon_id
        self.label = label
        self.hints = hints or []
        self.theme = theme
        self.theme_label = theme_label
        self.context = context
        self.context_label = context_label
        self.file = file
        self._paths = paths or {}
        self._synthetic_icon_generator = None  # set for synthetic icons only

    def path(self, size):
        """Absolute file path for the given size, or None.

        Logs error + returns None for synthetic icons (no file paths).
        """
        if self.theme == "synthetic":
            log_step(f"ERROR: path() called on synthetic icon '{self.icon_id}'.",
                     prefix="ICON")
            return None
        rel = self._paths.get(size)
        if rel is None:
            return None
        # Legacy icons store absolute paths; theme icons store relative paths
        if os.path.isabs(rel):
            return rel
        return os.path.join(_ICONS_DIR, self.theme, rel)

    def get_bitmap(self, size):
        """Load and return wx.Bitmap for the given size, or None.

        If synthetic, calls _synthetic_icon_generator.render_bitmap(size);
        otherwise loads from file.
        """
        import wx
        result = None
        if self.theme == "synthetic":
            if self._synthetic_icon_generator:
                result = self._synthetic_icon_generator.render_bitmap(size)
        else:
            icon_path = self.path(size)
            if icon_path and os.path.exists(icon_path):
                image = wx.Image(icon_path)
                if image.IsOk():
                    result = image.ConvertToBitmap()
        return result

    def get_cursor(self, window=None):
        """Return wx.Cursor, or None. HiDPI-aware.

        Picks size from window's content scale factor. If synthetic,
        calls _synthetic_icon_generator.render_cursor(size); otherwise
        logs error (safety guard — any icon could produce a cursor,
        remove the error and open the else block when needed).
        """
        import wx
        scaleFactor = 1.0
        if window:
            try:
                scaleFactor = window.GetContentScaleFactor()
            except (AttributeError, RuntimeError):
                pass
        # DPI-aware cursor sizing — only 16px cursors exist today.
        # When HiDPI cursors are added, uncomment the size assignments below.
        if scaleFactor >= 1.75:
            log_step("WARNING: HiDPI cursor (32px) not yet available, falling back to 16px")
            size = LIST_ICON_SIZE
        elif scaleFactor >= 1.125:
            log_step("WARNING: MidDPI cursor (22px) not yet available, falling back to 16px")
            size = LIST_ICON_SIZE
        else:
            size = LIST_ICON_SIZE
        result = None
        if self.theme == "synthetic":
            if self._synthetic_icon_generator:
                result = self._synthetic_icon_generator.render_cursor(size)
        else:
            log_step(f"ERROR: get_cursor() called on non-synthetic icon "
                     f"'{self.icon_id}'.", prefix="ICON")
        return result

    def get_wx_icon(self, size):
        """Return wx.Icon (bitmap with alpha-to-mask conversion)."""
        import wx
        bitmap = self.get_bitmap(size)
        if not bitmap or not bitmap.IsOk():
            return None
        image = bitmap.ConvertToImage()
        image.ConvertAlphaToMask()
        return wx.Icon(wx.Bitmap(image))

    def get_icon_bundle(self):
        """Return wx.IconBundle with all standard sizes."""
        import wx
        bundle = wx.IconBundle()
        for size in self.sizes:
            icon = self.get_wx_icon(size)
            if icon:
                bundle.AddIcon(icon)
        return bundle

    @property
    def sizes(self):
        return sorted(self._paths)



# ============================================================================
# IconCatalog class
# ============================================================================

class IconCatalog:
    """Registry of all icons. Single source of truth."""

    def __init__(self):
        self._icons = {}        # icon_id -> Icon
        self._duplicates = {}   # duplicate_id -> target_id

    def get_icon(self, icon_id):
        """Get Icon by id. Returns Icon or None.

        Calls normalize_icon_id() as a safety net — if a deprecated or
        duplicate name slipped through, it normalizes and logs.
        """
        icon_id = self.normalize_icon_id(icon_id)
        return self._icons.get(icon_id)

    def _get_fallback_icon(self, icon_id):
        """Return the fallback Icon with full logging. Returns None on failure."""
        if icon_id == _FALLBACK_ICON:
            log_step(
                f"CRITICAL: Fallback icon '{_FALLBACK_ICON}' itself failed. "
                f"This should never occur — the installation is broken.",
                prefix="ICON"
            )
            return None
        fallback = self.get_icon(_FALLBACK_ICON)
        if not fallback:
            log_step(
                f"CRITICAL: Fallback icon '{_FALLBACK_ICON}' not in catalog. "
                f"This should never occur — the installation is broken.",
                prefix="ICON"
            )
        return fallback

    def _fallback_bitmap(self, icon_id, size):
        """Try to get a bitmap from the fallback icon. Logs all failures."""
        import wx
        fallback = self._get_fallback_icon(icon_id)
        if not fallback:
            log_step(
                f"ERROR: No fallback available for icon '{icon_id}'.",
                prefix="ICON"
            )
            return wx.NullBitmap
        bmp = fallback.get_bitmap(size)
        if bmp and bmp.IsOk():
            return bmp
        log_step(
            f"ERROR: Fallback icon '{_FALLBACK_ICON}' also failed at size {size}.",
            prefix="ICON"
        )
        return wx.NullBitmap

    def _fallback_wx_icon(self, icon_id, size):
        """Try to get a wx.Icon from the fallback icon. Logs all failures."""
        import wx
        fallback = self._get_fallback_icon(icon_id)
        if not fallback:
            log_step(
                f"ERROR: No fallback available for icon '{icon_id}'.",
                prefix="ICON"
            )
            return wx.NullIcon
        wx_icon = fallback.get_wx_icon(size)
        if wx_icon and wx_icon.IsOk():
            return wx_icon
        log_step(
            f"ERROR: Fallback icon '{_FALLBACK_ICON}' wx.Icon also failed at size {size}.",
            prefix="ICON"
        )
        return wx.NullIcon

    def get_bitmap(self, icon_id, size):
        """Get bitmap for icon_id at size. Returns Bitmap or NullBitmap.

        Falls back to the fallback icon on failure.
        """
        import wx
        result = wx.NullBitmap

        if not icon_id:
            pass
        else:
            icon = self.get_icon(icon_id)
            if not icon:
                log_step(
                    f"ERROR: Icon '{icon_id}' not found in catalog. "
                    f"Migrate it or restore it. See ICON_LIBRARY.md.",
                    prefix="ICON"
                )
                result = self._fallback_bitmap(icon_id, size)
            else:
                bmp = icon.get_bitmap(size)
                if bmp and bmp.IsOk():
                    result = bmp
                else:
                    log_step(
                        f"ERROR: Icon '{icon_id}' failed at size {size}. "
                        f"Import it from the distillery. See ICON_LIBRARY.md.",
                        prefix="ICON"
                    )
                    result = self._fallback_bitmap(icon_id, size)

        return result

    def get_icon_bundle(self, icon_id):
        """Get IconBundle for icon_id. Returns IconBundle (empty if not found)."""
        import wx
        icon = self.get_icon(icon_id)
        if icon:
            return icon.get_icon_bundle()
        return wx.IconBundle()

    def get_wx_icon(self, icon_id, size):
        """Get wx.Icon for icon_id at size. Returns wx.Icon or NullIcon.

        Falls back to the fallback icon on failure.
        """
        import wx
        result = wx.NullIcon

        icon = self.get_icon(icon_id)
        if not icon:
            log_step(
                f"ERROR: Icon '{icon_id}' not found in catalog.",
                prefix="ICON"
            )
            result = self._fallback_wx_icon(icon_id, size)
        else:
            wx_icon = icon.get_wx_icon(size)
            if wx_icon and wx_icon.IsOk():
                result = wx_icon
            else:
                log_step(
                    f"ERROR: Icon '{icon_id}' wx.Icon failed at size {size}.",
                    prefix="ICON"
                )
                result = self._fallback_wx_icon(icon_id, size)

        return result

    def get_cursor(self, icon_id, window=None):
        """Get cursor for icon_id. Returns wx.Cursor or None."""
        icon = self.get_icon(icon_id)
        if icon:
            return icon.get_cursor(window)
        return None

    def get_path(self, icon_id, size):
        """Get file path for icon_id at size. Returns str or None."""
        icon = self.get_icon(icon_id)
        if icon:
            return icon.path(size)
        return None

    def normalize_icon_id(self, icon_id):
        """Normalize icon_id: resolve deprecated then duplicate.

        Returns the normalized id, or the same id unchanged if no match.
        """
        if not icon_id:
            return icon_id
        icon_id = self._normalize_deprecated(icon_id)
        icon_id = self._normalize_duplicate(icon_id)
        return icon_id

    def _normalize_deprecated(self, icon_id):
        """Resolve deprecated icon name to modern equivalent.

        Returns the modern id if deprecated, or the same id unchanged.
        """
        new_id = _DEPRECATED_ICONS.get(icon_id)
        if new_id:
            log_step(
                f"Normalizing deprecated icon '{icon_id}' -> '{new_id}'",
                prefix="ICON"
            )
            return new_id
        return icon_id

    def _normalize_duplicate(self, icon_id):
        """Resolve duplicate icon name to primary.

        Returns the primary id if duplicate, or the same id unchanged.
        """
        target = self._duplicates.get(icon_id)
        if target:
            log_step(
                f"Normalizing duplicate icon '{icon_id}' -> '{target}'",
                prefix="ICON"
            )
            return target
        return icon_id

    def _register(self, icon):
        """Register an Icon. Logs error and drops on ID conflict."""
        if icon.icon_id in self._icons:
            existing = self._icons[icon.icon_id]
            log_step(
                f"ERROR: Icon ID conflict '{icon.icon_id}' — "
                f"theme '{existing.theme}' vs '{icon.theme}'. "
                f"Keeping first, dropping second.",
                prefix="ICON"
            )
            return
        self._icons[icon.icon_id] = icon

    def viewer_icon_ids(self):
        """Icon IDs for viewer image lists (list, excludes duplicates).

        Currently returns all non-synthetic icons. Future: only icons
        actually assigned to items in the current data file.
        """
        return [icon_id for icon_id, icon in self._icons.items()
                if icon.theme != "synthetic"]

    def __len__(self):
        return len(self._icons)

    def _load_theme(self, theme):
        """Load all primary icons from a theme's icons_parsed.py."""
        parsed = _load_theme_parsed(theme)
        cat = _load_catalog()
        theme_label = cat.get(theme, {}).get("name", theme.title())
        contexts = parsed.get("contexts", {})
        for icon_id, data in parsed["icons"].items():
            if "duplicate_of" in data:
                self._duplicates[icon_id] = data["duplicate_of"]
                continue
            if not data.get("file") or not data.get("label") \
               or not data.get("paths"):
                continue
            ctx = data.get("context", "")
            self._register(Icon(
                icon_id=icon_id,
                label=data["label"],
                hints=data.get("hints", []),
                theme=theme,
                theme_label=theme_label,
                context=ctx,
                context_label=contexts.get(ctx, ctx.title()),
                file=data["file"],
                paths=data.get("paths", {}),
            ))

    def _load_theme_catalog(self):
        """Read ICON_THEME_CATALOG.json and return active theme names.

        Returns theme names where active=true and icons_parsed.py exists.
        Legacy and synthetic are not in the catalog — they are hardcoded
        direct calls in _load_all_themes().
        """
        themes = []
        cat = _load_catalog()
        for theme_name, theme_config in cat.items():
            if not theme_config.get("active", False):
                continue
            parsed_path = os.path.join(_ICONS_DIR, theme_name, "icons_parsed.py")
            if os.path.exists(parsed_path):
                themes.append(theme_name)
            else:
                log_step(f"ERROR: Active theme '{theme_name}' missing "
                         f"{theme_name}/icons_parsed.py", prefix="ICON")
        return themes

    def _load_synthetic_icons(self):
        """Register synthetic icons from the routing table.

        Creates plain Icon instances with _synthetic_icon_generator set.
        Bitmap generation is lazy — only happens on first get_bitmap() call.
        """
        from taskcoachlib.gui.icons.synthetic_icon_generator import (
            get_icon_defs, SyntheticIconGenerator)
        for sid in get_icon_defs():
            icon = Icon(icon_id=sid, theme="synthetic")
            icon._synthetic_icon_generator = SyntheticIconGenerator(sid)
            self._register(icon)

    def _load_all_themes(self):
        """Load all active themes.

        File-based: themes from ICON_THEME_CATALOG.json via _load_theme().
        Synthetic: generated icons (e.g. composite overlays).
        """
        for theme in self._load_theme_catalog():
            self._load_theme(theme)
        self._load_synthetic_icons()



# Module-level singleton
icon_catalog = IconCatalog()




# ============================================================================
# Internal helpers
# ============================================================================

def _load_catalog():
    """Load and cache the theme catalog JSON."""
    global _theme_catalog
    if _theme_catalog is None:
        catalog_path = os.path.join(_ICONS_DIR, "ICON_THEME_CATALOG.json")
        if os.path.exists(catalog_path):
            try:
                with open(catalog_path, "r", encoding="utf-8") as f:
                    _theme_catalog = json.load(f)
            except json.JSONDecodeError as e:
                log_step(f"ERROR: Failed to parse {catalog_path}: {e}", prefix="ICON")
                _theme_catalog = {}
        else:
            log_step(f"ERROR: Theme catalog not found: {catalog_path}", prefix="ICON")
            _theme_catalog = {}
    return _theme_catalog


def _load_theme_parsed(theme):
    """Load and cache icons_parsed.py module for a theme.

    Returns dict with 'icons' and 'contexts' from the module.
    """
    global _theme_parsed
    if theme not in _theme_parsed:
        module_name = f"taskcoachlib.gui.icons.{theme}.icons_parsed"
        try:
            mod = importlib.import_module(module_name)
            _theme_parsed[theme] = {
                "icons": getattr(mod, "icons", {}),
                "contexts": getattr(mod, "contexts", {}),
            }
        except ImportError as e:
            log_step(f"ERROR: Failed to import {module_name}: {e}", prefix="ICON")
            _theme_parsed[theme] = {"icons": {}, "contexts": {}}

    return _theme_parsed[theme]







# ============================================================================
# init() — call after wx.App exists
# ============================================================================

def init():
    """Initialize the icon system. Call once after wx.App exists.

    Calls _load_all_themes() (legacy, file-based, synthetic), sets up
    Windows remap option, and verifies fallback.
    """
    from taskcoachlib import operating_system
    import wx

    # Windows display depth optimization
    if operating_system.isWindows() and wx.DisplayDepth() >= 32:
        try:
            wx.SystemOptions.SetOption("msw.remap", "0")
        except AttributeError:
            wx.SystemOptions_SetOption("msw.remap", "0")

    # Load all active themes (legacy, file-based, synthetic)
    icon_catalog._load_all_themes()

    log_step(f"Icon system initialized: {len(icon_catalog)} icons registered", prefix="ICON")
