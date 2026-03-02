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

import wx
from taskcoachlib import patterns, widgets, command, render
from taskcoachlib.i18n import _
from taskcoachlib.gui import uicommand, toolbar
from taskcoachlib.gui.icons import icon_library
from taskcoachlib.gui.icons import image_list_cache
from wx.lib.agw import hypertreelist
from pubsub import pub
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

    def __init__(self, parent, taskFile, settings, *args, **kwargs):
        patterns.Observer.__init__(self)
        super().__init__(parent, -1)
        self.parent = parent
        self.taskFile = taskFile
        self.settings = settings
        self.__settingsSection = kwargs.pop("settingsSection")
        self.__freezeCount = 0
        # Track items changed during bulk operations
        self.__pendingRefreshItems = set()
        # The how maniest of this viewer type are we? Used for settings
        self.__instanceNumber = kwargs.pop("instanceNumber")
        self.__use_separate_settings_section = kwargs.pop(
            "use_separate_settings_section", True
        )
        # Flag so that we don't notify observers while we're selecting all items
        self.__selectingAllItems = False
        # Popup menus we have to destroy before closing the viewer to prevent
        # memory leakage:
        self._popupMenus = []
        # What are we presenting:
        self.__presentation = self.createSorter(
            self.createFilter(self.domainObjectsToView())
        )
        # The widget used to present the presentation:
        self.widget = self.createWidget()
        self.widget.SetBackgroundColour(
            wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        )
        self.toolbar = toolbar.ToolBar(self, settings,
                                       (toolbar.TOOLBAR_ICON_SIZE,) * 2)
        self.initLayout()
        self.registerPresentationObservers()
        self.refresh()

        pub.subscribe(self.onBeginIO, "taskfile.aboutToRead")
        pub.subscribe(self.onBeginIO, "taskfile.aboutToClear")
        pub.subscribe(self.onBeginIO, "taskfile.aboutToSave")
        pub.subscribe(self.onEndIO, "taskfile.justRead")
        pub.subscribe(self.onEndIO, "taskfile.justCleared")
        pub.subscribe(self.onEndIO, "taskfile.justSaved")
        # Subscribe to bulk operation signals to freeze/thaw during batch updates
        pub.subscribe(self.onBeginBulkOperation, "command.aboutToBulkModify")
        pub.subscribe(self.onEndBulkOperation, "command.justBulkModified")

        wx.CallAfter(self.__DisplayBalloon)

    def __DisplayBalloon(self):
        # Guard against deleted C++ object - can happen when wx.CallAfter
        # callback executes after window destruction (e.g., closing nested dialogs)
        try:
            if not self or self.IsBeingDeleted():
                return
        except RuntimeError:
            # wrapped C/C++ object has been deleted
            return
        # AuiFloatingFrame is instantiated from framemanager, we can't derive it from BalloonTipManager
        if self.toolbar.IsShownOnScreen() and hasattr(
            wx.GetTopLevelParent(self), "AddBalloonTip"
        ):
            wx.GetTopLevelParent(self).AddBalloonTip(
                self.settings,
                "customizabletoolbars",
                self.toolbar,
                title=_("Toolbars are customizable"),
                getRect=lambda: self.toolbar.GetToolRect(
                    self.toolbar.getToolIdByCommand("EditToolBarPerspective")
                ),
                message=_(
                    """Click on the gear icon on the right to add buttons and rearrange them."""
                ),
            )

    def onBeginIO(self, taskFile):
        self.__freezeCount += 1
        self.__presentation.freeze()

    def onEndIO(self, taskFile):
        self.__freezeCount -= 1
        self.__presentation.thaw()
        if self.__freezeCount == 0:
            self.refresh()

    def onBeginBulkOperation(self):
        """Freeze viewer and presentation to batch updates during bulk operations."""
        self.__freezeCount += 1
        self.__presentation.freeze()

    def onEndBulkOperation(self):
        """Thaw viewer and presentation after bulk operation, refresh only changed items."""
        self.__freezeCount -= 1
        self.__presentation.thaw()
        if self.__freezeCount == 0 and self.__pendingRefreshItems:
            # Refresh only items that changed during the bulk operation
            items = [item for item in self.__pendingRefreshItems
                     if item in self.presentation()]
            self.__pendingRefreshItems.clear()
            if items:
                self.widget.RefreshItems(*items)

    def activate(self):
        pass

    def _bindActivationEvents(self, window):
        """Bind click events to activate this viewer's pane.

        This ensures clicking anywhere on the viewer (toolbar, title bar area,
        empty space) will activate the pane. We skip text controls to avoid
        interfering with text input focus.
        """
        # Skip text input controls - they handle their own focus
        if isinstance(window, (wx.TextCtrl, wx.SearchCtrl, wx.ComboBox)):
            return
        window.Bind(wx.EVT_LEFT_DOWN, self._onViewerClick)
        # Recursively bind to children, but skip the main widget (tree/list)
        for child in window.GetChildren():
            if child != self.widget:
                self._bindActivationEvents(child)

    def _onViewerClick(self, event):
        """Handle clicks on the viewer to activate its pane."""
        wx.PostEvent(self, wx.ChildFocusEvent(self))
        self.SetFocus()  # Clear focus from other controls (e.g., search box)
        event.Skip()

    def domainObjectsToView(self):
        """Return the domain objects that this viewer should display. For
        global viewers this will be part of the task file,
        e.g. self.taskFile.tasks(), for local viewers this will be a list
        of objects passed to the viewer constructor."""
        raise NotImplementedError

    def registerPresentationObservers(self):
        self.removeObserver(self.onPresentationChanged)
        self.registerObserver(
            self.onPresentationChanged,
            eventType=self.presentation().addItemEventType(),
            eventSource=self.presentation(),
        )
        self.registerObserver(
            self.onPresentationChanged,
            eventType=self.presentation().removeItemEventType(),
            eventSource=self.presentation(),
        )
        self.registerObserver(self.onNewItem, eventType="newitem")

    def detach(self):
        """Should be called by viewer.container before closing the viewer"""
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
            if hasattr(observer, 'removeInstance'):
                observer.removeInstance()

        for popupMenu in self._popupMenus:
            try:
                popupMenu.clearMenu()
                popupMenu.Destroy()
            except RuntimeError:
                log_step("detach: popup menu already dead %x" %
                         id(popupMenu), prefix="DEAD-OBJ")

        pub.unsubscribe(self.onBeginIO, "taskfile.aboutToRead")
        pub.unsubscribe(self.onBeginIO, "taskfile.aboutToClear")
        pub.unsubscribe(self.onBeginIO, "taskfile.aboutToSave")
        pub.unsubscribe(self.onEndIO, "taskfile.justRead")
        pub.unsubscribe(self.onEndIO, "taskfile.justCleared")
        pub.unsubscribe(self.onEndIO, "taskfile.justSaved")
        pub.unsubscribe(self.onBeginBulkOperation, "command.aboutToBulkModify")
        pub.unsubscribe(self.onEndBulkOperation, "command.justBulkModified")

        self.presentation().detach()
        self.toolbar.detach()

    def viewerStatusEventType(self):
        return "viewer%s.status" % id(self)

    def selection_changed_event_type(self):
        return "viewer%s.selection" % id(self)

    def view_settings_changed_event_type(self):
        return "viewer%s.view_settings" % id(self)

    @property
    def has_selection(self):
        w = self.widget
        if hasattr(w, 'has_selection'):
            return w.has_selection
        return bool(w.curselection())

    @property
    def has_single_selection(self):
        w = self.widget
        if hasattr(w, 'has_single_selection'):
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

    def sendViewerStatusEvent(self):
        pub.sendMessage(self.viewerStatusEventType(), viewer=self)

    def statusMessages(self):
        return "", ""

    def title(self):
        return (
            self.settings.get(self.settingsSection(), "title")
            or self.defaultTitle
        )

    def setTitle(self, title):
        titleToSaveInSettings = "" if title == self.defaultTitle else title
        self.settings.set(
            self.settingsSection(), "title", titleToSaveInSettings
        )
        self.parent.setPaneTitle(self, title)
        self.parent.manager.Update()

    def initLayout(self):
        self._sizer = wx.BoxSizer(wx.VERTICAL)  # pylint: disable=W0201
        self._sizer.Add(self.toolbar, flag=wx.EXPAND)
        self._sizer.Add(self.widget, proportion=1, flag=wx.EXPAND)
        self.SetSizer(self._sizer)  # Changed from SetSizerAndFit to prevent locking MinSize
        # Prevent GetEffectiveMinSize() from returning child's BestSize
        self.SetMinSize((100, 50))
        # Bind click events to activate pane when clicking on toolbar/empty space
        self._bindActivationEvents(self)

    def createWidget(self, *args):
        raise NotImplementedError

    def createImageList(self):
        return image_list_cache.image_list

    def getWidget(self):
        return self.widget

    def SetFocus(self, *args, **kwargs):
        try:
            self.widget.SetFocus(*args, **kwargs)
        except RuntimeError as e:
            log_step("SetFocus on dead widget %s: %s" %
                     (self.__class__.__name__, e), prefix="DEAD-OBJ")

    def createSorter(self, collection):
        """This method can be overridden to decorate the presentation with a
        sorter."""
        return collection

    def createFilter(self, collection):
        """This method can be overridden to decorate the presentation with a
        filter."""
        return collection

    def onAttributeChanged(self, newValue, sender):  # pylint: disable=W0613
        if self:
            if self.__freezeCount:
                # During bulk operation, collect items to refresh later
                self.__pendingRefreshItems.add(sender)
            else:
                self.refreshItems(sender)

    def onAttributeChanged_Deprecated(self, event):
        if self.__freezeCount:
            # During bulk operation, collect items to refresh later
            self.__pendingRefreshItems.update(event.sources())
        else:
            self.refreshItems(*event.sources())

    def onNewItem(self, event):
        self.select(
            [
                item
                for item in list(event.values())
                if item in self.presentation()
            ]
        )

    def onPresentationChanged(self, event):  # pylint: disable=W0613
        """Whenever our presentation is changed (items added, items removed)
        the viewer refreshes itself."""

        def itemsRemoved():
            return event.type() == self.presentation().removeItemEventType()

        # BEFORE refresh - capture selection info while widget has old state
        selectionInfo = None
        if itemsRemoved():
            selectionInfo = self._captureSelectionInfo()

        self.refresh()

        # AFTER refresh - select next if selection became empty
        if itemsRemoved() and hasattr(self.widget, 'curselection') and not self.widget.curselection() and selectionInfo:
            self.selectNextItemsAfterRemoval(selectionInfo)
        # Center on selected item — tree views use scrollToSelectionCentered,
        # list views use ensureSelectionVisible (native wx scrollbar management)
        if hasattr(self.widget, 'scrollToSelectionCentered'):
            self.widget.scrollToSelectionCentered()
        elif hasattr(self.widget, 'ensureSelectionVisible'):
            self.widget.ensureSelectionVisible()
        self.sendViewerStatusEvent()

    def _captureSelectionInfo(self):
        """Capture selection info before refresh. Override in subclasses."""
        return None

    def selectNextItemsAfterRemoval(self, selectionInfo):
        """Select the next item after items were removed.

        Args:
            selectionInfo: Selection state captured before refresh (parent + index)
        """
        raise NotImplementedError

    def onSelect(self, event=None):  # pylint: disable=W0613
        """The selection of items in the widget has been changed. Notify
        our observers."""

        try:
            if self.IsBeingDeleted() or self.__selectingAllItems:
                # Some widgets change the selection and send selection events when
                # deleting all items as part of the Destroy process. Ignore.
                return

            # Fire selection signal — toolbar buttons subscribe via _SelectionSync
            patterns.Event(
                self.selection_changed_event_type(), self
            ).send()

            # Fire status event - StatusBar has its own 500ms debounce
            # No need to query selection here; status bar queries fresh when displaying
            wx.CallAfter(self.sendViewerStatusEvent)
        except RuntimeError as e:
            log_step("onSelect on dead viewer %s: %s" %
                     (self.__class__.__name__, e), prefix="DEAD-OBJ")

    def updateSelection(self, sendViewerStatusEvent=True):
        """Legacy method - kept for subclass compatibility.

        With SSOT selection (curselection() queries widget fresh),
        there's no cache to update. Just fires status event if requested.
        """
        if sendViewerStatusEvent:
            self.sendViewerStatusEvent()

    def freeze(self):
        self.widget.Freeze()

    def thaw(self):
        self.widget.Thaw()

    def refresh(self):
        if self and not self.__freezeCount:
            self.widget.RefreshAllItems(len(self.presentation()))

    def refreshItems(self, *items):
        if not self.__freezeCount:
            items = [item for item in items if item in self.presentation()]
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
        # Use CallAfter to make sure we start processing selection events
        # after all selection events have been fired (and ignored):
        wx.CallAfter(self.endOfSelectAll)

    def endOfSelectAll(self):
        # Guard against deleted C++ object - can happen when wx.CallAfter
        # callback executes after window destruction (e.g., closing nested dialogs)
        try:
            if not self or self.IsBeingDeleted():
                return
        except RuntimeError:
            # wrapped C/C++ object has been deleted
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

    def setPresentation(self, presentation):
        """Change the presentation of the viewer."""
        self.__presentation = presentation

    def widgetCreationKeywordArguments(self):
        return {}

    def isViewerContainer(self):
        return False

    def isShowingTasks(self):
        return False

    def isShowingEffort(self):
        return False

    def isShowingCategories(self):
        return False

    def isShowingNotes(self):
        return False

    def isShowingAttachments(self):
        return False

    def visibleColumns(self):
        return [widgets.Column("subject", _("Subject"))]

    def bitmap(self):
        """Return the bitmap that represents this viewer. Used for the
        'Viewer->New viewer' menu item, for example."""
        return self.defaultBitmap  # Class attribute of concrete viewers

    def settingsSection(self):
        """Return the settings section of this viewer."""
        section = self.__settingsSection
        if self.__use_separate_settings_section and self.__instanceNumber > 0:
            # We're not the first viewer of our class, so we need a different
            # settings section than the default one.
            section += str(self.__instanceNumber)
            if not self.settings.has_section(section):
                # Our section does not exist yet. Create it and copy the
                # settings from the previous section as starting point. We're
                # copying from the previous section instead of the default
                # section so that when the user closes a viewer and then opens
                # a new one, the settings of that closed viewer are reused.
                self.settings.add_section(
                    section, copyFromSection=self.previousSettingsSection()
                )
        return section

    def previousSettingsSection(self):
        """Return the settings section of the previous viewer of this
        class."""
        previousSectionNumber = self.__instanceNumber - 1
        while previousSectionNumber > 0:
            previousSection = self.__settingsSection + str(
                previousSectionNumber
            )
            if self.settings.has_section(previousSection):
                return previousSection
            previousSectionNumber -= 1
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

    def isFilterable(self):
        return False

    def getFilterUICommands(self):
        return []

    def supportsRounding(self):
        return False

    def getRoundingUICommands(self):
        return []

    def createToolBarUICommands(self):
        """UI commands to put on the toolbar of this viewer."""
        table = wx.AcceleratorTable(
            [
                (wx.ACCEL_CMD, ord("X"), wx.ID_CUT),
                (wx.ACCEL_CMD, ord("C"), wx.ID_COPY),
                (wx.ACCEL_CMD, ord("V"), wx.ID_PASTE),
                (wx.ACCEL_NORMAL, wx.WXK_RETURN, wx.ID_EDIT),
                (wx.ACCEL_CTRL, wx.WXK_DELETE, wx.ID_DELETE),
            ]
        )
        self.SetAcceleratorTable(table)

        clipboardToolBarUICommands = self.createClipboardToolBarUICommands()
        creationToolBarUICommands = self.createCreationToolBarUICommands()
        editToolBarUICommands = self.createEditToolBarUICommands()
        actionToolBarUICommands = self.createActionToolBarUICommands()
        modeToolBarUICommands = self.createModeToolBarUICommands()

        def separator(uiCommands, *otherUICommands):
            return (uicommand.Separator(),) if (uiCommands and any(otherUICommands)) else ()

        clipboardSeparator = separator(
            clipboardToolBarUICommands,
            creationToolBarUICommands,
            editToolBarUICommands,
            actionToolBarUICommands,
            modeToolBarUICommands,
        )
        creationSeparator = separator(
            creationToolBarUICommands,
            editToolBarUICommands,
            actionToolBarUICommands,
            modeToolBarUICommands,
        )
        editSeparator = separator(
            editToolBarUICommands,
            actionToolBarUICommands,
            modeToolBarUICommands,
        )
        actionSeparator = separator(
            actionToolBarUICommands, modeToolBarUICommands
        )

        return (
            clipboardToolBarUICommands
            + clipboardSeparator
            + creationToolBarUICommands
            + creationSeparator
            + editToolBarUICommands
            + editSeparator
            + actionToolBarUICommands
            + actionSeparator
            + modeToolBarUICommands
        )

    def getToolBarPerspective(self):
        return self.settings.get(self.settingsSection(), "toolbarperspective")

    def saveToolBarPerspective(self, perspective):
        self.settings.set(
            self.settingsSection(), "toolbarperspective", perspective
        )

    def createClipboardToolBarUICommands(self):
        """UI commands for manipulating the clipboard (cut, copy, paste)."""
        cutCommand = uicommand.EditCut(viewer=self)
        copyCommand = uicommand.EditCopy(viewer=self)
        pasteCommand = uicommand.EditPaste(viewer=self)
        cutCommand.bind(self, wx.ID_CUT)
        copyCommand.bind(self, wx.ID_COPY)
        pasteCommand.bind(self, wx.ID_PASTE)
        return cutCommand, copyCommand, pasteCommand

    def createCreationToolBarUICommands(self):
        """UI commands for creating new items."""
        return ()

    def createEditToolBarUICommands(self):
        """UI commands for editing items."""
        editCommand = uicommand.Edit(viewer=self)
        self.deleteUICommand = uicommand.Delete(
            viewer=self
        )  # For unittests pylint: disable=W0201
        editCommand.bind(self, wx.ID_EDIT)
        self.deleteUICommand.bind(self, wx.ID_DELETE)
        return editCommand, self.deleteUICommand

    def createActionToolBarUICommands(self):
        """UI commands for actions."""
        return ()

    def createModeToolBarUICommands(self):
        """UI commands for mode switches (e.g. list versus tree mode)."""
        return ()

    def newItemDialog(self, *args, **kwargs):
        icon_id = kwargs.pop("icon_id")
        newItemCommand = self.newItemCommand(*args, **kwargs)
        newItemCommand.do()
        return self.editItemDialog(
            newItemCommand.items, icon_id, items_are_new=True
        )

    def newSubItemDialog(self, icon_id):
        parents = self.curselection()
        newSubItemCommand = self.newSubItemCommand()
        newSubItemCommand.do()
        # Expand parent notes so the newly created subnotes are visible
        for parent in parents:
            parent.expand(True, context=self.settingsSection())
        return self.editItemDialog(
            newSubItemCommand.items, icon_id, items_are_new=True
        )

    def editItemDialog(
        self, items, icon_id, columnName="", items_are_new=False
    ):
        parent = wx.GetTopLevelParent(self)
        # If the viewer is inside an Editor dialog (e.g. EffortViewer inside
        # TaskEditor), parent to main window instead. Otherwise Destroy() on
        # the parent editor cascades to this editor without EVT_CLOSE, leaving
        # dangling observers/subscriptions and causing C++ segfaults.
        if isinstance(parent, wx.Dialog):
            parent = wx.GetApp().TopWindow
        EditorClass = self.itemEditorClass()
        return EditorClass(
            parent,
            items,
            self.settings,
            self.presentation(),
            self.taskFile,
            icon_id=icon_id,
            columnName=columnName,
            items_are_new=items_are_new,
        )

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
        return self.pasteItemCommandClass()(
            self.presentation()
        )

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

    def visibleItems(self):
        """Iterate over the items in the presentation."""
        for item in self.presentation():
            yield item

    def getItemWithIndex(self, index):
        try:
            return self.presentation()[index]
        except IndexError:
            return None

    def getIndexOfItem(self, item):
        return self.presentation().index(item)

    def selectNextItemsAfterRemoval(self, selectionInfo):
        pass  # Done automatically by list controls


