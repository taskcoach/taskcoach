"""
Task Coach - Your friendly task manager
Copyright (C) 2004-2026 Task Coach developers

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

Markdown preview (docs/MARKDOWN.md): the common syntax, as HTML for
wx.html (HTML 3.2, no CSS). Headings, bold, italic, strikethrough,
code, links, quotes, tables, and bullet, numbered and task lists whose
items hold any of these. Own code, no packages. Each line break stays
one, as in GitHub comments, so plain text looks as typed.
"""

import re
import unicodedata
from html import unescape

_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$")
_HEADING_END = re.compile(r"(?:^|[ \t]+)#+[ \t]*$")
_FENCE = re.compile(r"^( {0,3})(`{3,}|~{3,})(.*)$")
_HR = re.compile(r"^ {0,3}([-*_])(?:[ \t]*\1){2,}[ \t]*$")
_QUOTE = re.compile(r"^ {0,3}> ?")
_LIST = re.compile(r"^([ \t]*)([-*+]|\d{1,9}[.)])([ \t]+)(.*)$")
_TASK = re.compile(r"^\[([ xX])\](?:[ \t]+(.*))?$")
_TABLE_DELIMITER = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$")
_CELL_TOKEN = re.compile(r"\\\||`+|\|")
_AUTOLINK = re.compile(
    r"<((?:https?://|mailto:)[^<>\s]+"
    r"|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})>"
)
_BARE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"{}|\\^`\[\]]+",
    re.IGNORECASE,
)
_BARE_MAIL = re.compile(r"(?<![\w.+-])([\w.+-]+@[\w-]+(?:\.[\w-]+)+)(?![\w-])")
_SCHEME = re.compile(r"(?:https?://|mailto:)", re.IGNORECASE)
_BREAK_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)
_ENTITY = re.compile(
    r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});"
)
_TICKS = re.compile(r"`+")
_SPACE = re.compile(r"\s*")
_TITLE = re.compile(
    r"\s+(?:\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|\((?:[^()\\]|\\.)*\))",
    re.DOTALL,
)
_TAG = re.compile(r"<[^>]*>")
_PUNCTUATION = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
_ESCAPED = re.compile(r"\\([%s])" % re.escape(_PUNCTUATION))
_SPECIAL = frozenset("\\\n`<&[]!*_~")
_TRAILING_PUNCT = ".,;:!?*_~'"
# Struck text is marked, then crossed out once the whole text is HTML
_STRIKE_ON, _STRIKE_OFF = "\x02", "\x03"
_STRUCK = re.compile("\x02([^\x02\x03]*)\x03")
_STRIKE_PARTS = re.compile("(<[^>]*>|&#?\\w+;|\u0336)|(.)", re.DOTALL)
_STROKE = "\u0336"
_CONTROL = re.compile("[\x02\x03]")
_CHECKED = "☑"
_UNCHECKED = "□"
_BULLET = "•"
# Deeper quotes and lists stay text: no input may exhaust the stack
_MAX_DEPTH = 20


