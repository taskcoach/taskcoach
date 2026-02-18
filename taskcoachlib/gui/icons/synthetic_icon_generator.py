"""Synthetic icons — routing-table dispatch via SyntheticIconGenerator.

Each synthetic icon is defined by a route in _ROUTES: a method name and
method-specific parameters. Icon holds a SyntheticIconGenerator instance
and delegates render_bitmap()/render_cursor() to it.

Status filter overlays composite a base icon (from settings) with a fixed
error badge, cached per-size. Cache is invalidated when the base icon
changes (live-check).

DnD cursor overlays create wx.Cursor objects from catalog icons with
centered hotspot, cached per-size (static source, never invalidated).
"""

import numpy as np

from taskcoachlib.meta.debug import log_step
from taskcoachlib.tools import wxhelper


# SSOT: all synthetic icons and their configuration.
_ROUTES = {
    # Cursor: icon_id is the catalog icon to convert to a cursor.
    "synthetic_dnd_cursor_link": {"method": "_dnd_cursor_overlay", "icon_id": "taskcoach_actions_link_icon"},
    "synthetic_dnd_cursor_home": {"method": "_dnd_cursor_overlay", "icon_id": "nuvola_places_user-home"},
    # Status filter overlay: option is the settings key for the base icon.
    # Base icon ID read from settings.get("icon", option) at runtime.
    "synthetic_hide_inactive":   {"method": "_status_filter_overlay", "option_id": "inactivetasks"},
    "synthetic_hide_late":       {"method": "_status_filter_overlay", "option_id": "latetasks"},
    "synthetic_hide_active":     {"method": "_status_filter_overlay", "option_id": "activetasks"},
    "synthetic_hide_duesoon":    {"method": "_status_filter_overlay", "option_id": "duesoontasks"},
    "synthetic_hide_overdue":    {"method": "_status_filter_overlay", "option_id": "overduetasks"},
    "synthetic_hide_completed":  {"method": "_status_filter_overlay", "option_id": "completedtasks"},
}


