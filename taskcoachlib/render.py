# -*- coding: utf-8 -*-

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

""" render.py - functions to render various objects, like date, time, 
etc. """  # pylint: disable=W0105

from taskcoachlib.domain import date as datemodule
from taskcoachlib.i18n import _
from taskcoachlib import operating_system
import datetime
import codecs
import locale
import re

# pylint: disable=W0621


def priority(priority):
    """Render an (integer) priority"""
    return str(priority)


def timeLeft(time_left, completed_task):
    """Render time left as a text string. Returns an empty string for
    completed tasks and for tasks without planned due date. Otherwise it
    returns the number of days, hours, and minutes left."""
    if completed_task or time_left == datemodule.TimeDelta.max:
        return ""
    sign = "-" if time_left.days < 0 else ""
    time_left = abs(time_left)
    if time_left.days > 0:
        days = (
            _("%d days") % time_left.days if time_left.days > 1 else _("1 day")
        )
        days += ", "
    else:
        days = ""
    hours_and_minutes = ":".join(str(time_left).split(":")[:-1]).split(", ")[
        -1
    ]
    return sign + days + hours_and_minutes


def time_spent(
    time_spent: datemodule.TimeDelta, show_seconds=True, decimal=False
):
    """Render time spent (of type date.TimeDelta) as
    "<hours>:<minutes>:<seconds>" or "<hours>:<minutes>", or as
    "<hours>.<fractional hours>" when decimal is True (e.g. one hour
    fifteen minutes as "1.25" instead of "1:15", useful for invoices)."""
    zero = datemodule.TimeDelta()
    if time_spent == zero:
        return ""
    else:
        sign = "-" if time_spent < zero else ""
        hours, minutes, seconds = time_spent.hoursMinutesSeconds()
        if decimal:
            return sign + "%.2f" % (hours + minutes / 60.0 + seconds / 3600.0)
        return (
            sign
            + "%d:%02d" % (hours, minutes)
            + (":%02d" % seconds if show_seconds else "")
        )



def recurrence(recurrence):
    """Render the recurrence as a short string describing the frequency of
    the recurrence."""
    if not recurrence:
        return ""
    if recurrence.amount > 2:
        labels = [
            _("Every %(frequency)d days"),
            _("Every %(frequency)d weeks"),
            _("Every %(frequency)d months"),
            _("Every %(frequency)d years"),
        ]
    elif recurrence.amount == 2:
        labels = [
            _("Every other day"),
            _("Every other week"),
            _("Every other month"),
            _("Every other year"),
        ]
    else:
        labels = [_("Daily"), _("Weekly"), _("Monthly"), _("Yearly")]
    mapping = dict(list(zip(["daily", "weekly", "monthly", "yearly"], labels)))
    result = mapping.get(recurrence.unit) % dict(frequency=recurrence.amount)
    # Append weekday names for weekly recurrence if specific days are selected
    if recurrence.unit == "weekly" and recurrence.weekdays:
        weekday_names = [
            _("Mon"),
            _("Tue"),
            _("Wed"),
            _("Thu"),
            _("Fri"),
            _("Sat"),
            _("Sun"),
        ]
        selected_days = [weekday_names[d] for d in sorted(recurrence.weekdays)]
        result += " (" + ", ".join(selected_days) + ")"
    return result


def budget(budget, decimal=False):
    """Render budget (of type date.TimeDelta) as
    "<hours>:<minutes>:<seconds>", or as "<hours>.<fractional hours>"
    when decimal is True."""
    return time_spent(budget, decimal=decimal)


# Date/time format constants - computed once at startup.
# Changing date/time format in preferences requires a restart.
try:
    from taskcoachlib.widgets.maskedtimectrl import getEffectiveTimeFormat
    _timeFormatSetting = getEffectiveTimeFormat()
except Exception:
    _timeFormatSetting = "24"

if _timeFormatSetting == "12":
    timeFormat = "%I %p"
    timeWithMinutesFormat = "%I:%M %p"
    timeWithSecondsFormat = "%I:%M:%S %p"
