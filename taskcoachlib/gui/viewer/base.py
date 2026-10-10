# -*- coding: utf-8 -*-

"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2016 Task Coach developers <developers@taskcoach.org>
Copyright (C) 2008 Rob McMullen <rob.mcmullen@gmail.com>
Copyright (C) 2008 Thomas Sonne Olesen <tpo@sonnet.dk>

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

import contextlib
import wx
from taskcoachlib import patterns, widgets, command, render
from taskcoachlib.config import settings
from taskcoachlib.i18n import _
from taskcoachlib.gui import uicommand, toolbar
from taskcoachlib.gui.icons import image_list_cache
from wx.lib.agw import hypertreelist
from taskcoachlib.meta.debug import log_step
from . import mixin


class ViewerMeta(type(wx.Panel), patterns.NumberedInstances):
    pass


class Viewer(wx.Panel, patterns.Observer, metaclass=ViewerMeta):
    """A Viewer shows domain objects (e.g. tasks or efforts) by means of a
    widget (e.g. a ListCtrl or a TreeListCtrl)."""

    defaultTitle = "Subclass responsibility"
    defaultBitmap = "Subclass responsibility"
    coreObjectType = None

    def __init__(self, parent, task_file, *args, **kwargs):
        patterns.Observer.__init__(self)
        super().__init__(parent, -1)
        self.parent = parent
        self.taskFile = task_file
        self.__settingsSection = kwargs.pop("settingsSection")
        self.__freezeCount = 0
        self.__in_pass = False
        # Items changed during a bulk operation or a scheduler pass
        self.__pendingRefreshItems = set()
        # The how maniest of this viewer type are we? Used for settings
        self.__instanceNumber = kwargs.pop("instanceNumber")
        self.__use_separate_settings_section = kwargs.pop(
            "use_separate_settings_section", True
        )
        # Flag so that we don't notify observers while we're selecting all items
        self.__selectingAllItems = False
        # Flag set once the viewer is detached, so that selection events fired
        # by the widget while it is being destroyed (e.g. hidden viewers in the
        # export dialog) are ignored before touching any dead wx object.
        self.__detached = False
        # Popup menus we have to destroy before closing the viewer to prevent
        # memory leakage:
        self._popupMenus = []
        # What are we presenting:
        self.__presentation = self.create_sorter(
            self.createFilter(self.domainObjectsToView())
        )
        # The widget used to present the presentation:
        self.widget = self.create_widget()
        self.widget.SetBackgroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        )
        self.toolbar = toolbar.ToolBar(self, (toolbar.TOOLBAR_ICON_SIZE,) * 2)
        self.init_layout()
        self.register_presentation_observers()
        # Re-center when auto-scroll is turned back on
        self.registerObserver(
            self.on_auto_scroll_changed,
            eventType="view.autoscrollselection",
        )
        # Times are drawn as decimal hours or not: redraw on a change
        self.registerObserver(
            self.__on_decimal_time_changed, eventType="feature.decimal_time"
        )
        self.refresh()

        for event_type, handler in (
            ("taskfile.aboutToRead", self.on_begin_io),
            ("taskfile.aboutToClear", self.on_begin_io),
            ("taskfile.justRead", self.on_end_io),
            ("taskfile.justCleared", self.on_end_io),
        ):
            self.registerObserver(
                handler, eventType=event_type, eventSource=self.taskFile
            )
        # Frozen during a command's bulk changes, refreshed once after
        self.registerObserver(
            self.on_begin_bulk_operation, eventType="command.aboutToBulkModify"
        )
        self.registerObserver(
            self.on_end_bulk_operation, eventType="command.justBulkModified"
        )
        # Also refreshed once after a scheduler pass, which can change
        # every row (a file merged, the theme changed)
        self.registerObserver(
            self.on_begin_pass, eventType="scheduler.aboutToPass"
        )
        self.registerObserver(self.on_end_pass, eventType="scheduler.pass")

        patterns.later.soon(self, self.__DisplayBalloon)

    def __DisplayBalloon(self):
        # Run later: the viewer may be closing by then
        if not self or self.IsBeingDeleted():
            return
        # AuiFloatingFrame is instantiated from framemanager, we can't derive it from BalloonTipManager
        if self.toolbar.IsShownOnScreen() and hasattr(
            wx.GetTopLevelParent(self), "AddBalloonTip"
        ):
            wx.GetTopLevelParent(self).AddBalloonTip(
                "customizabletoolbars",
                self.toolbar,
                title=_("Toolbars are customizable"),
                get_rect=lambda: self.toolbar.GetToolRect(
                    self.toolbar.getToolIdByCommand("EditToolBarPerspective")
                ),
                message=_(
                    """Click on the gear icon on the right to add buttons and rearrange them."""
                ),
            )

    def on_begin_io(self, event):  # pylint: disable=W0613
        self.__freezeCount += 1
        self.__presentation.freeze()

    def on_end_io(self, event):  # pylint: disable=W0613
        self.__freezeCount -= 1
        self.__presentation.thaw()
        if self.__freezeCount == 0:
            # Every row redrawn, those changed meanwhile too (the first
            # pass runs as the file is read)
            self.__pendingRefreshItems = set()
            self.refresh()

    def on_begin_bulk_operation(self, event=None):  # pylint: disable=W0613
        """Freeze viewer and presentation to batch updates during bulk operations."""
        self.__freezeCount += 1
        self.__presentation.freeze()

    def on_end_bulk_operation(self, event=None):  # pylint: disable=W0613
        """Thaw viewer and presentation after bulk operation, refresh only changed items."""
        self.__freezeCount -= 1
        self.__presentation.thaw()
        self.__refresh_pending_items()

    def on_begin_pass(self, event):  # pylint: disable=W0613
        self.__in_pass = True

    def on_end_pass(self, event):  # pylint: disable=W0613
        self.__in_pass = False
        self.__refresh_pending_items()

    def __refresh_pending_items(self):
        if self.__freezeCount or self.__in_pass:
            return
        items, self.__pendingRefreshItems = self.__pendingRefreshItems, set()
        if items:
            self.refresh_changed_items(items)

    def activate(self):
        pass

    def _bind_activation_events(self, window):
        """A click anywhere in the viewer, with either button, makes its
        pane the active one. Text controls handle their own focus."""
        if isinstance(window, (wx.TextCtrl, wx.SearchCtrl, wx.ComboBox)):
            return
        if window is self.widget:
            self.__bind_widget_clicks(window)
            return
        for event_type in (wx.EVT_LEFT_DOWN, wx.EVT_RIGHT_DOWN):
            window.Bind(event_type, self._onViewerClick)
        for child in window.GetChildren():
            self._bind_activation_events(child)

    def __bind_widget_clicks(self, window):
        # A list takes the focus on a click, which activates its pane;
        # the calendars, timeline and square map take none
        for event_type in (wx.EVT_LEFT_DOWN, wx.EVT_RIGHT_DOWN):
            window.Bind(event_type, self.__on_widget_click)
        for child in window.GetChildren():
            if not child.IsTopLevel():
                self.__bind_widget_clicks(child)

    def _onViewerClick(self, event):
        """Handle clicks on the viewer to activate its pane."""
        wx.PostEvent(self, wx.ChildFocusEvent(self))
        self.SetFocus()  # Clear focus from other controls (e.g., search box)
        event.Skip()

    def __on_widget_click(self, event):
        event.Skip()
        focus = wx.Window.FindFocus()
        while focus is not None and focus is not self:
            focus = focus.GetParent()
        if focus is None:
            # Activating the pane gives the viewer the focus
            wx.PostEvent(self, wx.ChildFocusEvent(self))

    def domainObjectsToView(self):
        """Return the domain objects that this viewer should display. For
        global viewers this will be part of the task file,
        e.g. self.taskFile.tasks(), for local viewers this will be a list
        of objects passed to the viewer constructor."""
        raise NotImplementedError

    def register_presentation_observers(self):
        self.removeObserver(self.on_presentation_changed)
        self.registerObserver(
            self.on_presentation_changed,
            eventType=self.presentation().addItemEventType(),
            eventSource=self.presentation(),
        )
        self.registerObserver(
            self.on_presentation_changed,
            eventType=self.presentation().removeItemEventType(),
            eventSource=self.presentation(),
        )
        self.registerObserver(self.on_new_item, eventType="newitem")

    def detach(self):
        """Should be called by viewer.container before closing the viewer"""
        self.__detached = True
        observers = [self, self.presentation()]
        observable = self.presentation()
        while True:
            try:
                observable = observable.observable()
            except AttributeError:
                break
            else:
                observers.append(observable)
        for observer in observers:
            if hasattr(observer, "removeInstance"):
                observer.removeInstance()

        for popup_menu in self._popupMenus:
            try:
                popup_menu.clearMenu()
                popup_menu.Destroy()
            except RuntimeError:
                log_step(
                    "detach: popup menu already dead %x" % id(popup_menu),
                    prefix="DEAD-OBJ",
                    exc=True,
                )

        for handler in (
            self.on_begin_io,
            self.on_end_io,
            self.on_begin_bulk_operation,
            self.on_end_bulk_operation,
            self.on_begin_pass,
            self.on_end_pass,
        ):
            self.removeObserver(handler)

        self.presentation().detach()
        self.toolbar.detach()

    def viewer_status_event_type(self):
        return "viewer%s.status" % id(self)

    def selection_changed_event_type(self):
        return "viewer%s.selection" % id(self)

    def view_settings_changed_event_type(self):
        return "viewer%s.view_settings" % id(self)

    @property
    def has_selection(self):
        w = self.widget
        if hasattr(w, "has_selection"):
            return w.has_selection
        return bool(w.curselection())

    @property
    def has_single_selection(self):
        w = self.widget
        if hasattr(w, "has_single_selection"):
            return w.has_single_selection
        return len(w.curselection()) == 1

    @property
    def is_task(self):
        return self.coreObjectType == "tasks"

    @property
    def is_note(self):
        return self.coreObjectType == "notes"

    @property
    def is_category(self):
        return self.coreObjectType == "categories"

    @property
    def is_effort(self):
        return self.coreObjectType == "efforts"

    @property
    def is_attachment(self):
        return self.coreObjectType == "attachments"

    @property
    def has_filter(self):
        """Whether any filter is active. Overridden by filterable viewer
        mixins."""
        return False

    def send_viewer_status_event(self):
        patterns.Event(self.viewer_status_event_type(), self).send()

    def statusMessages(self):
        return "", ""

    def title(self):
        return self.options.title or self.defaultTitle

    def set_title(self, title):
        title_to_save_in_settings = "" if title == self.defaultTitle else title
        self.options.title = title_to_save_in_settings
        self.parent.set_pane_title(self, title)
        self.parent.manager.Update()

    def init_layout(self):
        self._sizer = wx.BoxSizer(wx.VERTICAL)  # pylint: disable=W0201
        self._sizer.Add(self.toolbar, flag=wx.EXPAND)
        self._sizer.Add(self.widget, proportion=1, flag=wx.EXPAND)
        self.SetSizer(
            self._sizer
        )  # Changed from SetSizerAndFit to prevent locking MinSize
        # Prevent GetEffectiveMinSize() from returning child's BestSize
        self.SetMinSize((100, 50))
        self._bind_activation_events(self)

    def create_widget(self, *args):
        raise NotImplementedError

    def createImageList(self):
        return image_list_cache.image_list

    def getWidget(self):
        return self.widget

    def SetFocus(self, *args, **kwargs):
        try:
            self.widget.SetFocus(*args, **kwargs)
        except RuntimeError as e:
            log_step(
                "SetFocus on dead widget %s: %s"
                % (self.__class__.__name__, e),
                prefix="DEAD-OBJ",
                exc=True,
            )

    def create_sorter(self, collection):
        """This method can be overridden to decorate the presentation with a
        sorter."""
        return collection

    def createFilter(self, collection):
        """This method can be overridden to decorate the presentation with a
        filter."""
        return collection

    def on_attribute_changed(self, event):
        if self.__freezeCount or self.__in_pass:
            # Refreshed once, after the bulk operation or the pass
            self.__pendingRefreshItems.update(event.sources())
        else:
            self.refresh_changed_items(event.sources())

    def refresh_changed_items(self, items):
        """Refresh the rows of the changed items. A viewer whose rows
        show other items' values refreshes those rows instead."""
        self.refreshItems(*items)

    def on_new_item(self, event):
        self.select(
            [
                item
                for item in list(event.values())
                if item in self.presentation()
            ]
        )

    def on_presentation_changed(self, event):  # pylint: disable=W0613
        """Whenever our presentation is changed (items added, items removed)
        the viewer refreshes itself."""

        def items_removed():
            return event.type() == self.presentation().removeItemEventType()

        # BEFORE refresh - capture selection info while widget has old state
        selection_info = None
        if items_removed():
            selection_info = self._capture_selection_info()

        self.refresh()

        # AFTER refresh - select next if selection became empty
        if (
            items_removed()
            and hasattr(self.widget, "curselection")
            and not self.widget.curselection()
            and selection_info
        ):
            # Selecting scrolls the widget, which "stable" mode must not
            keep_viewport = getattr(
                self.widget, "stable_viewport", contextlib.nullcontext
            )
            with keep_viewport():
                self.select_next_items_after_removal(selection_info)
        # Center on selected item — tree views use scroll_to_selection_centered,
        # list views use ensureSelectionVisible (native wx scrollbar management)
        if hasattr(self.widget, "scroll_to_selection_centered"):
            self.widget.scroll_to_selection_centered()
        elif hasattr(self.widget, "ensureSelectionVisible"):
            self.widget.ensureSelectionVisible()
        self.send_viewer_status_event()

    def __on_decimal_time_changed(self, event):  # pylint: disable=W0613
        self.refresh()

    def on_auto_scroll_changed(self, event=None):
        """Re-center on the selection when auto-scroll is turned back
        on."""
        if not settings.view.autoscrollselection:
            return
        if hasattr(self.widget, "scroll_to_selection_centered"):
            self.widget.scroll_to_selection_centered()
        elif hasattr(self.widget, "ensureSelectionVisible"):
            self.widget.ensureSelectionVisible()

    def _capture_selection_info(self):
        """Capture the rows around the selection before refresh.

        The removed items are already gone from the presentation by the
        time this runs, so the neighbouring rows can only be read from
        the widget, which still shows the old contents.
        """
        if not hasattr(self.widget, "selection_neighbours"):
            return None
        above, below = self.widget.selection_neighbours()
        if above or below:
            return {"above": above, "below": below}
        return None

    def select_next_items_after_removal(self, selection_info):
        """Select the row that moved into the removed rows' place, so
        the selection stays on the same line; the row above when they
        were the last (docs/LIST_MANAGEMENT.md, Which Row Gets
        Selected: ruled, the same in every view)."""
        new_selection = self.__first_survivor(
            selection_info["below"]
        ) or self.__first_survivor(selection_info["above"])
        if new_selection:
            self.select([new_selection])

    def __first_survivor(self, items):
        """The first of items still in the presentation."""
        presentation = self.presentation()
        for item in items:
            if item in presentation:
                return item
        return None

    def onSelect(self, event=None):  # pylint: disable=W0613
        """The selection of items in the widget has been changed. Notify
        our observers."""

        if self.__detached or not self:
            # The widget fired a selection event while the viewer is being
            # torn down (e.g. hidden viewers in the export dialog); "not
            # self" is false once the C++ object is deleted
            return

        if self.IsBeingDeleted() or self.__selectingAllItems:
            # Some widgets send selection events while deleting all
            # items as they are destroyed
            return

        # Toolbar buttons follow the selection (_SelectionSync)
        patterns.Event(self.selection_changed_event_type(), self).send()

        # The status bar reads the selection itself, 500 ms later
        patterns.later.soon(self, self.send_viewer_status_event)

    def updateSelection(self, send_status_event=True):
        """Legacy method - kept for subclass compatibility.

        With SSOT selection (curselection() queries widget fresh),
        there's no cache to update. Just fires status event if requested.
        """
        if send_status_event:
            self.send_viewer_status_event()

    def freeze(self):
        self.widget.Freeze()

    def thaw(self):
        self.widget.Thaw()

    def needs_second_refresh(self):
        """Whether tracked items must be redrawn every second (see
        SecondRefresher). Viewers that show nothing that changes every
        second override this."""
        return True

    def refresh(self):
        if self and not self.__freezeCount:
            self.widget.RefreshAllItems(len(self.presentation()))

    def refresh_order(self):
        """The rows' order changed, not what they show: a widget that
        can moves its rows (a tree), else the whole refresh."""
        reorder = getattr(self.widget, "reorder_items", None)
        if self and not self.__freezeCount and reorder and reorder():
            return
        self.refresh()

    def refreshItems(self, *items):
        if not self.__freezeCount:
            shown = set(self.presentation())
            items = [item for item in items if item in shown]
            self.widget.RefreshItems(*items)  # pylint: disable=W0142

    def select(self, items):
        self.widget.select(items)

    def curselection(self):
        """Return currently selected domain objects. Always fresh from widget.

        SSOT principle: Always query widget live, no cache for reads.
        Commands get fresh selection when user triggers action.
        Status bar queries fresh after its 500ms debounce.
        """
        return self.widget.curselection()

    def isselected(self, item):
        """Returns True if the given item is selected. See
        L{EffortViewer} for an explanation of why this may be
        different than 'if item in viewer.curselection()'."""
        return item in self.curselection()

    def select_all(self):
        """Select all items in the presentation. Since some of the widgets we
        use may send events for each individual item (!) we stop processing
        selection events while we select all items."""
        self.__selectingAllItems = True
        self.widget.select_all()
        # Later, to make sure we start processing selection events
        # after all selection events have been fired (and ignored):
        patterns.later.soon(self, self.end_of_select_all)

    def end_of_select_all(self):
        # Run later: the viewer may be closing by then
        if not self or self.IsBeingDeleted():
            return
        self.__selectingAllItems = False
        # Pretend we received one selection event for the select_all() call:
        self.onSelect()

    def clear_selection(self):
        self.widget.clear_selection()

    def size(self):
        return self.widget.GetItemCount()

    def presentation(self):
        """Return the domain objects that this viewer is currently
        displaying."""
        return self.__presentation

    def set_presentation(self, presentation):
        """Change the presentation of the viewer."""
        self.__presentation = presentation

    def widgetCreationKeywordArguments(self):
        return {}

    def is_showing_tasks(self):
        return False

    def is_showing_effort(self):
        return False

    def is_showing_categories(self):
        return False

    def is_showing_notes(self):
        return False

    def is_showing_attachments(self):
        return False

    def visibleColumns(self):
        return [widgets.Column("subject", _("Subject"))]

    def bitmap(self):
        """Return the bitmap that represents this viewer. Used for the
        'Viewer->New viewer' menu item, for example."""
        return self.defaultBitmap  # Class attribute of concrete viewers

    @property
    def options(self):
        """This viewer's own section of the settings, its options as
        attributes."""
        return settings.section(self.settingsSection())

    def settingsSection(self):
        """Return the settings section of this viewer."""
        section = self.__settingsSection
        if self.__use_separate_settings_section and self.__instanceNumber > 0:
            # We're not the first viewer of our class, so we need a different
            # settings section than the default one.
            section += str(self.__instanceNumber)
            if not settings.has_section(section):
                # Our section does not exist yet. Create it and copy the
                # settings from the previous section as starting point. We're
                # copying from the previous section instead of the default
                # section so that when the user closes a viewer and then opens
                # a new one, the settings of that closed viewer are reused.
                settings.add_section(
                    section, copy_from=self.previousSettingsSection()
                )
        return section

    def previousSettingsSection(self):
        """Return the settings section of the previous viewer of this
        class."""
        previous_section_number = self.__instanceNumber - 1
        while previous_section_number > 0:
            previous_section = self.__settingsSection + str(
                previous_section_number
            )
            if settings.has_section(previous_section):
                return previous_section
            previous_section_number -= 1
        return self.__settingsSection

    def hasModes(self):
        return False

    def getModeUICommands(self):
        return []

    def isSortable(self):
        return False

    def getSortUICommands(self):
        return []

    def isSearchable(self):
        return False

    def hasHideableColumns(self):
        return False

    def getColumnUICommands(self):
        return []

    def is_filterable(self):
        return False

    def getFilterUICommands(self):
        return []

    def supportsRounding(self):
        return False

    def getRoundingUICommands(self):
        return []

    def createToolBarUICommands(self):
        """UI commands to put on the toolbar of this viewer."""
        # On the list, not the viewer: an accelerator table takes its
        # keys from every child first, so the toolbar's search box
        # would lose Enter and its clipboard keys
        table = wx.AcceleratorTable(
            [
                (wx.ACCEL_CMD, ord("X"), wx.ID_CUT),
                (wx.ACCEL_CMD, ord("C"), wx.ID_COPY),
                (wx.ACCEL_CMD, ord("V"), wx.ID_PASTE),
                (wx.ACCEL_NORMAL, wx.WXK_RETURN, wx.ID_EDIT),
                (wx.ACCEL_NORMAL, wx.WXK_NUMPAD_ENTER, wx.ID_EDIT),
                (wx.ACCEL_CTRL, wx.WXK_DELETE, wx.ID_DELETE),
            ]
        )
        self.widget.SetAcceleratorTable(table)

        clipboard_tool_bar_ui_commands = (
            self.createClipboardToolBarUICommands()
        )
        creation_tool_bar_ui_commands = self.createCreationToolBarUICommands()
        edit_tool_bar_ui_commands = self.createEditToolBarUICommands()
        action_tool_bar_ui_commands = self.createActionToolBarUICommands()
        mode_tool_bar_ui_commands = self.createModeToolBarUICommands()

        def separator(ui_commands, *other_ui_commands):
            return (
                (uicommand.Separator(),)
                if (ui_commands and any(other_ui_commands))
                else ()
            )

        clipboard_separator = separator(
            clipboard_tool_bar_ui_commands,
            creation_tool_bar_ui_commands,
            edit_tool_bar_ui_commands,
            action_tool_bar_ui_commands,
            mode_tool_bar_ui_commands,
        )
        creation_separator = separator(
            creation_tool_bar_ui_commands,
            edit_tool_bar_ui_commands,
            action_tool_bar_ui_commands,
            mode_tool_bar_ui_commands,
        )
        edit_separator = separator(
            edit_tool_bar_ui_commands,
            action_tool_bar_ui_commands,
            mode_tool_bar_ui_commands,
        )
        action_separator = separator(
            action_tool_bar_ui_commands, mode_tool_bar_ui_commands
        )

        return (
            clipboard_tool_bar_ui_commands
            + clipboard_separator
            + creation_tool_bar_ui_commands
            + creation_separator
            + edit_tool_bar_ui_commands
            + edit_separator
            + action_tool_bar_ui_commands
            + action_separator
            + mode_tool_bar_ui_commands
        )

    def getToolBarPerspective(self):
        return self.options.toolbarperspective

    def saveToolBarPerspective(self, perspective):
        self.options.toolbarperspective = perspective

    def createClipboardToolBarUICommands(self):
        """UI commands for manipulating the clipboard (cut, copy, paste)."""
        cut_command = uicommand.EditCut(viewer=self)
        copy_command = uicommand.EditCopy(viewer=self)
        paste_command = uicommand.EditPaste(viewer=self)
        cut_command.bind(self, wx.ID_CUT)
        copy_command.bind(self, wx.ID_COPY)
        paste_command.bind(self, wx.ID_PASTE)
        return cut_command, copy_command, paste_command

    def createCreationToolBarUICommands(self):
        """UI commands for creating new items."""
        return ()

    def createEditToolBarUICommands(self):
        """UI commands for editing items."""
        edit_command = uicommand.Edit(viewer=self)
        self.deleteUICommand = uicommand.Delete(
            viewer=self
        )  # For unittests pylint: disable=W0201
        edit_command.bind(self, wx.ID_EDIT)
        self.deleteUICommand.bind(self, wx.ID_DELETE)
        return edit_command, self.deleteUICommand

    def createActionToolBarUICommands(self):
        """UI commands for actions."""
        return ()

    def createModeToolBarUICommands(self):
        """UI commands for mode switches (e.g. list versus tree mode)."""
        return ()

    def newItemDialog(self, *args, **kwargs):
        icon_id = kwargs.pop("icon_id")
        new_item_command = self.newItemCommand(*args, **kwargs)
        new_item_command.do()
        return self.editItemDialog(
            new_item_command.items, icon_id, items_are_new=True
        )

    def newSubItemDialog(self, icon_id):
        parents = self.curselection()
        new_sub_item_command = self.newSubItemCommand()
        new_sub_item_command.do()
        # Expand parent notes so the newly created subnotes are visible
        for parent in parents:
            parent.expand(True, context=self.settingsSection())
        return self.editItemDialog(
            new_sub_item_command.items, icon_id, items_are_new=True
        )

    def editItemDialog(
        self, items, icon_id, columnName="", items_are_new=False
    ):
        self.cancel_tip()
        parent = wx.GetTopLevelParent(self)
        # If the viewer is inside an Editor dialog (e.g. EffortViewer inside
        # TaskEditor), parent to main window instead. Otherwise Destroy() on
        # the parent editor cascades to this editor without EVT_CLOSE, leaving
        # dangling observers/subscriptions and causing C++ segfaults.
        if isinstance(parent, wx.Dialog):
            parent = wx.GetApp().TopWindow
        editor_class = self.itemEditorClass()
        return editor_class(
            parent,
            items,
            self.presentation(),
            self.taskFile,
            icon_id=icon_id,
            columnName=columnName,
            items_are_new=items_are_new,
        )

    def cancel_tip(self):
        """No list tooltip over an editor opened from the list."""
        cancel_tip = getattr(self.widget, "cancel_tip", None)
        if cancel_tip:
            cancel_tip()

    def itemEditorClass(self):
        raise NotImplementedError

    def newItemCommand(self, *args, **kwargs):
        return self.newItemCommandClass()(self.presentation(), *args, **kwargs)

    def newItemCommandClass(self):
        raise NotImplementedError

    def newSubItemCommand(self):
        return self.newSubItemCommandClass()(
            self.presentation(), self.curselection()
        )

    def newSubItemCommandClass(self):
        raise NotImplementedError

    def deleteItemCommand(self):
        return self.deleteItemCommandClass()(
            self.presentation(), self.curselection()
        )

    def deleteItemCommandClass(self):
        return command.DeleteCommand

    def cutItemCommand(self):
        return self.cutItemCommandClass()(
            self.presentation(), self.curselection()
        )

    def cutItemCommandClass(self):
        return command.CutCommand

    def pasteItemCommand(self):
        return self.pasteItemCommandClass()(self.presentation())

    def pasteItemCommandClass(self):
        return command.PasteCommand

    def getSupportedPasteTypes(self):
        """Return tuple of domain object types that can be pasted into this viewer.

        Override in subclasses to restrict paste to specific types.
        Return None to accept any type (default behavior).
        """
        return None

    def onEditSubject(self, item, newValue):
        command.EditSubjectCommand(items=[item], newValue=newValue).do()

    def onEditDescription(self, item, newValue):
        command.EditDescriptionCommand(items=[item], newValue=newValue).do()

    def getItemTooltipData(self, item):
        lines = [line.rstrip("\r") for line in item.description().split("\n")]
        return [(None, lines)] if lines and lines != [""] else []


