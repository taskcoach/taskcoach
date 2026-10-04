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
"""

# The date expressions of task templates: "tomorrow", "3pm tomorrow",
# "in 2 days", "next saturday at noon", "20 minutes from now"; English
# on every system, as the Help says. The grammar of the pyparsing
# example Task Coach used before (delta_time.py, docs/DEPENDENCIES.md),
# read the same way: of the alternatives the first that matches wins,
# a keyword is never part of a longer word, and the expression is the
# longest one at the start of the text.

import datetime
import re
import string

_SPACE = " \t\n\r"
# Characters that continue a word: a keyword next to one is part of it
_WORD = frozenset(string.ascii_uppercase + string.digits + "_$")
_NUMBER_WORD = frozenset(string.ascii_uppercase + "-")
_CLOCK_WORD = frozenset(string.ascii_uppercase + "'")
_DIGITS = re.compile(r"[0-9]+")
_HHMM = re.compile(r"\b([01]\d|2[0-3])([0-5]\d)\b")
_NUMBERS = (
    "one two three four five six seven eight nine ten eleven twelve"
    " thirteen fourteen fifteen sixteen seventeen eighteen nineteen"
    " twenty twenty-one twenty-two twenty-three twenty-four"
).split()
_WEEKDAYS = "monday tuesday wednesday thursday friday saturday sunday"
_WEEKDAYS = _WEEKDAYS.split()
_SECONDS = {"hour": 3600, "minute": 60, "second": 1}
_DAYS = {"week": 7, "day": 1}
_SIGN = {"from": 1, "after": 1, "before": -1}


class _Reader:
    """Each rule returns where it ended and its value, or None."""

    def __init__(self, text, now):
        self.text = text
        self.now = now.replace(microsecond=0)

    def skip(self, pos):
        while pos < len(self.text) and self.text[pos] in _SPACE:
            pos += 1
        return pos

    def word(self, pos, words, word_characters=_WORD):
        """The first of words at pos, any case, not inside a longer
        word."""
        pos = self.skip(pos)
        before = self.text[pos - 1 : pos].upper()
        if before and before in word_characters:
            return None
        for word in words:
            end = pos + len(word)
            after = self.text[end : end + 1].upper()
            if self.text[pos:end].upper() == word.upper() and not (
                after and after in word_characters
            ):
                return end, word
        return None

    def literal(self, pos, words):
        """The first of words at pos, any case, even inside a word."""
        pos = self.skip(pos)
        for word in words:
            if self.text[pos : pos + len(word)].lower() == word:
                return pos + len(word), word
        return None

    def number(self, pos):
        pos = self.skip(pos)
        match = _DIGITS.match(self.text, pos)
        if match:
            return match.end(), int(match.group())
        found = self.word(pos, _NUMBERS, _NUMBER_WORD)
        return found and (found[0], _NUMBERS.index(found[1]) + 1)

    def quantity(self, pos):
        """["just" | "only" | "exactly"] (a number | [a] couple [of]
        | a | an | the)"""
        found = self.word(pos, ("just", "only", "exactly"))
        pos = found[0] if found else pos
        found = self.number(pos)
        if found:
            return found
        start = self.word(pos, ("a",))
        found = self.word(start[0] if start else pos, ("couple",))
        if found:
            of = self.word(found[0], ("of",))
            return (of or found)[0], 2
        found = self.word(pos, ("a", "an", "the"))
        return found and (found[0], 1)

    def unit(self, pos, units):
        for unit in units:
            found = self.word(pos, (unit, unit + "s"))
            if found:
                return found[0], unit
        return None

    def clock_time(self, pos):
        """HHMM, unless a number of units ("1200 hours"), or hour
        [o'clock | :minute [:second]] am|pm"""
        start = self.skip(pos)
        digits = _DIGITS.match(self.text, start)
        units = ("week", "day", *_SECONDS)
        if not (digits and self.unit(digits.end(), units)):
            match = _HHMM.match(self.text, start)
            if match:
                hour, minute = map(int, match.groups())
                return match.end(), datetime.time(hour, minute)
        found = self.number(pos)
        if not found:
            return None
        pos, hour = found
        minute = second = 0
        found = self.word(pos, ("o'clock",), _CLOCK_WORD)
        colon = not found and self.literal(pos, (":",))
        minutes = colon and self.number(colon[0])
        if found:
            pos = found[0]
        elif minutes:
            pos, minute = minutes
            colon = self.literal(pos, (":",))
            seconds = colon and self.number(colon[0])
            if seconds:
                pos, second = seconds
        found = self.literal(pos, ("am", "pm"))
        if not found:
            return None
        hour = hour % 12 + (12 if found[1] == "pm" else 0)
        # A minute or second over 59 raises ValueError, as it did
        return found[0], datetime.time(hour, minute, second)

    def time_of_day(self, pos):
        found = self.word(pos, ("noon", "midnight", "now"))
        if not found:
            return self.clock_time(pos)
        if found[1] == "now":
            return found[0], self.now.time()
        return found[0], datetime.time(12 if found[1] == "noon" else 0)

    def relative(self, pos, units, reference):
        """quantity units ("ago" | ("from" | "before" | "after")
        reference) | "in" quantity units: end, signed quantity, unit
        and the reference's result or None."""
        found = self.quantity(pos)
        unit = found and self.unit(found[0], units)
        if unit:
            ago = self.word(unit[0], ("ago",))
            if ago:
                return ago[0], -found[1], unit[1], None
            way = self.word(unit[0], ("from", "before", "after"))
            ref = way and reference(way[0])
            if ref:
                return ref[0], _SIGN[way[1]] * found[1], unit[1], ref
        word = self.word(pos, ("in",))
        found = word and self.quantity(word[0])
        unit = found and self.unit(found[0], units)
        return unit and (unit[0], found[1], unit[1], None)

    def time_reference(self, pos):
        """A time of day or a time relative to one: end, time and
        offset."""
        found = self.time_of_day(pos)
        if found:
            return found[0], found[1], datetime.timedelta()
        found = self.relative(pos, _SECONDS, self.time_of_day)
        if not found:
            return None
        end, count, unit, ref = found
        time = ref[1] if ref else self.now.time()
        delta = datetime.timedelta(seconds=count * _SECONDS[unit])
        return end, time, delta

    def day(self, pos):
        """today | tomorrow | yesterday | now | [next | last] weekday:
        end, date and time, and whether the time is now's."""
        today = datetime.datetime.combine(self.now.date(), datetime.time())
        found = self.word(pos, ("today", "tomorrow", "yesterday", "now"))
        if found:
            if found[1] == "now":
                return found[0], self.now, True
            days = {"today": 0, "tomorrow": 1, "yesterday": -1}[found[1]]
            return found[0], today + datetime.timedelta(days=days), False
        way = self.word(pos, ("next", "last"))
        found = self.word(way[0] if way else pos, _WEEKDAYS)
        if not found:
            return None
        weekday, named = self.now.weekday(), _WEEKDAYS.index(found[1])
        if way and way[1] == "last":
            days = -((weekday - named) % 7 or 7)
        elif named == weekday and not way:
            days = 0  # Today
        else:
            days = (named - weekday) % 7 or 7
        return found[0], today + datetime.timedelta(days=days), False

    def day_reference(self, pos):
        """A day or days relative to one: end, date and time or None,
        offset, and whether the time is now's."""
        found = self.relative(pos, _DAYS, self.day)
        if found:
            end, count, unit, ref = found
            delta = datetime.timedelta(days=count * _DAYS[unit])
            return end, ref and ref[1], delta, bool(ref and ref[2])
        found = self.day(pos)
        return found and (found[0], found[1], datetime.timedelta(), found[2])

    def expression(self, pos):
        """time [[on] day] | day [[at] time of day]: end and the date
        and time. Without a time the result is at midnight."""
        date, date_delta = None, datetime.timedelta()
        found = self.time_reference(pos)
        if found:
            pos, time, time_delta = found
            has_time = True
            on = self.word(pos, ("on",))
            day = self.day_reference(on[0] if on else pos)
            if day:
                pos, date, date_delta, _ = day
        else:
            day = self.day_reference(pos)
            if not day:
                return None
            pos, date, date_delta, has_time = day
            time, time_delta = self.now.time(), datetime.timedelta()
            at = self.word(pos, ("at",))
            found = self.time_of_day(at[0] if at else pos)
            if found:
                pos, time = found
                has_time = True
        result = datetime.datetime.combine((date or self.now).date(), time)
        result += time_delta + date_delta
        if not has_time:
            result = datetime.datetime.combine(result.date(), datetime.time())
        return pos, result


def parse(text, now=None):
    """The date and time of the expression text starts with, relative
    to now; ValueError when it starts with none or gives no date."""
    reader = _Reader(text, now or datetime.datetime.now())
    try:
        found = reader.expression(0)
    except OverflowError as reason:  # "99999999 weeks from now"
        raise ValueError("Out of range: %r" % text) from reason
    if not found:
        raise ValueError("Not a date expression: %r" % text)
    return found[1]