class TreeViewer(Viewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.onItemExpanded)
        self.widget.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.onItemCollapsed)

    def onItemExpanded(self, event):
        self.__handleExpandedOrCollapsedItem(event, expanded=True)

    def onItemCollapsed(self, event):
        self.__handleExpandedOrCollapsedItem(event, expanded=False)

    def __handleExpandedOrCollapsedItem(self, event, expanded):
        event.Skip()
        treeItem = event.GetItem()
        # If we get an expanded or collapsed event for the root item, ignore it
        if treeItem == self.widget.GetRootItem():
            return
        item = self.widget.GetItemPyData(treeItem)
        item.expand(expanded, context=self.settingsSection())

    def expandAll(self):
        """Expand all items, recursively."""
        # Since the widget does not send EVT_TREE_ITEM_EXPANDED when expanding
        # all items, we have to do the bookkeeping ourselves:
        for item in self.visibleItems():
            item.expand(True, context=self.settingsSection(), notify=False)
        self.refresh()

    def collapseAll(self):
        """Collapse all items, recursively."""
        # Since the widget does not send EVT_TREE_ITEM_COLLAPSED when collapsing
        # all items, we have to do the bookkeeping ourselves:
        for item in self.visibleItems():
            item.expand(False, context=self.settingsSection(), notify=False)
        self.refresh()


    def createModeToolBarUICommands(self):
        return super().createModeToolBarUICommands() + (
            uicommand.ViewExpandAll(viewer=self),
            uicommand.ViewCollapseAll(viewer=self),
        )

    def is_tree_viewer(self):
        return True

    def select(self, items):
        for item in items:
            self.__expandItemRecursively(item)
        self.refresh()
        super().select(items)

    def __expandItemRecursively(self, item):
        parent = self.getItemParent(item)
        if parent:
            parent.expand(True, context=self.settingsSection(), notify=False)
            self.__expandItemRecursively(parent)

    def _captureSelectionInfo(self):
        """Capture selection position before refresh."""
        if not hasattr(self.widget, 'curselection'):
            return None
        curselection = self.widget.curselection()
        if curselection and curselection[0] is not None:
            selectedItem = curselection[0]
            parent = self.getItemParent(selectedItem)
            siblings = self.children(parent)
            index = siblings.index(selectedItem) if selectedItem in siblings else 0
            return {'parent': parent, 'index': index}
        return None

    def selectNextItemsAfterRemoval(self, selectionInfo):
        """Select next item using position captured before refresh."""
        if not selectionInfo:
            return
        parent = selectionInfo['parent']
        index = selectionInfo['index']
        # Parent might have been deleted too - check if still in presentation
        if parent is not None and parent not in self.presentation():
            parent = None
        siblings = self.children(parent)
        newSelection = (
            siblings[min(len(siblings) - 1, index)]
            if siblings
            else parent
        )
        if newSelection:
            self.select([newSelection])

    def visibleItems(self):
        """Iterate over the items in the presentation."""

        def yieldItemsAndChildren(items):
            sortedItems = [
                item for item in self.presentation() if item in items
            ]
            for item in sortedItems:
                yield item
                children = self.children(item)
                if children:
                    for child in yieldItemsAndChildren(children):
                        yield child

        for item in yieldItemsAndChildren(self.getRootItems()):
            yield item

    def getRootItems(self):
        """Allow for overriding what the rootItems are."""
        return self.presentation().rootItems()

    def getItemParent(self, item):
        """Allow for overriding what the parent of an item is."""
        return item.parent() if item is not None else None

    def getItemExpanded(self, item):
        return item.isExpanded(context=self.settingsSection())

    def children(self, parent=None):
        if parent:
            children = parent.children()
            if children:
                return [
                    child for child in self.presentation() if child in children
                ]
            else:
                return []
        else:
            return self.getRootItems()

    def getItemText(self, item):
        return item.subject()


