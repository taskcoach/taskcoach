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
import datetime
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
    "LONG_DMY": "%A, %d %B %Y",  # Saturday, 28 March 2026
    "ISO_ABBREV": "%Y-%b-%d-%a",  # 2026-Mar-28-Sat
}


def _get_display_override_from_settings():
    from taskcoachlib.config import settings

    return settings.view.dateformat_display_override


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
        _format_map = {"year": "%Y", "month": "%m", "date_day": "%d"}
        dateFormat = _separator.join(
            _format_map.get(f, "%Y") for f in _field_order
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
    return datetime.datetime.strftime(dt, dateFormat)


def dateFunc(dt=None, human_readable=False):
    if human_readable:
        the_date = dt.date()
        if the_date == datemodule.Now().date():
            return _("Today")
        elif the_date == datemodule.Yesterday().date():
            return _("Yesterday")
        elif the_date == datemodule.Tomorrow().date():
            return _("Tomorrow")
    return rawDateFunc(dt)


def dateTimeFunc(dt=None, human_readable=False):
    """Format date and time together. Uses time() to avoid Windows timezone issues."""
    return "%s %s" % (
        dateFunc(dt, human_readable=human_readable),
        time(dt),
    )


def date(a_date_time, human_readable=False):
    """Render a date/time as date."""
    if str(a_date_time) == "":
        return ""
    year = a_date_time.year
    if year >= 1900:
        return dateFunc(a_date_time, human_readable=human_readable)
    else:
        result = date(
            datemodule.DateTime(
                year + 1900, a_date_time.month, a_date_time.day
            ),
            human_readable=human_readable,
        )
        return re.sub(str(year + 1900), str(year), result)


def dateTime(a_date_time, human_readable=False):
    if (
        not a_date_time
        or a_date_time == datemodule.DateTime()
        or a_date_time == datemodule.DateTime.min
    ):
        return ""
    time_is_midnight = (a_date_time.hour, a_date_time.minute) in (
        (0, 0),
        (23, 59),
    )
    year = a_date_time.year
    if year >= 1900:
        return (
            dateFunc(a_date_time, human_readable=human_readable)
            if time_is_midnight
            else dateTimeFunc(a_date_time, human_readable=human_readable)
        )
    else:
        result = dateTime(
            a_date_time.replace(year=year + 1900),
            human_readable=human_readable,
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


def time(date_time, seconds=False, minutes=True):
    """Format a time or datetime for display."""
    try:
        # strftime doesn't handle years before 1900, be prepared:
        date_time = date_time.replace(year=2000)
    except TypeError:  # We got a time instead of a datetime
        # Convert time to datetime for strftime
        import datetime as dt

        date_time = dt.datetime(
            2000, 1, 1, date_time.hour, date_time.minute, date_time.second
        )

    return rawTimeFunc(date_time, minutes=minutes, seconds=seconds)


def month(dateTime):
    return dateTime.strftime("%Y %B")


def weekNumber(dateTime):
    # Would have liked to use dateTime.strftime('%Y-%U'), but the week number
    # is one off in 2004
    return "%d-%d" % (dateTime.year, dateTime.weeknumber())


def monetaryAmount(a_float):
    """Render a monetary amount, using the user's locale."""
    return (
        ""
        if round(a_float, 2) == 0
        else locale.format_string("%.2f", a_float, monetary=True)
    )


def percentage(a_float):
    """Render a percentage."""
    return "" if round(a_float, 0) == 0 else "%.0f%%" % a_float


def exception(exception, instance):
    """Safely render an exception, being prepared for new exceptions."""

    try:
        return str(instance)
    except UnicodeEncodeError:
        return "<class %s>" % str(exception)
