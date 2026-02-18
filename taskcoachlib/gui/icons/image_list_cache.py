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

from taskcoachlib.gui.icons.icon_library import (
    icon_catalog, _FALLBACK_ICON, LIST_ICON_SIZE,
)
from taskcoachlib.meta.debug import log_step


class ImageListCache:
    """Global owner of the single shared wx.ImageList for all viewers.

    Icons are loaded lazily on first request via get_index(). All viewers
    borrow the list via SetImageList (no ownership transfer). Size is set
    once at construction (from settings or default) and used for all
    bitmap loads.
    """

    def __init__(self, size=LIST_ICON_SIZE):
        import wx
        self._size = size
        self._image_list = wx.ImageList(self._size, self._size)
        self._index = {}  # icon_id -> int index in _image_list
        self._fallback_idx = -1
        self._init_fallback()

    @property
    def size(self):
        """Icon size (square pixels). All bitmaps loaded at this size."""
        return self._size

    @property
    def image_list(self):
        """The wx.ImageList."""
        return self._image_list

    def _init_fallback(self):
        """Load fallback icon as first entry in the ImageList."""
        bitmap = icon_catalog.get_bitmap(_FALLBACK_ICON, self._size)
        if bitmap and bitmap.IsOk():
            self._fallback_idx = self._image_list.Add(bitmap)
        else:
            log_step(
                "CRITICAL: Fallback icon '{}' missing".format(_FALLBACK_ICON),
                prefix="ICON",
            )

    def get_index(self, icon_id):
        """Return ImageList index for icon_id, loading lazily on first call.

        Uses icon.get_bitmap() directly (not icon_catalog.get_bitmap()) to avoid
        icon_catalog's own fallback logic which would duplicate the fallback bitmap
        as a separate ImageList entry per failed icon. On failure: logs error
        and returns the single shared fallback index.
        """
        idx = self._index.get(icon_id)
        if idx is None:
            icon = icon_catalog.get_icon(icon_id)
            if icon:
                bitmap = icon.get_bitmap(self._size)
                if bitmap and bitmap.IsOk():
                    idx = self._image_list.Add(bitmap)
                else:
                    log_step(
                        "Icon '{}' bitmap failed at size {}, using fallback".format(
                            icon_id, self._size),
                        prefix="ICON",
                    )
                    idx = self._fallback_idx
            else:
                log_step(
                    "Icon '{}' not in catalog, using fallback".format(icon_id),
                    prefix="ICON",
                )
                idx = self._fallback_idx
            self._index[icon_id] = idx
        return idx

    def __contains__(self, icon_id):
        """True if icon_id has already been loaded."""
        return icon_id in self._index

    def __len__(self):
        """Number of icons currently loaded."""
        return len(self._index)


image_list_cache = None  # initialized in init()


def init():
    """Create the image_list_cache singleton. Call after icon_library.init()."""
    global image_list_cache
    image_list_cache = ImageListCache()


def __getattr__(name):
    """Delegate attribute access to the singleton so callers can import the
    module and use image_list_cache.get_index(...) directly."""
    if image_list_cache is not None:
        return getattr(image_list_cache, name)
    raise AttributeError(
        "module 'image_list_cache' has no attribute {!r}".format(name)
    )