class SyntheticIconGenerator:
    """Generates synthetic bitmaps and cursors via routing-table dispatch.

    Each instance is one synthetic icon (e.g. "synthetic_hide_inactive"),
    carrying its own route from _ROUTES, its own cache, and its own
    last-seen base state. NOT an Icon subclass — Icon holds a reference.
    """

    def __init__(self, icon_id):
        route = _ROUTES.get(icon_id)
        if not route:
            log_step(f"ERROR: Unknown synthetic icon '{icon_id}'", prefix="ICON")
            return
        self.icon_id = icon_id
        self._route = route
        self._bitmaps = {}         # {size: wx.Bitmap or wx.Cursor}
        self._last_base_icon_id = None  # last seen base icon ID (overlay only)

    def render_bitmap(self, size):
        """Dispatch to bitmap route. Logs error if this is a cursor route.

        Uses explicit if/elif instead of getattr for security and grepability.
        """
        method = self._route["method"]
        if method == "_status_filter_overlay":
            return self._status_filter_overlay(self._route, size)
        elif method == "_dnd_cursor_overlay":
            log_step(f"ERROR: render_bitmap() called on cursor route "
                     f"'{self.icon_id}', call render_cursor() instead.",
                     prefix="ICON")
            return None
        else:
            log_step(f"ERROR: Unknown route method '{method}' "
                     f"for synthetic icon '{self.icon_id}'", prefix="ICON")
            return None

    def render_cursor(self, size):
        """Dispatch to cursor route. Logs error if this is a bitmap route.

        Uses explicit if/elif instead of getattr for security and grepability.
        """
        method = self._route["method"]
        if method == "_dnd_cursor_overlay":
            return self._dnd_cursor_overlay(self._route, size)
        elif method == "_status_filter_overlay":
            log_step(f"ERROR: render_cursor() called on bitmap route "
                     f"'{self.icon_id}', call render_bitmap() instead.",
                     prefix="ICON")
            return None
        else:
            log_step(f"ERROR: Unknown route method '{method}' "
                     f"for synthetic icon '{self.icon_id}'", prefix="ICON")
            return None

    def _status_filter_overlay(self, route, size):
        """Compose base icon + error badge (half-size, bottom-right).

        Reads settings directly — no stored settings reference.
        """
        import wx
        OVERLAY_ICON_ID = "nuvola_status_dialog-error"
        option = route["option_id"]
        settings = wx.GetApp().settings
        base_icon_id = settings.get("icon", option)
        if not base_icon_id:
            log_step(f"ERROR: Setting 'icon.{option}' is empty.",
                     prefix="ICON")
            return None
        # Invalidate cache if base icon changed
        if base_icon_id != self._last_base_icon_id:
            self._bitmaps.clear()
            self._last_base_icon_id = base_icon_id
        if size not in self._bitmaps:
            self._bitmaps[size] = self._compose(
                base_icon_id, OVERLAY_ICON_ID, size)
        return self._bitmaps[size]

    def _dnd_cursor_overlay(self, route, size):
        """Create cursor from catalog icon with centered hotspot.

        Cached per-instance — source icon is static (from _ROUTES),
        never invalidated.
        """
        source_icon_id = route["icon_id"]
        if size not in self._bitmaps:
            self._bitmaps[size] = self._make_cursor(source_icon_id, size)
        return self._bitmaps[size]

    def _compose(self, base_icon_id, overlay_icon_id, size):
        """Alpha-blend base + overlay at half-size in bottom-right."""
        import wx
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        main_bmp = icon_catalog.get_bitmap(base_icon_id, size)
        overlay_bmp = icon_catalog.get_bitmap(overlay_icon_id, size)

        if not main_bmp or not main_bmp.IsOk():
            log_step(
                f"Synthetic compose: base '{base_icon_id}' not found at {size}px.",
                prefix="ICON"
            )
            return None
        if not overlay_bmp or not overlay_bmp.IsOk():
            log_step(
                f"Synthetic compose: overlay '{overlay_icon_id}' not found at {size}px.",
                prefix="ICON"
            )
            return None

        overlay_image = overlay_bmp.ConvertToImage()
        overlay_image.Rescale(size // 2, size // 2, wx.IMAGE_QUALITY_HIGH)

        main_image = main_bmp.ConvertToImage()
        if not main_image.HasAlpha():
            main_image.InitAlpha()
        if not overlay_image.HasAlpha():
            overlay_image.InitAlpha()

        original_main_alpha = wxhelper.getAlphaDataFromImage(main_image).copy()

        main_bitmap = main_image.ConvertToBitmap()

        with wx.MemoryDC(main_bitmap) as dc:
            dc.DrawBitmap(
                overlay_image.ConvertToBitmap(), size // 2, size // 2, True
            )

        result_image = main_bitmap.ConvertToImage()
        result_image = wxhelper.mergeImagesWithAlpha(
            result_image, overlay_image, (size // 2, size // 2)
        )

        main_w, main_h = main_image.GetWidth(), main_image.GetHeight()
        ov_w, ov_h = overlay_image.GetWidth(), overlay_image.GetHeight()
        ov_x, ov_y = size // 2, size // 2

        result_alpha = wxhelper.getAlphaDataFromImage(result_image).copy()
        result_alpha_2d = result_alpha.reshape(main_h, main_w)
        original_alpha_2d = original_main_alpha.reshape(main_h, main_w)

        mask = np.ones((main_h, main_w), dtype=bool)
        mask[ov_y:min(ov_y + ov_h, main_h),
             ov_x:min(ov_x + ov_w, main_w)] = False
        result_alpha_2d[mask] = original_alpha_2d[mask]

        wxhelper.setAlphaDataToImage(result_image, result_alpha_2d)
        return result_image.ConvertToBitmap()

    def _make_cursor(self, icon_id, size):
        """Icon -> image -> cursor with centered hotspot."""
        import wx
        from taskcoachlib.gui.icons.icon_library import icon_catalog

        bitmap = icon_catalog.get_bitmap(icon_id, size)
        if not bitmap or not bitmap.IsOk():
            log_step(f"Cursor icon '{icon_id}' not found at {size}px.", prefix="ICON")
            return None
        image = bitmap.ConvertToImage()
        hotspot = size // 2
        image.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_X, hotspot)
        image.SetOption(wx.IMAGE_OPTION_CUR_HOTSPOT_Y, hotspot)
        return wx.Cursor(image)


# ============================================================================
# Module-level functions
# ============================================================================

def get_icon_defs():
    """Return metadata dict derived from _ROUTES for catalog registration.

    Returns _ROUTES directly — each entry is {icon_id: {method, icon_id/option_id}}.
    """
    return _ROUTES