class CategorizableViewerMixin(object):
    def getItemTooltipData(self, item):
        return [
            (
                "nuvola_places_folder-downloads",
                (
                    [
                        ", ".join(
                            sorted(
                                [cat.subject() for cat in item.categories()]
                            )
                        )
                    ]
                    if item.categories()
                    else []
                ),
            )
        ] + super().getItemTooltipData(item)


class WithAttachmentsViewerMixin(object):
    def getItemTooltipData(self, item):
        return [
            (
                "nuvola_status_mail-attachment",
                sorted([str(attachment) for attachment in item.attachments()]),
            )
        ] + super().getItemTooltipData(item)


class ListViewer(Viewer):  # pylint: disable=W0223
    def is_tree_viewer(self):
        return False

    def visible_items(self):
        """Iterate over the items in the presentation."""
        for item in self.presentation():
            yield item

    def get_item_with_index(self, index):
        try:
            return self.presentation()[index]
        except IndexError:
            return None


class TreeViewer(Viewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.__selection_before = None
        super().__init__(*args, **kwargs)
        self.widget.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.__remember_selection)
        self.widget.Bind(
            wx.EVT_TREE_ITEM_COLLAPSING, self.__remember_selection
        )
        self.widget.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.on_item_expanded)
        self.widget.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.on_item_collapsed)

    def __remember_selection(self, event):
        event.Skip()
        self.__selection_before = self.widget.GetSelections()

    def __announce_selection_change(self):
        # Collapsing drops the hidden children from the selection and
        # expanding brings them back, without a selection event: the
        # status bar and the toolbar would keep the old selection
        if self.widget.GetSelections() != self.__selection_before:
            self.onSelect()
        self.__selection_before = None

    def on_item_expanded(self, event):
        self.__handleExpandedOrCollapsedItem(event, expanded=True)
        self.__announce_selection_change()
        self.widget._schedule_scrollbar_adjustment()

    def on_item_collapsed(self, event):
        self.__handleExpandedOrCollapsedItem(event, expanded=False)
        self.__announce_selection_change()
        self.widget._schedule_scrollbar_adjustment()

    def __handleExpandedOrCollapsedItem(self, event, expanded):
        event.Skip()
        tree_item = event.GetItem()
        # If we get an expanded or collapsed event for the root item, ignore it
        if tree_item == self.widget.GetRootItem():
            return
        item = self.widget.GetItemPyData(tree_item)
        item.expand(expanded, context=self.settingsSection())

    def expand_all(self):
        """Expand all items, recursively."""
        # Since the widget does not send EVT_TREE_ITEM_EXPANDED when expanding
        # all items, we have to do the bookkeeping ourselves:
        for item in self.visible_items():
            item.expand(True, context=self.settingsSection(), notify=False)
        self.refresh()
        self.widget._schedule_scrollbar_adjustment()

    def collapse_all(self):
        """Collapse all items, recursively."""
        # Since the widget does not send EVT_TREE_ITEM_COLLAPSED when collapsing
        # all items, we have to do the bookkeeping ourselves:
        for item in self.visible_items():
            item.expand(False, context=self.settingsSection(), notify=False)
        self.refresh()
        self.widget._schedule_scrollbar_adjustment()

    def createModeToolBarUICommands(self):
        return super().createModeToolBarUICommands() + (
            uicommand.ViewExpandAll(viewer=self),
            uicommand.ViewCollapseAll(viewer=self),
        )

    def is_tree_viewer(self):
        return True

    def select(self, items):
        for item in items:
            self.__expand_item_recursively(item)
        self.refresh()
        super().select(items)

    def __expand_item_recursively(self, item):
        parent = self.get_item_parent(item)
        if parent:
            parent.expand(True, context=self.settingsSection(), notify=False)
            self.__expand_item_recursively(parent)

    def _capture_selection_info(self):
        """Widgets without a row order (timeline, calendar, square map)
        give the selected item's parent and place among its siblings."""
        if not hasattr(self.widget, "curselection"):
            return None
        if hasattr(self.widget, "selection_neighbours"):
            return super()._capture_selection_info()
        curselection = self.widget.curselection()
        if curselection and curselection[0] is not None:
            selected_item = curselection[0]
            parent = self.get_item_parent(selected_item)
            siblings = self.children(parent)
            index = (
                siblings.index(selected_item)
                if selected_item in siblings
                else 0
            )
            return {"parent": parent, "index": index}
        return None

    def select_next_items_after_removal(self, selection_info):
        if "above" in selection_info:
            super().select_next_items_after_removal(selection_info)
            return
        parent = selection_info["parent"]
        index = selection_info["index"]
        # Parent might have been deleted too - check if still in presentation
        if parent is not None and parent not in self.presentation():
            parent = None
        siblings = self.children(parent)
        new_selection = (
            siblings[min(len(siblings) - 1, index)] if siblings else parent
        )
        if new_selection:
            self.select([new_selection])

    def visible_items(self):
        """Iterate over the items in the presentation."""

        def yield_items_and_children(items):
            sorted_items = [
                item for item in self.presentation() if item in items
            ]
            for item in sorted_items:
                yield item
                children = self.children(item)
                if children:
                    for child in yield_items_and_children(children):
                        yield child

        for item in yield_items_and_children(self.get_root_items()):
            yield item

    def get_root_items(self):
        """Allow for overriding what the rootItems are."""
        return self.presentation().rootItems()

    def get_item_parent(self, item):
        """Allow for overriding what the parent of an item is."""
        return item.parent() if item is not None else None

    def get_item_expanded(self, item):
        return item.isExpanded(context=self.settingsSection())

    def children(self, parent=None):
        if parent:
            # The parent's own subitems the view shows, in its order
            presentation = self.presentation()
            if hasattr(presentation, "children_of"):
                return presentation.children_of(parent)
            children = set(parent.children())
            if children:
                return [
                    child for child in self.presentation() if child in children
                ]
            else:
                return []
        else:
            return self.get_root_items()

    def getItemText(self, item):
        return item.subject()


