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

"""
Appearance SSOT (Single Source of Truth) Architecture

WRITE (stored procedures):
  computeDerived(obj, field_type)   → computes and writes derived value/source via object setters
  computeEffective(obj, field_type) → computes and writes effective value/default/source via object setters

READ (object accessor methods - each returns single value):
  obj.derivedFgColor()              → reads derived foreground color value
  obj.derivedFgColorSource()        → reads derived foreground color source
  obj.effectiveFgColor()            → reads effective foreground color value
  obj.effectiveFgColorSource()      → reads effective foreground color source

UI Pattern:
  1. Subscribe to per-field SSOT change events (derivedXxxChanged, effectiveXxxChanged)
  2. Call object accessors when notified

Volatile Fields (not persisted):
  - Derived and effective values are Attribute fields in object.py
  - NOT in __getstate__, so after file load they are all None/""
  - ComputeStyles polling populates them within 1 second of app start

Field types: 'fgColor', 'bgColor', 'font', 'icon'
"""

from pubsub import pub

# =============================================================================
# Constants
# =============================================================================

SYSTEM_FG_COLOR = "SYS_COLOUR_WINDOWTEXT"
SYSTEM_BG_COLOR = "SYS_COLOUR_WINDOW"
SYSTEM_FONT = "SYS_DEFAULT_GUI_FONT"
SYSTEM_THEME_SOURCE = "System Theme"

FIELD_TYPES = ('fgColor', 'bgColor', 'font', 'icon')

FIELD_DEFAULTS = {
    'fgColor': SYSTEM_FG_COLOR,
    'bgColor': SYSTEM_BG_COLOR,
    'font': SYSTEM_FONT,
    'icon': "",
}

FIELD_NO_VALUE_SOURCE = {
    'fgColor': SYSTEM_THEME_SOURCE,
    'bgColor': SYSTEM_THEME_SOURCE,
    'font': SYSTEM_THEME_SOURCE,
    'icon': "N/A",
}

OVERRIDE_METHOD = {
    'fgColor': 'foregroundColor',
    'bgColor': 'backgroundColor',
    'font': 'font',
    'icon': 'icon',
}


# =============================================================================
# Per-field Event Types
# =============================================================================

def effectiveFgColorChangedEventType():
    return "pubsub.effective.fgColor"


def effectiveBgColorChangedEventType():
    return "pubsub.effective.bgColor"


def effectiveIconChangedEventType():
    return "pubsub.effective.icon"


def effectiveFontChangedEventType():
    return "pubsub.effective.font"


EFFECTIVE_EVENT_TYPES = {
    'fgColor': effectiveFgColorChangedEventType,
    'bgColor': effectiveBgColorChangedEventType,
    'icon': effectiveIconChangedEventType,
    'font': effectiveFontChangedEventType,
}


# =============================================================================
# Per-field Effective Setters
# =============================================================================

def setEffectiveFgColor(obj, value, default, source):
    obj.setEffectiveFgColor(value, default, source)


def setEffectiveBgColor(obj, value, default, source):
    obj.setEffectiveBgColor(value, default, source)


def setEffectiveIcon(obj, value, default, source):
    # Icon setter doesn't take default
    obj.setEffectiveIcon(value, source)


def setEffectiveFont(obj, value, default, source):
    obj.setEffectiveFont(value, default, source)


EFFECTIVE_SETTERS = {
    'fgColor': setEffectiveFgColor,
    'bgColor': setEffectiveBgColor,
    'icon': setEffectiveIcon,
    'font': setEffectiveFont,
}


# =============================================================================
# Stored Procedure: computeDerived
# =============================================================================

# Mapping of field types to effective getter method names
EFFECTIVE_GETTERS = {
    'fgColor': 'effectiveFgColor',
    'bgColor': 'effectiveBgColor',
    'icon': 'effectiveIcon',
    'font': 'effectiveFont',
}

# Mapping of field types to status getter method names (Task only)
STATUS_GETTERS = {
    'fgColor': 'statusFgColor',
    'bgColor': 'statusBgColor',
    'icon': 'statusIcon',
    'font': 'statusFont',
}

# Mapping of field types to derived setter method names
DERIVED_SETTERS = {
    'fgColor': 'setDerivedFgColor',
    'bgColor': 'setDerivedBgColor',
    'icon': 'setDerivedIcon',
    'font': 'setDerivedFont',
}


def _getObjectType(obj):
    class_name = obj.__class__.__name__
    if class_name == 'Task':
        return 'Task'
    elif class_name == 'Category':
        return 'Category'
    elif class_name == 'Note':
        return 'Note'
    return 'Attachment'