class ViewerWithColumns(Viewer):  # pylint: disable=W0223
    def __init__(self, *args, **kwargs):
        self.__initDone = False
        self._columns = []
        self.__visibleColumns = []
        self.__columnUICommands = []
        super().__init__(*args, **kwargs)
        self.initColumns()
        self.__initDone = True
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

    def initColumns(self):
        for column in self.columns():
            self.initColumn(column)
        if self.hasOrderingColumn():
            self.widget.SetResizeColumn(1)
            self.widget.SetMainColumn(1)

    def initColumn(self, column):
        if column.name() in self.settings.getlist(
            self.settingsSection(), "columnsalwaysvisible"
        ):
            show = True
        else:
            show = column.name() in self.settings.getlist(
                self.settingsSection(), "columns"
            )
            self.widget.showColumn(column, show=show)
        if show:
            self.__visibleColumns.append(column)
            self.__startObserving(column.eventTypes())

    def showColumnByName(self, columnName, show=True):
        for column in self.hideableColumns():
            if columnName == column.name():
                isVisibleColumn = self.isVisibleColumn(column)
                if (show and not isVisibleColumn) or (
                    not show and isVisibleColumn
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
            self.__startObserving(column.eventTypes())
        else:
            self.__visibleColumns.remove(column)
            self.__stopObserving(column.eventTypes())
        self.widget.showColumn(column, show)
        # Set main column AFTER inserting/removing the ordering column
        if column.name() == "ordering":
            self.widget.SetResizeColumn(1 if show else 0)
            self.widget.SetMainColumn(1 if show else 0)
        self.settings.set(
            self.settingsSection(),
            "columns",
            str([column.name() for column in self.__visibleColumns]),
        )
        if refresh:
            self.widget.RefreshAllItems(len(self.presentation()))

    def hideColumn(self, visibleColumnIndex):
        column = self.visibleColumns()[visibleColumnIndex]
        self.showColumn(column, show=False)

    def columns(self):
        return self._columns

    def selectableColumns(self):
        return self._columns

    def isVisibleColumnByName(self, columnName):
        return columnName in [
            column.name() for column in self.__visibleColumns
        ]

    def isVisibleColumn(self, column):
        return column in self.__visibleColumns

    def visibleColumns(self):
        return self.__visibleColumns

    def hideableColumns(self):
        return [
            column
            for column in self._columns
            if column.name()
            not in self.settings.getlist(
                self.settingsSection(), "columnsalwaysvisible"
            )
        ]

    def isHideableColumn(self, visibleColumnIndex):
        column = self.visibleColumns()[visibleColumnIndex]
        unhideableColumns = self.settings.getlist(
            self.settingsSection(), "columnsalwaysvisible"
        )
        return column.name() not in unhideableColumns

    def getColumnWidth(self, column_name):
        column_widths = self.settings.getdict(
            self.settingsSection(), "columnwidths"
        )
        default_width = (
            28
            if column_name == "ordering"
            else hypertreelist._DEFAULT_COL_WIDTH
        )  # pylint: disable=W0212
        return int(column_widths.get(column_name, default_width))

    def onResizeColumn(self, column, width):
        column_widths = self.settings.getdict(
            self.settingsSection(), "columnwidths"
        )
        column_widths[column.name()] = int(width)
        self.settings.setdict(
            self.settingsSection(), "columnwidths", column_widths
        )

    def validateDrag(self, dropItem, dragItems, columnIndex):
        if (
            columnIndex == -1
            or self.visibleColumns()[columnIndex].name() != "ordering"
        ):
            return None  # Normal behavior

        # Ordering

        if not self.is_tree_viewer():
            return True

        # Tree mode. Only allow drag if all selected items are siblings.
        if len(set([item.parent() for item in dragItems])) >= 2:
            wx.GetTopLevelParent(self).AddBalloonTip(
                self.settings,
                "treemanualordering",
                self,
                title=_("Reordering in tree mode"),
                getRect=lambda: wx.Rect(0, 0, 28, 16),
                message=_(
                    """When in tree mode, manual ordering is only possible when all selected items are siblings."""
                ),
            )
            return False

        # If they are, only allow drag at the same level
        if dragItems[0].parent() != (
            None if dropItem is None else dropItem.parent()
        ):
            wx.GetTopLevelParent(self).AddBalloonTip(
                self.settings,
                "treechildrenmanualordering",
                self,
                title=_("Reordering in tree mode"),
                getRect=lambda: wx.Rect(0, 0, 28, 16),
                message=_(
                    """When in tree mode, you can only put objects at the same level (parent)."""
                ),
            )
            return False

        return True

    def getItemText(self, item, column=None):
        if column is None:
            column = 1 if self.hasOrderingColumn() else 0
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
        normal_icon_id = item.icon_id(recursive=True)
        selected_icon_id = item.selected_icon_id(recursive=True) or normal_icon_id
        normalImageIndex = image_list_cache.get_index(normal_icon_id) if normal_icon_id else -1
        selectedImageIndex = (
            image_list_cache.get_index(selected_icon_id) if selected_icon_id else -1
        )
        return {
            wx.TreeItemIcon_Normal: normalImageIndex,
            wx.TreeItemIcon_Expanded: selectedImageIndex,
        }

    def __startObserving(self, eventTypes):
        for eventType in eventTypes:
            if eventType.startswith("pubsub"):
                pub.subscribe(self.onAttributeChanged, eventType)
            else:
                self.registerObserver(
                    self.onAttributeChanged_Deprecated, eventType=eventType
                )

    def __stopObserving(self, eventTypes):
        # Collect the event types that the currently visible columns are
        # interested in and make sure we don't stop observing those event types.
        eventTypesOfVisibleColumns = []
        for column in self.visibleColumns():
            eventTypesOfVisibleColumns.extend(column.eventTypes())
        for eventType in eventTypes:
            if eventType not in eventTypesOfVisibleColumns:
                if eventType.startswith("pubsub"):
                    pub.unsubscribe(self.onAttributeChanged, eventType)
                else:
                    self.removeObserver(
                        self.onAttributeChanged_Deprecated, eventType=eventType
                    )

    def renderCategories(self, item):
        return self.renderSubjectsOfRelatedItems(item, item.categories)

    def renderSubjectsOfRelatedItems(self, item, getItems):
        subjects = []
        ownItems = getItems(recursive=False)
        if ownItems:
            subjects.append(self.renderSubjects(ownItems))
        is_list_viewer = not self.is_tree_viewer()  # pylint: disable=E1101
        if is_list_viewer or self.isItemCollapsed(item):
            childItems = [
                theItem
                for theItem in getItems(recursive=True, upwards=is_list_viewer)
                if theItem not in ownItems
            ]
            if childItems:
                subjects.append("(%s)" % self.renderSubjects(childItems))
        return " ".join(subjects)

    @staticmethod
    def renderSubjects(items):
        subjects = [item.subject(recursive=True) for item in items]
        return ", ".join(sorted(subjects))

    @staticmethod
    def renderCreationDateTime(item, humanReadable=True):
        return render.dateTime(
            item.creationDateTime(), humanReadable=humanReadable
        )

    @staticmethod
    def renderModificationDateTime(item, humanReadable=True):
        return render.dateTime(
            item.modificationDateTime(), humanReadable=humanReadable
        )

    def isItemCollapsed(self, item):
        # pylint: disable=E1101
        # pylint: disable=E1101
        return (
            not self.getItemExpanded(item)
            if self.is_tree_viewer() and item.children()
            else False
        )


class SortableViewerWithColumns(
    mixin.SortableViewerMixin, ViewerWithColumns
):  # pylint: disable=W0223
    def initColumn(self, column):
        super().initColumn(column)
        if self.isSortedBy(column.name()):
            self.widget.showSortColumn(column)
            self.showSortOrder()

    def setSortOrderAscending(self, *args, **kwargs):  # pylint: disable=W0221
        super().setSortOrderAscending(*args, **kwargs)
        self.showSortOrder()

    def sortBy(self, *args, **kwargs):  # pylint: disable=W0221
        super().sortBy(*args, **kwargs)
        self.showSortColumn()
        self.showSortOrder()

    def showSortColumn(self):
        for column in self.columns():
            if self.isSortedBy(column.name()):
                self.widget.showSortColumn(column)
                break

    def showSortOrder(self):
        self.widget.showSortOrder(image_list_cache.get_index(self.getSortOrderImage()))

    def getSortOrderImage(self):
        # Arrow points in direction of sort: down for A→Z/old→new, up for Z→A/new→old
        return (
            "nuvola_actions_go-down"
            if self.isSortOrderAscending()
            else "nuvola_actions_go-up"
        )