class ViewerWithColumns(Viewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.__initDone = False
        self._columns = []
        self.__visibleColumns = []
        self.__columnUICommands = []
        super().__init__(*args, **kwargs)
        self.init_columns()
        self.__initDone = True
        self.refresh()
        # Relative dates ("Today", "Yesterday") change at midnight;
        # removed by detach()
        self.registerObserver(
            self.__on_date_changed, eventType="scheduler.date"
        )

    def __on_date_changed(self, event):  # pylint: disable=W0613
        self.refresh()

    def hasHideableColumns(self):
        return True

    def hasOrderingColumn(self):
        for column in self.__visibleColumns:
            if column.name() == "ordering":
                return True
        return False

    def getColumnUICommands(self):
        if not self.__columnUICommands:
            self.__columnUICommands = self.createColumnUICommands()
        return self.__columnUICommands

    def createColumnUICommands(self):
        raise NotImplementedError

    def refresh(self, *args, **kwargs):
        if self and self.__initDone:
            super().refresh(*args, **kwargs)

    def init_columns(self):
        for column in self.columns():
            self.initColumn(column)
        self.__place_anchor_columns()

    def ordered_columns(self, columns):
        """The columns in the order the user gave them (the option
        columnorder, by name). A column it does not name, new in a later
        release, follows the one before it in the view's own order
        (docs/LIST_MANAGEMENT.md, Moving Columns)."""
        by_name = {column.name(): column for column in columns}
        ordered = [
            by_name[name]
            for name in dict.fromkeys(self.options.columnorder)
            if name in by_name
        ]
        for index, column in enumerate(columns):
            if column not in ordered:
                previous = columns[index - 1] if index else None
                place = 0 if previous is None else ordered.index(previous) + 1
                ordered.insert(place, column)
        return ordered

    def move_column(self, column, slot):
        """Move a shown column to slot, a place between the shown
        columns: 0 before the first, their count after the last; the
        order is saved."""
        if not self.widget.move_column(column, slot):
            return
        self._columns[:] = self.widget.all_columns()
        self.__visibleColumns = [
            each for each in self.columns() if each in self.__visibleColumns
        ]
        self.__place_anchor_columns()
        self.options.columnorder = [each.name() for each in self.columns()]
        self.options.columns = [each.name() for each in self.__visibleColumns]
        self.widget.RefreshAllItems(len(self.presentation()))

    def fill_column_name(self):
        """The column that takes the width left when the columns fit the
        window."""
        return "subject"

    def __place_anchor_columns(self):
        """The tree's hierarchy is drawn in the subject column and the
        width left goes to the fill column, wherever they are."""
        names = [column.name() for column in self.__visibleColumns]
        if self.fill_column_name() in names:
            self.widget.SetResizeColumn(names.index(self.fill_column_name()))
        if "subject" in names and hasattr(self.widget, "SetMainColumn"):
            self.widget.SetMainColumn(names.index("subject"))

    def initColumn(self, column):
        if column.name() in self.options.columnsalwaysvisible:
            show = True
        else:
            show = column.name() in self.options.columns
            self.widget.showColumn(column, show=show)
        if show:
            self.__visibleColumns.append(column)
            self.__start_observing(column.eventTypes())

    def showColumnByName(self, columnName, show=True):
        for column in self.hideable_columns():
            if columnName == column.name():
                is_visible_column = self.isVisibleColumn(column)
                if (show and not is_visible_column) or (
                    not show and is_visible_column
                ):
                    self.showColumn(column, show)
                break

    def showColumn(self, column, show=True, refresh=True):
        if show:
            self.__visibleColumns.append(column)
            # Make sure we keep the columns in the right order:
            self.__visibleColumns = [
                c for c in self.columns() if c in self.__visibleColumns
            ]
            self.__start_observing(column.eventTypes())
        else:
            self.__visibleColumns.remove(column)
            self.__stop_observing(column.eventTypes())
        self.widget.showColumn(column, show)
        self.__place_anchor_columns()
        self.options.columns = [
            column.name() for column in self.__visibleColumns
        ]
        if refresh:
            self.widget.RefreshAllItems(len(self.presentation()))

    def hide_column(self, visible_column_index):
        column = self.visibleColumns()[visible_column_index]
        self.showColumn(column, show=False)

    def columns(self):
        return self._columns

    def selectable_columns(self):
        return self._columns

    def isVisibleColumnByName(self, columnName):
        return columnName in [
            column.name() for column in self.__visibleColumns
        ]

    def isVisibleColumn(self, column):
        return column in self.__visibleColumns

    def visibleColumns(self):
        return self.__visibleColumns

    def hideable_columns(self):
        return [
            column
            for column in self._columns
            if column.name() not in self.options.columnsalwaysvisible
        ]

    def is_hideable_column(self, visible_column_index):
        column = self.visibleColumns()[visible_column_index]
        unhideable_columns = self.options.columnsalwaysvisible
        return column.name() not in unhideable_columns

    def getColumnWidth(self, column_name):
        column_widths = self.options.columnwidths
        default_width = (
            28
            if column_name == "ordering"
            else hypertreelist._DEFAULT_COL_WIDTH
        )  # pylint: disable=W0212
        return int(column_widths.get(column_name, default_width))

    def onResizeColumn(self, column, width):
        column_widths = self.options.columnwidths
        column_widths[column.name()] = int(width)
        self.options.columnwidths = column_widths

    def validate_drag(self, drop_item, drag_items, column_index):
        if (
            column_index == -1
            or self.visibleColumns()[column_index].name() != "ordering"
        ):
            return None  # Normal behavior

        # Ordering

        if not self.is_tree_viewer():
            return True

        # Tree mode. Only allow drag if all selected items are siblings.
        if len(set([item.parent() for item in drag_items])) >= 2:
            wx.GetTopLevelParent(self).AddBalloonTip(
                "treemanualordering",
                self,
                title=_("Reordering in tree mode"),
                get_rect=lambda: wx.Rect(0, 0, 28, 16),
                message=_(
                    """When in tree mode, manual ordering is only possible when all selected items are siblings."""
                ),
            )
            return False

        # If they are, only allow drag at the same level
        if drag_items[0].parent() != (
            None if drop_item is None else drop_item.parent()
        ):
            wx.GetTopLevelParent(self).AddBalloonTip(
                "treechildrenmanualordering",
                self,
                title=_("Reordering in tree mode"),
                get_rect=lambda: wx.Rect(0, 0, 28, 16),
                message=_(
                    """When in tree mode, you can only put objects at the same level (parent)."""
                ),
            )
            return False

        return True

    def getItemText(self, item, column=None):
        if column is None:  # The subject, wherever it is
            names = [each.name() for each in self.visibleColumns()]
            column = names.index("subject") if "subject" in names else 0
        column = self.visibleColumns()[column]
        return column.render(item)

    def getItemImages(self, item, column=0):
        column = self.visibleColumns()[column]
        return column.imageIndices(item)

    def hasColumnImages(self, column):
        return self.visibleColumns()[column].hasImages()

    def getItemMultiImages(self, item, column=0):
        column = self.visibleColumns()[column]
        return column.multiImageIndices(item)

    def hasColumnMultiImages(self, column):
        return self.visibleColumns()[column].hasMultiImages()

    def subjectImageIndices(self, item):
        # One icon, expanded or not
        icon_id = item.shown_icon_id()
        index = image_list_cache.get_index(icon_id) if icon_id else -1
        return {
            wx.TreeItemIcon_Normal: index,
            wx.TreeItemIcon_Expanded: index,
        }

    def __start_observing(self, event_types):
        # Columns observe with their own callback, so hiding one never
        # drops an event type the viewer observes for every row
        for event_type in event_types:
            self.registerObserver(
                self.__on_column_changed, eventType=event_type
            )

    def __stop_observing(self, event_types):
        # Keep observing the event types the visible columns still need
        visible_event_types = []
        for column in self.visibleColumns():
            visible_event_types.extend(column.eventTypes())
        for event_type in event_types:
            if event_type not in visible_event_types:
                self.removeObserver(
                    self.__on_column_changed, eventType=event_type
                )

    def __on_column_changed(self, event):
        self.on_attribute_changed(event)

    def renderCategories(self, item):
        return self.renderSubjectsOfRelatedItems(item, item.categories)

    def renderSubjectsOfRelatedItems(self, item, get_items):
        subjects = []
        own_items = get_items(recursive=False)
        if own_items:
            subjects.append(self.renderSubjects(own_items))
        is_list_viewer = not self.is_tree_viewer()  # pylint: disable=E1101
        if is_list_viewer or self.isItemCollapsed(item):
            child_items = [
                the_item
                for the_item in get_items(
                    recursive=True, upwards=is_list_viewer
                )
                if the_item not in own_items
            ]
            if child_items:
                subjects.append("(%s)" % self.renderSubjects(child_items))
        return " ".join(subjects)

    @staticmethod
    def renderSubjects(items):
        subjects = [item.subject(recursive=True) for item in items]
        return ", ".join(sorted(subjects))

    @staticmethod
    def renderCreationDateTime(item, human_readable=True):
        return render.dateTime(
            item.creationDateTime(), human_readable=human_readable
        )

    @staticmethod
    def renderModificationDateTime(item, human_readable=True):
        return render.dateTime(
            item.modificationDateTime(), human_readable=human_readable
        )

    def isItemCollapsed(self, item):
        # pylint: disable=E1101
        # pylint: disable=E1101
        return (
            not self.get_item_expanded(item)
            if self.is_tree_viewer() and item.children()
            else False
        )


class SortableViewerWithColumns(
    mixin.SortableViewerMixin, ViewerWithColumns
):  # pylint: disable=W0223
    def initColumn(self, column):
        super().initColumn(column)
        if self.isSortedBy(column.name()):
            self.widget.show_sort_column(column)
            self.show_sort_order()

    def setSortOrderAscending(self, *args, **kwargs):  # pylint: disable=W0221
        super().setSortOrderAscending(*args, **kwargs)
        self.show_sort_order()

    def sortBy(self, *args, **kwargs):  # pylint: disable=W0221
        super().sortBy(*args, **kwargs)
        self.show_sort_column()
        self.show_sort_order()

    def show_sort_column(self):
        for column in self.columns():
            if self.isSortedBy(column.name()):
                self.widget.show_sort_column(column)
                break

    def show_sort_order(self):
        self.widget.show_sort_order(
            image_list_cache.get_index(self.get_sort_order_image())
        )

    def get_sort_order_image(self):
        # Arrow points in direction of sort: down for A→Z/old→new, up for Z→A/new→old
        return (
            "nuvola_actions_go-down"
            if self.isSortOrderAscending()
            else "nuvola_actions_go-up"
        )
