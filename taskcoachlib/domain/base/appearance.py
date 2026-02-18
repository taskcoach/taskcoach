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
    'icon': 'icon_id',
}


# =============================================================================
# Per-field Event Types
# =============================================================================

def effectiveFgColorChangedEventType():
    return "effective.fgColor"


def effectiveBgColorChangedEventType():
    return "effective.bgColor"


def effectiveIconChangedEventType():
    return "effective.icon"


def effectiveFontChangedEventType():
    return "effective.font"


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


# Default icons for types without status-based icons (Task gets icons from status)
TYPE_DEFAULT_ICONS = {
    'Category': 'nuvola_mimetypes_inode-directory',
    'Note': 'nuvola_apps_knotes',
    'Attachment': 'nuvola_status_mail-attachment',
}


def _isBeingTracked(obj):
    return hasattr(obj, 'isBeingTracked') and obj.isBeingTracked()


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


def _getFromCategories(object_ref, effective_getter):
    """Get a style value from the object's categories, sorted by stylePriority.

    Returns (value, source) from the highest-priority category that has
    a non-system-theme value, or (None, None) if no category provides one.
    """
    if not hasattr(object_ref, 'categories'):
        return None, None
    categories = list(object_ref.categories())
    categories.sort(
        key=lambda c: getattr(c, 'stylePriority', lambda: 0)(),
        reverse=True,
    )
    for cat in categories:
        getter = getattr(cat, effective_getter, None)
        if getter:
            cat_value = getter()
            if cat_value and not _isSystemThemeValue(cat_value):
                return cat_value, f"[Category] {cat.subject()}"
    return None, None


def _getFromParent(object_ref, obj_type, effective_getter):
    """Get a style value from the object's parent.

    Returns (value, source) or (None, None).
    """
    if not object_ref.parent():
        return None, None
    parent = object_ref.parent()
    getter = getattr(parent, effective_getter, None)
    if getter:
        parent_value = getter()
        if parent_value and not _isSystemThemeValue(parent_value):
            return parent_value, f"[{obj_type}] {parent.subject()}"
    return None, None


def computeDerived(object_ref, field_type):
    """Compute derived value from sources and write to SSOT.

    Sources by object type:
    - Task: categories (sorted by stylePriority) → parent → status
    - Note: categories (sorted by stylePriority) → parent
    - Category: parent only
    - Attachment: (none - always uses default icon)

    OUTPUTS: Calls object_ref.setDerivedXxx(value, source)
    """
    obj_type = _getObjectType(object_ref)
    effective_getter = EFFECTIVE_GETTERS[field_type]

    value = None
    source = FIELD_NO_VALUE_SOURCE[field_type]

    if obj_type == 'Task':
        # Tracking icon: highest priority for icon field
        if field_type == 'icon' and _isBeingTracked(object_ref):
            value = "nuvola_apps_clock"
            source = "[Tracking]"

        # Task sources: categories → parent → status
        if value is None:
            value, src = _getFromCategories(object_ref, effective_getter)
            if src:
                source = src

        if value is None:
            value, src = _getFromParent(object_ref, obj_type, effective_getter)
            if src:
                source = src

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

    elif obj_type == 'Note':
        # Note sources: categories → parent
        value, src = _getFromCategories(object_ref, effective_getter)
        if src:
            source = src

        if value is None:
            value, src = _getFromParent(object_ref, obj_type, effective_getter)
            if src:
                source = src

    elif obj_type == 'Category':
        # Category sources: parent only
        value, src = _getFromParent(object_ref, obj_type, effective_getter)
        if src:
            source = src

    # Attachment: no sources, value stays None

    # Default icon fallback for types without status (Category, Note, Attachment)
    if field_type == 'icon' and value is None:
        default_icon = TYPE_DEFAULT_ICONS.get(obj_type)
        if default_icon:
            value = default_icon
            source = SYSTEM_THEME_SOURCE

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
    if field_type == 'icon' and _isBeingTracked(object_ref):
        effective_value = derived_value
        effective_source = derived_source
    elif override_value:
        effective_value = override_value
        effective_source = "[Override]"
    else:
        effective_value = derived_value
        effective_source = derived_source

    effective_default = FIELD_DEFAULTS[field_type]

    # Call per-field setter (now calls object's Attribute-based setter)
    setter = EFFECTIVE_SETTERS[field_type]
    setter(object_ref, effective_value, effective_default, effective_source)


# =============================================================================
# computeStyles - Per-Object Style Computation
# =============================================================================

def computeStyles(obj):
    """Compute derived and effective styles for a single object.

    Called by MasterScheduler for each object. Computes all field types.
    Does NOT recurse into notes/attachments - caller handles that.
    Does NOT call computeStoredStatus - caller handles that separately.

    Args:
        obj: Domain object (Task, Category, Note, Attachment)
    """
    for field_type in FIELD_TYPES:
        computeDerived(obj, field_type)
        computeEffective(obj, field_type)