else:
    timeFormat = "%H"
    timeWithMinutesFormat = "%H:%M"
    timeWithSecondsFormat = "%H:%M:%S"

# Display-only overrides applied on top of the entry-compatible date
# format when rendering. Cannot be used for date input (no name parsing).
_DISPLAY_ONLY_DATE_FORMATS = {
    "LONG_DMY": "%A, %d %B %Y",      # Saturday, 28 March 2026
    "ISO_ABBREV": "%Y-%b-%d-%a",     # 2026-Mar-28-Sat
}


def _get_display_override_from_settings():
    try:
        from taskcoachlib.config import settings
        return settings.Settings().get("view", "dateformat_display_override")
    except Exception as exc:
        from taskcoachlib.meta.debug import log_step
        log_step(
            "could not read dateformat_display_override (%s); treating as empty"
            % exc,
            prefix="RENDER",
        )
        return ""


try:
    _display_override = _get_display_override_from_settings()
    if _display_override in _DISPLAY_ONLY_DATE_FORMATS:
        dateFormat = _DISPLAY_ONLY_DATE_FORMATS[_display_override]
    else:
        if _display_override:
            from taskcoachlib.meta.debug import log_step
            log_step(
                "unknown dateformat_display_override %r; ignoring"
                % _display_override,
                prefix="RENDER",
            )
        from taskcoachlib.widgets.maskedtimectrl import getEffectiveDateFormat
        _field_order, _separator = getEffectiveDateFormat()
        _format_map = {'year': '%Y', 'month': '%m', 'date_day': '%d'}
        dateFormat = _separator.join(
            _format_map.get(f, '%Y') for f in _field_order
        )
except Exception as exc:
    from taskcoachlib.meta.debug import log_step
    log_step(
        "failed to resolve dateFormat (%s); falling back to locale %%x" % exc,
        prefix="RENDER",
    )
    dateFormat = "%x"


def rawTimeFunc(dt, minutes=True, seconds=False):
    if seconds:
        fmt = timeWithSecondsFormat
    elif minutes:
        fmt = timeWithMinutesFormat
    else:
        fmt = timeFormat
    return dt.strftime(fmt)


def rawDateFunc(dt=None):
    return operating_system.decodeSystemString(
        datetime.datetime.strftime(dt, dateFormat)
    )


def dateFunc(dt=None, human_readable=False):
    if human_readable:
        theDate = dt.date()
        if theDate == datemodule.Now().date():
            return _("Today")
        elif theDate == datemodule.Yesterday().date():
            return _("Yesterday")
        elif theDate == datemodule.Tomorrow().date():
            return _("Tomorrow")
    return rawDateFunc(dt)


# OS-specific time formatting
if operating_system.isWindows():
    import pywintypes, win32api

    def rawTimeFunc(dt, minutes=True, seconds=False):
        if dt is None:
            return operating_system.decodeSystemString(
                win32api.GetTimeFormat(0x400, 0, None, None)
            )
        # Use strftime directly to avoid pywintypes.Time() timezone issues.
        # pywintypes.Time() interprets naive datetimes as UTC and converts to
        # local time, causing times like 07:00 to display as 06:00 in UTC+1.
        if seconds:
            fmt = timeWithSecondsFormat
        elif minutes:
            fmt = timeWithMinutesFormat
        else:
            fmt = timeFormat
        return operating_system.decodeSystemString(dt.strftime(fmt))

    def rawDateFunc(dt):
        if dt is None:
            return operating_system.decodeSystemString(
                win32api.GetDateFormat(0x400, 0, None, None)
            )
        # Use strftime directly to avoid pywintypes.Time() timezone issues.
        # pywintypes.Time() interprets naive datetimes as UTC and converts to
        # local time, which can shift dates when times are near midnight.
        return operating_system.decodeSystemString(dt.strftime(dateFormat))