def _escape_html(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_href(url):
    return _escape_html(url).replace('"', "&quot;")


def _anchor(href, shown):
    return '<a href="%s" target="_blank">%s</a>' % (
        _escape_href(href),
        shown,
    )


def _is_punctuation(char):
    return char in _PUNCTUATION or unicodedata.category(char).startswith("P")


def _indent_of(line):
    """Width of the leading whitespace, a tab reaching the next
    multiple of four."""
    width = 0
    for char in line:
        if char == " ":
            width += 1
        elif char == "\t":
            width += 4 - width % 4
        else:
            break
    return width


def _dedent(line, columns):
    """The line with up to that many columns of indent taken off."""
    return " " * max(0, _indent_of(line) - columns) + line.lstrip(" \t")


def _trim_address(url):
    """A bare address without the punctuation that ends its sentence;
    a closing bracket stays when the address opened it."""
    while url:
        if url[-1] in _TRAILING_PUNCT or (
            url[-1] == ")" and url.count(")") > url.count("(")
        ):
            url = url[:-1]
        else:
            break
    return url


def _bare_links(text):
    """Addresses written out in the text, by position: what to open,
    what to show and the position after it."""
    found = {}
    for match in _BARE.finditer(text):
        start = match.start()
        if start and text[start - 1].isalnum():
            continue
        url = _trim_address(match.group())
        href = url if "://" in url else "http://" + url
        found[start] = (href, url, start + len(url))
    for match in _BARE_MAIL.finditer(text):
        mail = match.group(1)
        found.setdefault(
            match.start(1), ("mailto:" + mail, mail, match.end(1))
        )
    return found


def _link_target(text, pos):
    """The address of (address "title") at pos and the position after
    it, None when that is not what stands there."""
    if not text.startswith("(", pos):
        return None
    index = _SPACE.match(text, pos + 1).end()
    if text.startswith("<", index):
        end = text.find(">", index)
        address = text[index + 1 : end]
        if end < 0 or "\n" in address or "<" in address:
            return None
        index = end + 1
    else:
        start = index
        depth = 0
        while index < len(text):
            char = text[index]
            if char == "\\" and text[index + 1 : index + 2].strip():
                index += 2
                continue
            if char.isspace():
                break
            if char == "(":
                depth += 1
            elif char == ")":
                if not depth:
                    break
                depth -= 1
            index += 1
        if depth:
            return None
        address = text[start:index]
    title = _TITLE.match(text, index)
    if title:
        index = title.end()
    index = _SPACE.match(text, index).end()
    if not text.startswith(")", index):
        return None
    address = _ENTITY.sub(lambda m: unescape(m.group()), address)
    return _ESCAPED.sub(r"\1", address), index + 1


class _Run:
    """A run of emphasis marks (* _ ~~): what is left of it once
    paired, and the tags it then closes and opens."""

    def __init__(self, char, count, opens, closes):
        self.char = char
        self.count = self.left = count
        self.opens = opens
        self.closes = closes
        self.live = True
        self.closing = []
        self.opening = []

    def render(self, _linked):
        return (
            "".join(self.closing)
            + self.char * self.left
            + "".join(self.opening)
        )


class _Bracket:
    """An opening [ or ![, text unless a link comes to close it."""

    def __init__(self, image):
        self.image = image
        self.active = True

    def render(self, _linked):
        return "![" if self.image else "["


class _Link:
    """A link that is text inside another link's text: a bare address,
    an image."""

    def __init__(self, href, shown):
        self.href = href
        self.shown = shown

    def render(self, linked):
        return self.shown if linked else _anchor(self.href, self.shown)


def _pair_runs(nodes):
    """Pair the emphasis marks by CommonMark's rules, the nearest
    opener first, so nested bold and italic close in order."""
    runs = [node for node in nodes if isinstance(node, _Run)]
    floors = {}
    current = 0
    while current < len(runs):
        closer = runs[current]
        if not (closer.closes and closer.left):
            current += 1
            continue
        key = (closer.char, closer.opens, closer.count % 3)
        found = None
        for index in range(current - 1, floors.get(key, -1), -1):
            opener = runs[index]
            if not (opener.live and opener.opens and opener.left):
                continue
            if opener.char != closer.char:
                continue
            # A run that both opens and closes pairs only where the
            # lengths cannot be read two ways (*a**b*)
            if (
                closer.char != "~"
                and (opener.closes or closer.opens)
                and (opener.count + closer.count) % 3 == 0
                and closer.count % 3
            ):
                continue
            found = index
            break
        if found is None:
            floors[key] = current - 1
            current += 1
            continue
        opener = runs[found]
        if closer.char == "~":
            used, opening, closing = 2, _STRIKE_ON, _STRIKE_OFF
        elif opener.left >= 2 and closer.left >= 2:
            used, opening, closing = 2, "<b>", "</b>"
        else:
            used, opening, closing = 1, "<i>", "</i>"
        opener.left -= used
        closer.left -= used
        opener.opening.insert(0, opening)
        closer.closing.append(closing)
        for between in runs[found + 1 : current]:
            between.live = False
        if not closer.left:
            current += 1


def _join(nodes, linked=False):
    _pair_runs(nodes)
    return "".join(
        node if isinstance(node, str) else node.render(linked)
        for node in nodes
    )


def _struck(text):
    """The text crossed out, character by character with the combining
    long stroke: wx.html draws <strike> as an underline, which reads as
    a link. Tags and entities are left whole."""
    parts = []
    for kept, char in _STRIKE_PARTS.findall(text):
        parts.append(kept or char)
        if char and not char.isspace():
            parts.append(_STROKE)
    return "".join(parts)


class _Scanner:
    """One pass over a paragraph's text, left to right, the way
    CommonMark reads it: what comes first wins, so code hides the
    marks inside it and a link's address is never styled."""

    def __init__(self, text):
        self.text = text
        self.nodes = []
        self.brackets = []

    def scan(self):
        text = self.text
        bare = _bare_links(text)
        pos = plain = 0
        while pos < len(text):
            if pos not in bare and text[pos] not in _SPECIAL:
                pos += 1
                continue
            if pos > plain:
                self.nodes.append(_escape_html(text[plain:pos]))
                plain = pos
            end = self._take(pos, bare.get(pos))
            if end is None:
                pos += 1
            else:
                pos = plain = end
        if pos > plain:
            self.nodes.append(_escape_html(text[plain:]))
        return self.nodes

    def _take(self, pos, bare):
        """Take the syntax at pos into the nodes: the position after
        it, None when the character there is plain text."""
        text = self.text
        char = text[pos]
        following = text[pos + 1 : pos + 2]
        if bare:
            href, shown, end = bare
            self.nodes.append(_Link(href, _escape_html(shown)))
            return end
        if char == "\n":
            self.nodes.append("<br>\n")
            return pos + 1
        if char == "\\":
            if following == "\n":
                return pos + 1
            if following and following in _PUNCTUATION:
                self.nodes.append(_escape_html(following))
                return pos + 2
            return None
        if char == "`":
            return self._code(pos)
        if char == "<":
            return self._angle(pos)
        if char == "&":
            return self._entity(pos)
        if char == "[" or (char == "!" and following == "["):
            bracket = _Bracket(char == "!")
            self.brackets.append(bracket)
            self.nodes.append(bracket)
            return pos + len(bracket.render(False))
        if char == "!":
            return None
        if char == "]":
            return self._close(pos)
        return self._run(pos)

    def _code(self, pos):
        ticks = _TICKS.match(self.text, pos).group()
        start = pos + len(ticks)
        closing = re.compile("(?<!`)%s(?!`)" % ticks).search(self.text, start)
        if not closing:
            self.nodes.append(ticks)
            return start
        code = self.text[start : closing.start()].replace("\n", " ")
        if code.strip(" ") and code[0] == " " == code[-1]:
            code = code[1:-1]
        self.nodes.append("<tt>%s</tt>" % _escape_html(code))
        return closing.end()

    def _angle(self, pos):
        match = _AUTOLINK.match(self.text, pos)
        if match:
            target = match.group(1)
            href = target if _SCHEME.match(target) else "mailto:" + target
            self.nodes.append(_Link(href, _escape_html(target)))
            return match.end()
        match = _BREAK_TAG.match(self.text, pos)
        if match:
            # The one tag honoured: the only way to break a table cell
            self.nodes.append("<br>\n")
            return match.end()
        return None

    def _entity(self, pos):
        match = _ENTITY.match(self.text, pos)
        if not match or unescape(match.group()) == match.group():
            return None
        self.nodes.append(_escape_html(unescape(match.group())))
        return match.end()

    def _close(self, pos):
        """A ] makes a link or an image of the nearest open bracket
        when (address) follows."""
        if not self.brackets:
            return None
        bracket = self.brackets.pop()
        target = _link_target(self.text, pos + 1) if bracket.active else None
        if target is None:
            return None
        href, end = target
        first = self.nodes.index(bracket)
        shown = _join(self.nodes[first + 1 :], linked=True)
        del self.nodes[first:]
        if bracket.image:
            # wx.html loads no web image: its description, linked
            shown = _TAG.sub("", shown) or _escape_html(href)
            self.nodes.append(_Link(href, shown))
        else:
            self.nodes.append(_anchor(href, shown))
            # No link inside a link
            for other in self.brackets:
                other.active = other.image
        return end

    def _run(self, pos):
        text = self.text
        char = text[pos]
        end = pos
        while end < len(text) and text[end] == char:
            end += 1
        count = end - pos
        before = text[pos - 1] if pos else " "
        after = text[end] if end < len(text) else " "
        left = not after.isspace() and (
            not _is_punctuation(after)
            or before.isspace()
            or _is_punctuation(before)
        )
        right = not before.isspace() and (
            not _is_punctuation(before)
            or after.isspace()
            or _is_punctuation(after)
        )
        if char == "_":
            # Not inside a word: snake_case stays as typed
            opens = left and (not right or _is_punctuation(before))
            closes = right and (not left or _is_punctuation(after))
        else:
            opens, closes = left, right
        if (char == "~" and count != 2) or not (opens or closes):
            self.nodes.append(char * count)
        else:
            self.nodes.append(_Run(char, count, opens, closes))
        return end


def _inline(text):
    """Inline syntax as HTML: code, bold, italic, strikethrough,
    links, images, bare addresses, escapes."""
    result = _join(_Scanner(text).scan())
    while True:
        # Innermost first: struck text may hold struck text
        crossed = _STRUCK.sub(lambda m: _struck(m.group(1)), result)
        if crossed == result:
            return result
        result = crossed


def _table_cells(line):
    """The cells of a table row. A pipe splits them unless escaped or
    inside inline code."""
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    cells = []
    cell = ""
    pos = 0
    while True:
        token = _CELL_TOKEN.search(line, pos)
        if not token:
            break
        cell += line[pos : token.start()]
        pos = token.end()
        mark = token.group()
        if mark == "|":
            cells.append(cell)
            cell = ""
        elif mark == "\\|":
            cell += "|"
        else:
            closing = re.compile("(?<!`)%s(?!`)" % mark).search(line, pos)
            if closing:
                cell += mark + line[pos : closing.end()].replace("\\|", "|")
                pos = closing.end()
            else:
                cell += mark
    cell += line[pos:]
    # A pipe may close the row: nothing after it is no cell
    if cell.strip() or not cells:
        cells.append(cell)
    return [entry.strip() for entry in cells]


def _starts_table(lines, index):
    if index + 1 >= len(lines):
        return False
    header, delimiter = lines[index], lines[index + 1]
    return (
        "|" in header
        and "|" in delimiter
        and _TABLE_DELIMITER.match(delimiter) is not None
        and len(_table_cells(header)) == len(_table_cells(delimiter))
    )


def _fence(line):
    """The match of a line opening a code block. A language may follow
    (```python), but no backtick: that is inline code."""
    match = _FENCE.match(line)
    if match and not ("`" in match.group(2) and "`" in match.group(3)):
        return match
    return None


def _starts_block(lines, index):
    """Whether the line ends the paragraph before it. A list marker
    with nothing after it does not: that is a dash in the text."""
    line = lines[index]
    item = _LIST.match(line)
    return bool(
        not line.strip()
        or _fence(line)
        or _HEADING.match(line)
        or _HR.match(line)
        or _QUOTE.match(line)
        or (item and item.group(4).strip())
        or _starts_table(lines, index)
    )


class _Blocks:
    """Lines to HTML, block by block. A quote and a list item hold
    blocks of their own, read the same way once their marker and
    indent are taken off."""

    def __init__(self, code_background, quote_colour):
        self._code_background = code_background
        self._quote_colour = quote_colour

    def render(self, lines, depth=0):
        """The lines as HTML. Text, code, a quote and a table each
        start a line below what comes before (<p>), but not the first
        in a quote or a list item (depth): it sits beside its marker.
        A list stays right under the line that announces it."""
        parts = []
        index = 0
        nests = depth < _MAX_DEPTH
        while index < len(lines):
            line = lines[index]
            fence = _fence(line)
            block = None
            if not line.strip():
                index += 1
            elif fence:
                block, index = self._code(lines, index, fence)
            elif _HEADING.match(line):
                parts.append(self._heading(line))
                index += 1
            elif _HR.match(line):
                parts.append("<hr>")
                index += 1
            elif nests and _QUOTE.match(line):
                block, index = self._quote(lines, index, depth)
            elif _starts_table(lines, index):
                block, index = self._table(lines, index)
            elif nests and _LIST.match(line):
                items, index = self._list(lines, index, depth)
                parts.append(items)
            else:
                start = index
                index += 1
                while index < len(lines) and not _starts_block(lines, index):
                    index += 1
                block = _inline(
                    "\n".join(entry.strip() for entry in lines[start:index])
                )
            if block is not None:
                parts.append(
                    block if depth and not parts else "<p>%s</p>" % block
                )
        return "".join(parts)

    def _code(self, lines, index, fence):
        """The code block opened at lines[index]: its HTML and the
        index of the first line after it. Shaded, a row for each line:
        wx.html puts a blank line above a <pre>."""
        indent, mark = len(fence.group(1)), fence.group(2)
        closing = re.compile("^ {0,3}%s{%d,}[ \t]*$" % (mark[0], len(mark)))
        rows = []
        index += 1
        while index < len(lines) and not closing.match(lines[index]):
            row = _dedent(lines[index], indent).expandtabs(4)
            rows.append(_escape_html(row).replace(" ", "&nbsp;"))
            index += 1
        shade = (
            ' bgcolor="%s"' % self._code_background
            if self._code_background
            else ""
        )
        return (
            '<table width="100%%" cellpadding="6"%s><tr><td><tt>%s</tt></td>'
            "</tr></table>" % (shade, "<br>".join(rows)),
            index + 1,
        )

    @staticmethod
    def _heading(line):
        """The two top levels are underlined, as on GitHub; the rule
        goes inside the heading, or wx.html drops it a line lower. The
        three lowest are bold text, the last two smaller: wx.html
        draws its own <h4> and <h6> in italics."""
        marks, title = _HEADING.match(line).groups()
        level = len(marks)
        title = _inline(_HEADING_END.sub("", title).strip())
        if level == 4:
            return "<p><b>%s</b></p>" % title
        if level > 4:
            return '<p><font size="2"><b>%s</b></font></p>' % title
        rule = "<hr>" if level <= 2 else ""
        return "<h%d>%s%s</h%d>" % (level, title, rule, level)

    def _quote(self, lines, index, depth):
        """The quote starting at lines[index], a bar down its left
        side: a narrow coloured cell, since wx.html draws none."""
        quoted = []
        while index < len(lines) and _QUOTE.match(lines[index]):
            quoted.append(_QUOTE.sub("", lines[index], count=1))
            index += 1
        inner = self.render(quoted, depth + 1)
        bar = ""
        if self._quote_colour:
            bar = ' bgcolor="%s"' % self._quote_colour
            inner = '<font color="%s">%s</font>' % (self._quote_colour, inner)
        return (
            '<table cellspacing="0" cellpadding="0"><tr><td width="4"%s></td>'
            '<td width="10"></td><td>%s</td></tr></table>' % (bar, inner),
            index,
        )

    @staticmethod
    def _table(lines, index):
        """The GitHub pipe table starting at lines[index]."""
        header = _table_cells(lines[index])
        aligns = []
        for cell in _table_cells(lines[index + 1]):
            if cell.startswith(":") and cell.endswith(":"):
                aligns.append("center")
            elif cell.endswith(":"):
                aligns.append("right")
            else:
                aligns.append("left")

        def row(cells, tag):
            return "<tr>%s</tr>" % "".join(
                '<%s align="%s">%s</%s>' % (tag, align, _inline(cell), tag)
                for cell, align in zip(cells, aligns)
            )

        rows = [row(header, "th")]
        index += 2
        while index < len(lines) and lines[index].strip():
            if "|" not in lines[index]:
                break
            cells = _table_cells(lines[index])[: len(header)]
            rows.append(row(cells + [""] * (len(header) - len(cells)), "td"))
            index += 1
        return (
            '<table border="1" cellspacing="0" cellpadding="4">%s</table>'
            % "".join(rows),
            index,
        )

    def _list(self, lines, index, depth):
        """The list starting at lines[index], bullets or numbers. An
        item goes on with every line indented further than its marker,
        blank lines between them too: a second paragraph, code, a list
        inside it."""
        ordered = _LIST.match(lines[index]).group(2)[0].isdigit()
        items = []
        while index < len(lines):
            match = _LIST.match(lines[index])
            if (
                not match
                or _HR.match(lines[index])
                or match.group(2)[0].isdigit() != ordered
            ):
                break
            indent = _indent_of(match.group(1))
            marker, gap, content = match.group(2, 3, 4)
            column = indent + len(marker) + 1
            if content and len(gap) <= 4 and "\t" not in gap:
                column += len(gap) - 1
            box = None
            task = _TASK.match(content)
            if task:
                box = _UNCHECKED if task.group(1) == " " else _CHECKED
                content = task.group(2) or ""
            body = [content]
            index += 1
            while index < len(lines):
                ahead = index
                while ahead < len(lines) and not lines[ahead].strip():
                    ahead += 1
                if ahead == len(lines) or _indent_of(lines[ahead]) <= indent:
                    break
                body.extend([""] * (ahead - index))
                body.append(_dedent(lines[ahead], column))
                index = ahead + 1
            number = int(marker[:-1]) if ordered else 0
            items.append((number, box, self.render(body, depth + 1)))
            # A blank line between two items leaves them in one list
            ahead = index
            while ahead < len(lines) and not lines[ahead].strip():
                ahead += 1
            if ahead < len(lines) and _LIST.match(lines[ahead]):
                index = ahead
        return self._list_html(items, ordered), index

    @staticmethod
    def _list_html(items, ordered):
        """wx.html numbers from 1 and always draws a bullet, so a list
        starting elsewhere or holding task boxes is laid out as a
        table with its own markers."""
        start = items[0][0]
        if not any(box for _number, box, _body in items) and (
            not ordered or start == 1
        ):
            tag = "ol" if ordered else "ul"
            return "<%s>%s</%s>" % (
                tag,
                "".join("<li>%s</li>" % body for _number, _box, body in items),
                tag,
            )
        rows = []
        for offset, (_number, box, body) in enumerate(items):
            marker = box or ("%d." % (start + offset) if ordered else _BULLET)
            rows.append(
                '<tr><td width="12"></td><td valign="top" align="right">'
                "%s&nbsp;</td><td>%s</td></tr>" % (marker, body)
            )
        return '<table cellspacing="0" cellpadding="0">%s</table>' % "".join(
            rows
        )


def markdown_to_html(
    text, code_background=None, quote_colour=None, text_colour=None
):
    """Render Markdown as HTML for wx.html. The colours, hex strings,
    shade code blocks, grey quotes and their bar, and set the text;
    without them each stays as the window draws it, so plain converter
    tests need no theme."""
    if not text:
        return ""
    text = _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    body = _Blocks(code_background, quote_colour).render(text.split("\n"))
    attributes = ' text="%s"' % text_colour if text_colour else ""
    return "<html><body%s>%s</body></html>" % (attributes, body)