def _isSystemThemeValue(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.startswith("SYS_")
    return False


def computeDerived(object_ref, field_type):
    """Compute derived value from sources and write to SSOT.

    Sources by object type:
    - Category: parent.effectiveXxx()
    - Task: categories (sorted by stylePriority) → parent → status
    - Note: parent.effectiveXxx()
    - Attachment: (none - always empty)

    OUTPUTS: Calls object_ref.setDerivedXxx(value, source)
    """
    obj_type = _getObjectType(object_ref)
    effective_getter = EFFECTIVE_GETTERS[field_type]

    value = None
    source = FIELD_NO_VALUE_SOURCE[field_type]

    if obj_type == 'Task':
        # Task sources: categories → parent → status
        # Check categories first (sorted by stylePriority, higher = first)
        if hasattr(object_ref, 'categories'):
            categories = list(object_ref.categories())
            # Sort by stylePriority descending (higher priority first)
            categories.sort(key=lambda c: getattr(c, 'stylePriority', lambda: 0)(), reverse=True)
            for cat in categories:
                getter = getattr(cat, effective_getter, None)
                if getter:
                    cat_value = getter()
                    if cat_value and not _isSystemThemeValue(cat_value):
                        value = cat_value
                        source = f"[Category] {cat.subject()}"
                        break

        # Check parent task if no category value
        if value is None and object_ref.parent():
            parent = object_ref.parent()
            getter = getattr(parent, effective_getter, None)
            if getter:
                parent_value = getter()
                if parent_value and not _isSystemThemeValue(parent_value):
                    value = parent_value
                    source = f"[Task] {parent.subject()}"

        # Fall back to status
        if value is None:
            status_getter = STATUS_GETTERS.get(field_type)
            if status_getter and hasattr(object_ref, status_getter):
                getter = getattr(object_ref, status_getter)
                value = getter()
                if hasattr(object_ref, 'status'):
                    source = f"[Status] {object_ref.status()}"
                else:
                    source = "[Status]"

    elif obj_type in ('Category', 'Note'):
        # Category/Note sources: parent only
        if object_ref.parent():
            parent = object_ref.parent()
            getter = getattr(parent, effective_getter, None)
            if getter:
                parent_value = getter()
                if parent_value and not _isSystemThemeValue(parent_value):
                    value = parent_value
                    source = f"[{obj_type}] {parent.subject()}"

    # Attachment: no sources, value stays None

    # Write via object setter
    setter_name = DERIVED_SETTERS[field_type]
    setter = getattr(object_ref, setter_name, None)
    if setter:
        setter(value, source)



# =============================================================================
# Stored Procedure: computeEffective
# =============================================================================

# Mapping of field types to derived getter method names
DERIVED_VALUE_GETTERS = {
    'fgColor': 'derivedFgColor',
    'bgColor': 'derivedBgColor',
    'icon': 'derivedIcon',
    'font': 'derivedFont',
}

DERIVED_SOURCE_GETTERS = {
    'fgColor': 'derivedFgColorSource',
    'bgColor': 'derivedBgColorSource',
    'icon': 'derivedIconSource',
    'font': 'derivedFontSource',
}


def computeEffective(object_ref, field_type):
    """Compute effective from derived + override. Calls per-field setter.

    INPUTS:  derived value/source from object getters, override value
    OUTPUTS: calls object's setEffectiveXxx(value, default, source)
    """
    # Read derived values from object getters
    derived_value_getter = getattr(object_ref, DERIVED_VALUE_GETTERS[field_type], None)
    derived_source_getter = getattr(object_ref, DERIVED_SOURCE_GETTERS[field_type], None)

    derived_value = derived_value_getter() if derived_value_getter else None
    derived_source = (derived_source_getter() if derived_source_getter else None) or FIELD_NO_VALUE_SOURCE[field_type]

    override_method = getattr(object_ref, OVERRIDE_METHOD[field_type])
    override_value = override_method() if field_type == 'icon' else override_method(recursive=False)

    # Compute effective
    if override_value:
        effective_value = override_value
        effective_source = "Override"
    else:
        effective_value = derived_value
        effective_source = derived_source

    effective_default = FIELD_DEFAULTS[field_type]

    # Call per-field setter (now calls object's Attribute-based setter)
    setter = EFFECTIVE_SETTERS[field_type]
    setter(object_ref, effective_value, effective_default, effective_source)


# =============================================================================
# ComputeStyles - Per-Second Polling for SSOT Updates
# =============================================================================

class ComputeStyles:
    """Computes derived and effective styles for all objects every second.

    This polling approach catches ALL changes without needing explicit triggers:
    - Category changes (color, icon, font)
    - Parent changes
    - Status changes (from time passing)
    - Settings changes (theme, status colors)

    Processing order: Categories → Tasks → Notes → Attachments
    Simple iteration, no hierarchy sorting. Eventual consistency within 1-2 seconds.
    """

    def __init__(self, taskFile):
        """Initialize ComputeStyles.

        Args:
            taskFile: The task file to access categories, tasks, notes, attachments
        """
        self._taskFile = taskFile
        pub.subscribe(self._onSecond, 'timer.second')

    def _onSecond(self, timestamp):
        """Recompute derived and effective values for all objects."""
        if not self._taskFile:
            return

        # Process in order: categories, tasks, notes, attachments
        # Categories first so tasks can read their effective values
        for category in self._taskFile.categories():
            self._computeForObject(category)

        for task in self._taskFile.tasks():
            self._computeForObject(task)

        for note in self._taskFile.notes():
            self._computeForObject(note)

        # Attachments from tasks and notes
        for task in self._taskFile.tasks():
            if hasattr(task, 'attachments'):
                for attachment in task.attachments():
                    self._computeForObject(attachment)
        for note in self._taskFile.notes():
            if hasattr(note, 'attachments'):
                for attachment in note.attachments():
                    self._computeForObject(attachment)

    def _computeForObject(self, obj):
        """Per-object processing: status (tasks only) → derived → effective."""
        if hasattr(obj, 'computeStoredStatus'):
            obj.computeStoredStatus()
        for field_type in FIELD_TYPES:
            computeDerived(obj, field_type)
            computeEffective(obj, field_type)

    def shutdown(self):
        """Cleanup subscriptions."""
        pub.unsubscribe(self._onSecond, 'timer.second')
