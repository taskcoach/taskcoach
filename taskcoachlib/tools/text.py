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

Text a task file can hold (docs/ATTRIBUTE_PATTERN.md, Text).
"""

import re

# Control characters, halves of a character (surrogates) and the two
# non-characters XML forbids; multi-line text keeps tab and line breaks
_NOT_TEXT = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff￾￿]")
_TAB_OR_LINE_BREAK = re.compile("\r\n|[\t\n\r]")


def multi_line(text):
    """Text of several lines: tab and line breaks, no other control
    character."""
    return _NOT_TEXT.sub("", text) if text else text


def single_line(text):
    """Text of one line: a tab or line break becomes a space, as a paste
    into a one-line field does; no other control character."""
    return multi_line(_TAB_OR_LINE_BREAK.sub(" ", text)) if text else text
