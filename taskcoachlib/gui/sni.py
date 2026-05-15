# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers <developers@taskcoach.org>

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

Direct StatusNotifierItem (SNI) tray icon implementation.

Two D-Bus services are exported on a private SessionBus connection:

- `org.kde.StatusNotifierItem` at /StatusNotifierItem
    ItemIsMenu=False so the host calls Activate() on left-click (which we
    route to a caller-supplied callback) instead of showing the menu.

- `com.canonical.dbusmenu` at /MenuBar
    The right-click menu, exposed as a DBusMenu tree built from the
    Gtk.Menu the caller passes in. The SNI host (KDE plasmashell, gnome
    AppIndicator extension, etc.) renders and positions the menu itself
    — necessary on Wayland where popup positioning by absolute screen
    coordinates is forbidden.

Click events on a DBusMenu item route back to the source Gtk.MenuItem by
emitting its 'activate' signal, so existing handlers wired via
gtk_item.connect('activate', ...) continue to fire unchanged.

The public class `SniIcon` has the AppIndicatorIcon-compatible API
(set_icon_full, set_tooltip, set_gtk_menu, RemoveIcon, Destroy) plus
set_left_click_callback().
"""

import os
import logging

_log = logging.getLogger(__name__)

_ITEM_IFACE = 'org.kde.StatusNotifierItem'
_WATCHER_IFACE = 'org.kde.StatusNotifierWatcher'
_WATCHER_PATH = '/StatusNotifierWatcher'
_ITEM_PATH = '/StatusNotifierItem'
_DBUSMENU_IFACE = 'com.canonical.dbusmenu'
_DBUSMENU_PATH = '/MenuBar'
_PROPERTIES_IFACE = 'org.freedesktop.DBus.Properties'

SNI_AVAILABLE = False
SNI_ERROR = None

try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    SNI_AVAILABLE = True
except (ImportError, ValueError) as e:
    SNI_ERROR = f"SNI deps not available: {e}"


def watcher_available():
    """Return True iff an SNI host owns org.kde.StatusNotifierWatcher.

    Called at startup to decide whether direct SNI is usable. False means
    fall back to wx.adv.TaskBarIcon.
    """
    if not SNI_AVAILABLE:
        return False
    try:
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()
        return bool(bus.name_has_owner(_WATCHER_IFACE))
    except Exception as e:
        _log.debug("watcher_available probe failed: %s", e)
        return False


if SNI_AVAILABLE:

    class _DBusMenuItem:
        """A node in the DBusMenu tree.

        gtk_item is the source Gtk.MenuItem; we hold the reference so we
        can dispatch click events back to its 'activate' signal.
        """
        __slots__ = ('id', 'props', 'children', 'gtk_item')

        def __init__(self, item_id, props, children=None, gtk_item=None):
            self.id = item_id
            self.props = props
            self.children = children if children is not None else []
            self.gtk_item = gtk_item


    class _DBusMenuServer(dbus.service.Object):
        """Implements com.canonical.dbusmenu so SNI hosts render the menu
        themselves. Layout rebuilds increment the revision and emit
        LayoutUpdated; hosts then re-fetch with GetLayout.
        """

        def __init__(self, bus_name):
            super().__init__(bus_name, _DBUSMENU_PATH)
            self._revision = 0
            self._root = _DBusMenuItem(0, {'children-display': 'submenu'})
            self._by_id = {0: self._root}
            # Hold a reference to the source Gtk.Menu so it (and the
            # signal handlers attached to its items) outlives this
            # method. Without this, the freshly-built menu goes out of
            # scope after set_gtk_menu() returns and Python GCs it,
            # silently breaking Event() click dispatch later.
            self._gtk_menu = None

        def set_root_from_gtk(self, gtk_menu):
            """Walk a Gtk.Menu and rebuild the DBusMenu tree.

            IDs are reassigned on every rebuild. We bump the revision and
            emit LayoutUpdated(revision, 0) so the host invalidates its
            cache and re-fetches the layout.
            """
            self._gtk_menu = gtk_menu
            next_id = [1]
            self._by_id = {0: self._root}
            self._root.children = []
            if gtk_menu is not None:
                for gtk_item in gtk_menu.get_children():
                    child = self._build_item(gtk_item, next_id)
                    if child is not None:
                        self._root.children.append(child)
            self._revision += 1
            try:
                self.LayoutUpdated(dbus.UInt32(self._revision),
                                   dbus.Int32(0))
            except Exception:
                _log.exception("LayoutUpdated emit failed")

        def _build_item(self, gtk_item, next_id):
            item_id = next_id[0]
            next_id[0] += 1
            props = {}
            if isinstance(gtk_item, Gtk.SeparatorMenuItem):
                props['type'] = 'separator'
            else:
                # Both Gtk and DBusMenu use _ as accelerator prefix, so
                # forward labels verbatim.
                props['label'] = gtk_item.get_label() or ''
                props['enabled'] = bool(gtk_item.get_sensitive())
                props['visible'] = bool(gtk_item.get_visible())
            children = []
            submenu = (gtk_item.get_submenu()
                       if hasattr(gtk_item, 'get_submenu') else None)
            if submenu is not None:
                props['children-display'] = 'submenu'
                for child in submenu.get_children():
                    child_item = self._build_item(child, next_id)
                    if child_item is not None:
                        children.append(child_item)
            item = _DBusMenuItem(item_id, props, children, gtk_item)
            self._by_id[item_id] = item
            return item

        # Wire-type helpers -----------------------------------------------

        @staticmethod
        def _dbusify_value(v):
            # a{sv} requires each value wrapped as a variant.
            # variant_level=1 tells dbus-python to emit it that way.
            if isinstance(v, bool):
                return dbus.Boolean(v, variant_level=1)
            if isinstance(v, int):
                return dbus.Int32(v, variant_level=1)
            return dbus.String(str(v), variant_level=1)

        def _dbusify_props(self, props):
            d = dbus.Dictionary(signature='sv')
            for k, v in props.items():
                d[k] = self._dbusify_value(v)
            return d

        def _serialize(self, item, depth, prop_filter):
            """Build the (ia{sv}av) layout tuple recursively.

            depth: -1 means unbounded. 0 means props only, no children.
            """
            if prop_filter:
                visible_props = {k: v for k, v in item.props.items()
                                 if k in prop_filter}
            else:
                visible_props = item.props
            props = self._dbusify_props(visible_props)
            children = []
            if depth != 0 and item.children:
                next_depth = (depth - 1) if depth > 0 else -1
                for child in item.children:
                    child_tuple = self._serialize(child, next_depth,
                                                  prop_filter)
                    children.append(dbus.Struct(
                        child_tuple,
                        signature='(ia{sv}av)',
                        variant_level=1,
                    ))
            return (dbus.Int32(item.id),
                    props,
                    dbus.Array(children, signature='v'))

        # com.canonical.dbusmenu methods ---------------------------------

        @dbus.service.method(_DBUSMENU_IFACE,
                             in_signature='iias',
                             out_signature='u(ia{sv}av)')
        def GetLayout(self, parent_id, recursion_depth, property_names):
            item = self._by_id.get(int(parent_id), self._root)
            prop_filter = list(property_names) if property_names else None
            layout = self._serialize(item, int(recursion_depth), prop_filter)
            return (dbus.UInt32(self._revision), layout)

        @dbus.service.method(_DBUSMENU_IFACE,
                             in_signature='aias',
                             out_signature='a(ia{sv})')
        def GetGroupProperties(self, ids, property_names):
            prop_filter = list(property_names) if property_names else None
            out = []
            for item_id in ids:
                item = self._by_id.get(int(item_id))
                if item is None:
                    continue
                visible = (item.props if not prop_filter
                           else {k: v for k, v in item.props.items()
                                 if k in prop_filter})
                out.append(dbus.Struct(
                    (dbus.Int32(item.id), self._dbusify_props(visible)),
                    signature='(ia{sv})',
                ))
            return dbus.Array(out, signature='(ia{sv})')

        @dbus.service.method(_DBUSMENU_IFACE,
                             in_signature='is',
                             out_signature='v')
        def GetProperty(self, item_id, name):
            item = self._by_id.get(int(item_id))
            if item is None or name not in item.props:
                return dbus.String('', variant_level=1)
            return self._dbusify_value(item.props[name])

        @dbus.service.method(_DBUSMENU_IFACE,
                             in_signature='isvu',
                             out_signature='')
        def Event(self, item_id, event_id, data, timestamp):
            _log.debug("DBusMenu.Event id=%s event=%s", item_id, event_id)
            if event_id != 'clicked':
                return
            item = self._by_id.get(int(item_id))
            if item is None or item.gtk_item is None:
                return
            try:
                # .activate() is the idiomatic GTK call; it emits the
                # 'activate' signal and invokes the default handler,
                # which works whether the item is currently mapped or
                # not (it isn't — the host renders its own UI).
                item.gtk_item.activate()
            except Exception:
                _log.exception("DBusMenu click handler failed")

        @dbus.service.method(_DBUSMENU_IFACE,
                             in_signature='i',
                             out_signature='b')
        def AboutToShow(self, item_id):
            # We rebuild eagerly on source changes, so no late mutation
            # is ever needed at popup time.
            return False

        @dbus.service.signal(_DBUSMENU_IFACE, signature='ui')
        def LayoutUpdated(self, revision, parent):
            pass

        # org.freedesktop.DBus.Properties --------------------------------

        @dbus.service.method(_PROPERTIES_IFACE,
                             in_signature='ss', out_signature='v')
        def Get(self, interface, prop):
            if interface != _DBUSMENU_IFACE:
                raise dbus.exceptions.DBusException(
                    f"Unknown interface: {interface}",
                    name='org.freedesktop.DBus.Error.UnknownInterface')
            return self._get_iface_property(prop)

        @dbus.service.method(_PROPERTIES_IFACE,
                             in_signature='s', out_signature='a{sv}')
        def GetAll(self, interface):
            if interface != _DBUSMENU_IFACE:
                raise dbus.exceptions.DBusException(
                    f"Unknown interface: {interface}",
                    name='org.freedesktop.DBus.Error.UnknownInterface')
            return dbus.Dictionary({
                'Version': dbus.UInt32(3, variant_level=1),
                'Status': dbus.String('normal', variant_level=1),
                'TextDirection': dbus.String('ltr', variant_level=1),
                'IconThemePath': dbus.Array([], signature='s',
                                            variant_level=1),
            }, signature='sv')

        @dbus.service.method(_PROPERTIES_IFACE,
                             in_signature='ssv', out_signature='')
        def Set(self, interface, prop, value):
            raise dbus.exceptions.DBusException(
                f"Property is read-only: {prop}",
                name='org.freedesktop.DBus.Error.PropertyReadOnly')

        def _get_iface_property(self, prop):
            if prop == 'Version':
                return dbus.UInt32(3)
            if prop == 'Status':
                return dbus.String('normal')
            if prop == 'TextDirection':
                return dbus.String('ltr')
            if prop == 'IconThemePath':
                return dbus.Array([], signature='s')
            raise dbus.exceptions.DBusException(
                f"Unknown property: {prop}",
                name='org.freedesktop.DBus.Error.UnknownProperty')


    class SniIcon(dbus.service.Object):
        """A StatusNotifierItem exported on the session bus, with a
        DBusMenu companion for the right-click menu.

        Constructor and the five behavioural methods (set_icon_full,
        set_tooltip, set_gtk_menu, RemoveIcon, Destroy) match
        appindicator.AppIndicatorIcon; set_left_click_callback() is the
        SNI-only extension.
        """

        def __init__(self, app_id='taskcoach', icon_name=None,
                     icon_theme_path=None, category=None,
                     tooltip='Task Coach'):
            # dbus.SessionBus() is a process-wide singleton. idle.py may
            # have already created one without a mainloop (its only DBus
            # use is synchronous), and set_default_main_loop can't retro-
            # attach a mainloop to an existing connection. Exporting
            # objects requires one, so we open a private connection with
            # the GLib mainloop wired in directly. The well-known name
            # still ends up on the session bus daemon where SNI hosts can
            # find it.
            self._bus = dbus.SessionBus(mainloop=DBusGMainLoop(),
                                         private=True)
            self._service_name = (
                f"org.kde.StatusNotifierItem-{os.getpid()}-1"
            )
            self._bus_name = dbus.service.BusName(self._service_name,
                                                  self._bus)
            super().__init__(self._bus_name, _ITEM_PATH)

            self._id = app_id
            self._title = app_id
            self._tooltip_text = tooltip
            self._status = 'Active'
            self._icon_name = icon_name or 'application-default-icon'
            self._icon_theme_path = icon_theme_path or ''
            self._category = category or 'ApplicationStatus'

            self._left_click_cb = None

            # Export the DBusMenu companion on the same bus connection so
            # SNI's Menu property can point at it.
            self._dbusmenu = _DBusMenuServer(self._bus_name)

            try:
                watcher = self._bus.get_object(_WATCHER_IFACE,
                                                _WATCHER_PATH)
                dbus.Interface(watcher, _WATCHER_IFACE) \
                    .RegisterStatusNotifierItem(self._service_name)
                _log.info("SNI registered as %s", self._service_name)
            except Exception:
                _log.exception("Failed to register SNI with watcher")
                raise

        # AppIndicatorIcon-compatible API ------------------------------

        def set_icon_full(self, icon_name, tooltip=''):
            if icon_name and icon_name != self._icon_name:
                self._icon_name = icon_name
                self.NewIcon()
            if tooltip and tooltip != self._tooltip_text:
                self._tooltip_text = tooltip
                self.NewToolTip()

        def set_tooltip(self, tooltip):
            if tooltip != self._tooltip_text:
                self._tooltip_text = tooltip
                self.NewToolTip()

        def set_gtk_menu(self, menu):
            """Rebuild the DBusMenu tree from the given Gtk.Menu."""
            if self._dbusmenu is not None:
                self._dbusmenu.set_root_from_gtk(menu)

        def RemoveIcon(self):
            self._status = 'Passive'
            self.NewStatus(self._status)

        def Destroy(self):
            try:
                self.remove_from_connection()
            except Exception:
                pass
            if self._dbusmenu is not None:
                try:
                    self._dbusmenu.remove_from_connection()
                except Exception:
                    pass
                self._dbusmenu = None
            self._bus_name = None

        # SNI-only extension -------------------------------------------

        def set_left_click_callback(self, callback):
            """Bind a zero-arg callable to left-click (Activate)."""
            self._left_click_cb = callback

        # SNI methods (called by the host) -----------------------------

        @dbus.service.method(_ITEM_IFACE, in_signature='ii',
                             out_signature='')
        def Activate(self, x, y):
            _log.debug("Activate(%s, %s)", x, y)
            if self._left_click_cb is not None:
                try:
                    self._left_click_cb()
                except Exception:
                    _log.exception("Activate callback failed")

        @dbus.service.method(_ITEM_IFACE, in_signature='ii',
                             out_signature='')
        def ContextMenu(self, x, y):
            # With Menu pointing at /MenuBar, well-behaved hosts render
            # the DBusMenu themselves and never call this. Kept as a no-op
            # so misbehaving hosts don't get a NoSuchMethod error.
            pass

        @dbus.service.method(_ITEM_IFACE, in_signature='ii',
                             out_signature='')
        def SecondaryActivate(self, x, y):
            pass

        @dbus.service.method(_ITEM_IFACE, in_signature='is',
                             out_signature='')
        def Scroll(self, delta, orientation):
            pass

        # SNI signals (emitted on property changes) --------------------

        @dbus.service.signal(_ITEM_IFACE, signature='')
        def NewIcon(self):
            pass

        @dbus.service.signal(_ITEM_IFACE, signature='')
        def NewTitle(self):
            pass

        @dbus.service.signal(_ITEM_IFACE, signature='')
        def NewToolTip(self):
            pass

        @dbus.service.signal(_ITEM_IFACE, signature='s')
        def NewStatus(self, status):
            pass

        # org.freedesktop.DBus.Properties ------------------------------

        @dbus.service.method(_PROPERTIES_IFACE,
                             in_signature='ss', out_signature='v')
        def Get(self, interface, prop):
            if interface != _ITEM_IFACE:
                raise dbus.exceptions.DBusException(
                    f"Unknown interface: {interface}",
                    name='org.freedesktop.DBus.Error.UnknownInterface')
            return self._get_property(prop)

        @dbus.service.method(_PROPERTIES_IFACE,
                             in_signature='s', out_signature='a{sv}')
        def GetAll(self, interface):
            if interface != _ITEM_IFACE:
                raise dbus.exceptions.DBusException(
                    f"Unknown interface: {interface}",
                    name='org.freedesktop.DBus.Error.UnknownInterface')
            names = ('Category', 'Id', 'Title', 'Status', 'WindowId',
                     'IconThemePath', 'IconName', 'IconPixmap',
                     'OverlayIconName', 'OverlayIconPixmap',
                     'AttentionIconName', 'AttentionIconPixmap',
                     'AttentionMovieName', 'ToolTip',
                     'ItemIsMenu', 'Menu')
            return {n: self._get_property(n) for n in names}

        @dbus.service.method(_PROPERTIES_IFACE,
                             in_signature='ssv', out_signature='')
        def Set(self, interface, prop, value):
            raise dbus.exceptions.DBusException(
                f"Property is read-only: {prop}",
                name='org.freedesktop.DBus.Error.PropertyReadOnly')

        def _get_property(self, prop):
            if prop == 'Category':
                return dbus.String(self._category)
            if prop == 'Id':
                return dbus.String(self._id)
            if prop == 'Title':
                return dbus.String(self._title)
            if prop == 'Status':
                return dbus.String(self._status)
            if prop == 'WindowId':
                return dbus.Int32(0)
            if prop == 'IconThemePath':
                return dbus.String(self._icon_theme_path)
            if prop == 'IconName':
                return dbus.String(self._icon_name)
            if prop in ('OverlayIconName', 'AttentionIconName',
                        'AttentionMovieName'):
                return dbus.String('')
            if prop in ('IconPixmap', 'OverlayIconPixmap',
                        'AttentionIconPixmap'):
                return dbus.Array([], signature='(iiay)')
            if prop == 'ToolTip':
                # (icon-name, icon-pixmap, title, description) per SNI spec.
                return dbus.Struct(
                    (dbus.String(''),
                     dbus.Array([], signature='(iiay)'),
                     dbus.String(self._tooltip_text),
                     dbus.String('')),
                    signature='(sa(iiay)ss)')
            if prop == 'ItemIsMenu':
                # The whole point of this module: left-click → Activate(),
                # not "show the menu".
                return dbus.Boolean(False)
            if prop == 'Menu':
                return dbus.ObjectPath(_DBUSMENU_PATH)
            raise dbus.exceptions.DBusException(
                f"Unknown property: {prop}",
                name='org.freedesktop.DBus.Error.UnknownProperty')

else:

    class SniIcon:  # pragma: no cover - stub when dbus-python is missing
        def __init__(self, *args, **kwargs):
            raise ImportError(f"SNI not available: {SNI_ERROR}")