elif operating_system.isMac():
    # Use simple strftime formatting on macOS
    # PyObjC/Cocoa formatting was removed as it adds complexity and
    # dependency issues without significant benefit for a task manager
    def rawTimeFunc(dt, minutes=True, seconds=False):
        if dt is None:
            dt = datetime.datetime.now()
        if seconds:
            return dt.strftime(timeWithSecondsFormat)
        elif minutes:
            return dt.strftime(timeWithMinutesFormat)
        else:
            return dt.strftime(timeFormat)

    def rawDateFunc(dt):
        if dt is None:
            dt = datetime.datetime.now()
        return dt.strftime(dateFormat)


timeFunc = lambda dt, minutes=True, seconds=False: operating_system.decodeSystemString(
    rawTimeFunc(dt, minutes=minutes, seconds=seconds)
)

def dateTimeFunc(dt=None, human_readable=False):
    """Format date and time together. Uses time() to avoid Windows timezone issues."""
    return "%s %s" % (
        dateFunc(dt, human_readable=human_readable),
        time(dt),
    )


def date(aDateTime, human_readable=False):
    """Render a date/time as date."""
    if str(aDateTime) == "":
        return ""
    year = aDateTime.year
    if year >= 1900:
        return dateFunc(aDateTime, human_readable=human_readable)
    else:
        result = date(
            datemodule.DateTime(year + 1900, aDateTime.month, aDateTime.day),
            human_readable=human_readable,
        )
        return re.sub(str(year + 1900), str(year), result)


def dateTime(aDateTime, human_readable=False):
    if (
        not aDateTime
        or aDateTime == datemodule.DateTime()
        or aDateTime == datemodule.DateTime.min
    ):
        return ""
    timeIsMidnight = (aDateTime.hour, aDateTime.minute) in ((0, 0), (23, 59))
    year = aDateTime.year
    if year >= 1900:
        return (
            dateFunc(aDateTime, human_readable=human_readable)
            if timeIsMidnight
            else dateTimeFunc(aDateTime, human_readable=human_readable)
        )
    else:
        result = dateTime(
            aDateTime.replace(year=year + 1900), human_readable=human_readable
        )
        return re.sub(str(year + 1900), str(year), result)


def dateTimePeriod(start, stop, human_readable=False):
    if stop is None:
        return "%s - %s" % (
            dateTime(start, human_readable=human_readable),
            _("now"),
        )
    elif start.date() == stop.date():
        return "%s %s - %s" % (
            date(start, human_readable=human_readable),
            time(start),
            time(stop),
        )
    else:
        return "%s - %s" % (
            dateTime(start, human_readable=human_readable),
            dateTime(stop, human_readable=human_readable),
        )


def time(dateTime, seconds=False, minutes=True):
    """Format a time or datetime for display."""
    try:
        # strftime doesn't handle years before 1900, be prepared:
        dateTime = dateTime.replace(year=2000)
    except TypeError:  # We got a time instead of a dateTime
        # Convert time to datetime for strftime
        import datetime as dt
        dateTime = dt.datetime(2000, 1, 1, dateTime.hour, dateTime.minute, dateTime.second)

    return timeFunc(dateTime, minutes=minutes, seconds=seconds)


def month(dateTime):
    return dateTime.strftime("%Y %B")


def weekNumber(dateTime):
    # Would have liked to use dateTime.strftime('%Y-%U'), but the week number
    # is one off in 2004
    return "%d-%d" % (dateTime.year, dateTime.weeknumber())


def monetaryAmount(aFloat):
    """Render a monetary amount, using the user's locale."""
    return (
        ""
        if round(aFloat, 2) == 0
        else locale.format_string("%.2f", aFloat, monetary=True)
    )


def percentage(aFloat):
    """Render a percentage."""
    return "" if round(aFloat, 0) == 0 else "%.0f%%" % aFloat


def exception(exception, instance):
    """Safely render an exception, being prepared for new exceptions."""

    try:
        # In this order. Python 2.6 fixed the unicode exception problem.
        try:
            return str(instance)
        except UnicodeDecodeError:
            # On Windows, some exceptions raised by win32all lead to this
            # Hack around it
            result = []
            for val in instance.args:
                if isinstance(val, str):
                    result.append(val.encode("UTF-8"))
                else:
                    result.append(val)
            return str(result)
    except UnicodeEncodeError:
        return "<class %s>" % str(exception)
