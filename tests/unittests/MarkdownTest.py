# -*- coding: utf-8 -*-

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
"""

import test
from taskcoachlib.tools.markdown import markdown_to_html

# A code block and a quote start a line below what comes before, but
# not the first thing in a list item or a quote
FIRST_CODE = (
    '<table width="100%%" cellpadding="6"><tr><td><tt>%s</tt></td></tr>'
    "</table>"
)
FIRST_QUOTE = (
    '<table cellspacing="0" cellpadding="0"><tr><td width="4"></td>'
    '<td width="10"></td><td>%s</td></tr></table>'
)
CODE = "<p>%s</p>" % FIRST_CODE
QUOTE = "<p>%s</p>" % FIRST_QUOTE
LINK = '<a href="%s" target="_blank">%s</a>'


class MarkdownTest(test.TestCase):
    def assert_html(self, expected_body, text):
        self.assertEqual(
            "<html><body>%s</body></html>" % expected_body,
            markdown_to_html(text),
        )

    def test_empty(self):
        self.assertEqual("", markdown_to_html(""))
        self.assertEqual("", markdown_to_html(None))

    def test_plain_text_kept(self):
        self.assert_html("<p>3 * 4 = 12</p>", "3 * 4 = 12")
        self.assert_html("<p>file_name_here</p>", "file_name_here")

    def test_line_break_stays_one(self):
        self.assert_html("<p>one<br>\ntwo</p>", "one\ntwo")
        self.assert_html("<p>one</p><p>two</p>", "one\n\ntwo")

    def test_backslash_at_line_end_is_only_a_break(self):
        self.assert_html("<p>one<br>\ntwo</p>", "one\\\ntwo")

    def test_headings(self):
        self.assert_html("<h1>Title<hr></h1>", "# Title")
        self.assert_html("<h2>Title<hr></h2>", "## Title")
        self.assert_html("<h3>Title</h3>", "### Title")
        self.assert_html("<p><b>Four</b></p>", "#### Four")
        self.assert_html(
            '<p><font size="2"><b>Deep</b></font></p>', "###### Deep"
        )
        self.assert_html("<h3>Closed</h3>", "### Closed ###")
        self.assert_html("<p>#5</p>", "#5")

    def test_emphasis(self):
        self.assert_html("<p><b>bold</b></p>", "**bold**")
        self.assert_html("<p><b>bold</b></p>", "__bold__")
        self.assert_html("<p><i>it</i> and <i>it</i></p>", "*it* and _it_")
        self.assert_html("<p><i><b>both</b></i></p>", "***both***")
        self.assert_html(
            "<p>g\u0336o\u0336n\u0336e\u0336 a\u0336n\u0336d\u0336</p>",
            "~~gone and~~",
        )
        self.assert_html("<p><b>bold <tt>code</tt></b></p>", "**bold `code`**")

    def test_emphasis_inside_emphasis(self):
        self.assert_html("<p><b>a <i>b</i> c</b></p>", "**a *b* c**")
        self.assert_html("<p><i>a <b>b</b> c</i></p>", "*a **b** c*")
        self.assert_html("<p><b>a <i>b</i></b></p>", "**a *b***")
        self.assert_html("<p><i>a <b>b</b></i></p>", "_a **b**_")

    def test_emphasis_over_two_lines(self):
        self.assert_html("<p><b>one<br>\ntwo</b></p>", "**one\ntwo**")
        self.assert_html("<p><i>one<br>\ntwo</i></p>", "*one\ntwo*")

    def test_emphasis_leaves_plain_text_alone(self):
        self.assert_html("<p>snake_case_name</p>", "snake_case_name")
        self.assert_html("<p>3 * 4 * 5</p>", "3 * 4 * 5")
        self.assert_html("<p>**never closed</p>", "**never closed")
        self.assert_html("<p>*args and **kwargs</p>", "*args and **kwargs")
        self.assert_html("<p>about ~5 and ~6</p>", "about ~5 and ~6")

    def test_emphasis_not_in_code_or_links(self):
        self.assert_html("<p><tt>**a**</tt></p>", "`**a**`")
        html = markdown_to_html("http://x.com/a_b_c")
        self.assertIn('href="http://x.com/a_b_c"', html)

    def test_lists(self):
        self.assert_html("<ul><li>one</li><li>two</li></ul>", "- one\n- two")
        self.assert_html("<ol><li>one</li><li>two</li></ol>", "1. one\n2. two")
        self.assert_html(
            "<ul><li>one<ul><li>sub</li></ul></li></ul>",
            "- one\n  - sub",
        )

    def test_list_right_after_a_line(self):
        self.assert_html("<p>Todo:</p><ul><li>one</li></ul>", "Todo:\n- one")

    def test_line_after_a_list_is_not_in_it(self):
        self.assert_html("<ul><li>one</li></ul><p>two</p>", "- one\ntwo")

    def test_marker_alone_in_a_paragraph_stays_text(self):
        self.assert_html("<p>one<br>\n-</p>", "one\n- ")

    def test_bullets_under_a_number_indented_by_two(self):
        self.assert_html(
            "<ol><li>one<ul><li>sub</li></ul></li><li>two</li></ol>",
            "1. one\n  - sub\n2. two",
        )

    def test_blank_line_between_items_keeps_one_list(self):
        self.assert_html("<ul><li>one</li><li>two</li></ul>", "- one\n\n- two")

    def test_second_paragraph_in_a_list_item(self):
        self.assert_html(
            "<ul><li>one<p>more</p></li><li>two</li></ul>",
            "- one\n\n  more\n- two",
        )

    def test_code_block_in_a_list_item(self):
        self.assert_html(
            "<ol><li>Run:%s</li><li>Done</li></ol>" % (CODE % "make&nbsp;all"),
            "1. Run:\n   ```sh\n   make all\n   ```\n2. Done",
        )

    def test_code_block_in_a_nested_item_keeps_its_indent(self):
        code = CODE % ("if&nbsp;x:<br>" + "&nbsp;" * 4 + "y")
        self.assert_html(
            "<ul><li>a<ul><li>b%s</li></ul></li></ul>" % code,
            "- a\n  - b\n    ```\n    if x:\n        y\n    ```",
        )

    def test_quote_and_heading_in_a_list_item(self):
        self.assert_html(
            "<ul><li><h3>Title</h3><p>text</p></li><li>%s</li></ul>"
            % (FIRST_QUOTE % "q"),
            "- ### Title\n  text\n- > q",
        )

    def test_task_lists(self):
        html = markdown_to_html("- [ ] todo\n- [x] done")
        self.assertIn("\u25a1&nbsp;</td><td>todo", html)
        self.assertIn("\u2611&nbsp;</td><td>done", html)

    def test_task_box_needs_a_space_after_it(self):
        self.assert_html(
            "<ul><li>%s</li></ul>" % (LINK % ("http://x.com", "x")),
            "- [x](http://x.com)",
        )

    def test_code(self):
        self.assert_html("<p><tt>code</tt></p>", "`code`")
        self.assert_html(CODE % "SELECT&nbsp;1;", "```sql\nSELECT 1;\n```")
        self.assert_html(CODE % "a<br>b", "~~~\na\nb\n~~~")

    def test_code_block_keeps_spaces_and_blank_lines(self):
        self.assert_html(
            CODE % "a&nbsp;&nbsp;b<br><br>&nbsp;&nbsp;&nbsp;&nbsp;c",
            "```\na  b\n\n\tc\n```",
        )

    def test_code_block_shows_markup_as_typed(self):
        self.assert_html(
            CODE % "&lt;b&gt;&nbsp;**x**&nbsp;&amp;amp;",
            "```\n<b> **x** &amp;\n```",
        )

    def test_code_block_language_with_options(self):
        self.assert_html(CODE % "x", '```python title="a b.py"\nx\n```')

    def test_code_block_never_closed_runs_to_the_end(self):
        self.assert_html(CODE % "a<br><br>b", "```\na\n\nb")

    def test_inline_code_holding_a_backtick(self):
        self.assert_html("<p><tt>a ` b</tt></p>", "``a ` b``")
        self.assert_html("<p>a ` b</p>", "a ` b")

    def test_quote(self):
        self.assert_html(QUOTE % "quoted", "> quoted")

    def test_quote_holds_lists_and_code(self):
        self.assert_html(
            QUOTE % ("a<ul><li>b</li></ul>" + CODE % "&nbsp;&nbsp;c"),
            "> a\n> - b\n>\n> ```\n>   c\n> ```",
        )

    def test_blocks_in_a_row_stand_apart(self):
        self.assert_html(
            CODE % "a" + CODE % "b" + QUOTE % "c",
            "```\na\n```\n```\nb\n```\n> c",
        )
        self.assert_html(
            "<ul><li>%s</li></ul>" % (FIRST_CODE % "a" + CODE % "b"),
            "- ```\n  a\n  ```\n  ```\n  b\n  ```",
        )

    def test_quote_in_a_quote(self):
        self.assert_html(QUOTE % ("a" + QUOTE % "b"), "> a\n> > b")

    def test_line_after_a_quote_is_not_in_it(self):
        self.assert_html(QUOTE % "a" + "<p>b</p>", "> a\nb")

    def test_colours_shade_code_and_quotes(self):
        html = markdown_to_html(
            "```\ncode\n```\n\n> quoted",
            code_background="#f0f0f0",
            quote_colour="#808080",
        )
        self.assertIn(
            '<table width="100%" cellpadding="6" bgcolor="#f0f0f0">'
            "<tr><td><tt>code</tt></td></tr></table>",
            html,
        )
        self.assertIn(
            '<td width="4" bgcolor="#808080"></td><td width="10"></td>'
            '<td><font color="#808080">quoted</font></td>',
            html,
        )

    def test_links(self):
        self.assert_html(
            "<p>%s</p>" % (LINK % ("https://example.com", "text")),
            "[text](https://example.com)",
        )
        self.assert_html(
            "<p>%s</p>" % (LINK % ("https://example.com", "text")),
            '[text](https://example.com "title")',
        )
        html = markdown_to_html("see https://example.com/ now")
        self.assertIn('href="https://example.com/"', html)
        html = markdown_to_html("see www.example.com/ now")
        self.assertIn('href="http://www.example.com/"', html)

    def test_link_address_with_brackets(self):
        self.assert_html(
            "<p>%s</p>" % (LINK % ("http://x.com/a_(b)", "w")),
            "[w](http://x.com/a_(b))",
        )
        self.assert_html(
            "<p>(%s)</p>"
            % (LINK % ("http://x.com/a_(b)", "http://x.com/a_(b)")),
            "(http://x.com/a_(b))",
        )

    def test_brackets_that_are_no_link_stay_text(self):
        self.assert_html("<p>[x] and [a](</p>", "[x] and [a](")

    def test_bare_address_in_bold(self):
        self.assert_html(
            "<p><b>%s</b></p>" % (LINK % ("https://x.com", "https://x.com")),
            "**https://x.com**",
        )

    def test_address_in_a_link_text_is_not_linked_again(self):
        self.assert_html(
            "<p>%s</p>" % (LINK % ("http://y.com", "http://x.com")),
            "[http://x.com](http://y.com)",
        )

    def test_image_shows_its_description_as_a_link(self):
        self.assert_html(
            "<p>%s</p>" % (LINK % ("http://x.com/logo.png", "Logo")),
            "![Logo](http://x.com/logo.png)",
        )
        self.assert_html(
            "<p>%s</p>" % (LINK % ("http://x.com/", "Build")),
            "[![Build](http://x.com/badge.svg)](http://x.com/)",
        )

    def test_html_shown_as_typed(self):
        self.assert_html("<p>&lt;b&gt;</p>", "<b>")
        self.assert_html("<p>a &amp; b</p>", "a & b")
        self.assert_html("<p>AT&amp;T; x</p>", "AT&T; x")

    def test_named_characters(self):
        self.assert_html(
            "<p>\u00a9 &amp; &lt; A</p>", "&copy; &amp; &lt; &#65;"
        )

    def test_setext_underline_is_not_a_heading(self):
        html = markdown_to_html("Title\n---")
        self.assertNotIn("<h1>", html)
        self.assertNotIn("<h2>", html)

    def test_indented_code_is_plain_text(self):
        self.assert_html("<p>code</p>", "    code")

    def test_escapes(self):
        self.assert_html("<p>*hi*</p>", "\\*hi\\*")
        self.assert_html("<p>C:\\dir\\file</p>", "C:\\dir\\file")

    def test_rule(self):
        self.assert_html("<hr>", "---")

    def test_spaced_rule(self):
        self.assert_html("<hr>", "* * *")

    def test_ampersand_in_address_escaped_once(self):
        html = markdown_to_html("[q](https://x.com/a?b=1&c=2)")
        self.assertIn('href="https://x.com/a?b=1&amp;c=2"', html)
        html = markdown_to_html("see https://x.com/a?b=1&c=2 now")
        self.assertIn('href="https://x.com/a?b=1&amp;c=2"', html)
        self.assertIn(">https://x.com/a?b=1&amp;c=2</a>", html)

    def test_angle_bracket_autolink(self):
        self.assert_html(
            "<p>%s</p>"
            % (LINK % ("https://example.com", "https://example.com")),
            "<https://example.com>",
        )
        self.assert_html(
            "<p>%s</p>" % (LINK % ("mailto:a@b.com", "a@b.com")), "<a@b.com>"
        )
        self.assert_html(
            "<p>%s</p>" % (LINK % ("mailto:a@b.com", "mailto:a@b.com")),
            "<mailto:a@b.com>",
        )

    def test_mail_address_before_full_stop(self):
        html = markdown_to_html("write to a@b.com.")
        self.assertIn('href="mailto:a@b.com"', html)
        self.assertTrue(html.endswith("</a>.</p></body></html>"))

    def test_code_and_escape_in_link_text(self):
        self.assert_html(
            "<p>%s</p>" % (LINK % ("http://x.com", "<tt>code</tt>")),
            "[`code`](http://x.com)",
        )
        self.assert_html(
            "<p>%s</p>" % (LINK % ("http://x.com", "a*b")),
            "[a\\*b](http://x.com)",
        )

    def test_numbered_list_keeps_its_start(self):
        html = markdown_to_html("5. five\n6. six")
        self.assertIn("5.&nbsp;", html)
        self.assertIn("6.&nbsp;", html)
        self.assertNotIn("<ol>", html)
        self.assertIn("<ol>", markdown_to_html("1. one\n2. two"))

    def test_task_list_has_no_bullet(self):
        html = markdown_to_html("- [ ] todo\n- [x] done")
        self.assertNotIn("<ul>", html)
        self.assertNotIn("<li>", html)

    def test_table(self):
        html = markdown_to_html(
            "| Name | Qty |\n|:--|--:|\n| apple | **3** |\n| pear | 4 |"
        )
        self.assertIn('<table border="1"', html)
        self.assertIn('<th align="left">Name</th>', html)
        self.assertIn('<th align="right">Qty</th>', html)
        self.assertIn('<td align="right"><b>3</b></td>', html)
        self.assertEqual(3, html.count("<tr>"))

    def test_table_needs_its_delimiter_row(self):
        html = markdown_to_html("a | b\nc | d")
        self.assertNotIn("<table", html)
        self.assertIn("<br>", html)

    def test_table_row_short_or_long_fits_the_header(self):
        html = markdown_to_html("| a | b |\n|---|---|\n| 1 |\n| 1 | 2 | 3 |")
        self.assertIn('<td align="left">1</td><td align="left"></td>', html)
        self.assertNotIn(">3<", html)

    def test_escaped_pipe_stays_in_its_cell(self):
        html = markdown_to_html("| a |\n|---|\n| x \\| y |")
        self.assertIn('<td align="left">x | y</td>', html)

    def test_pipe_in_inline_code_stays_in_its_cell(self):
        html = markdown_to_html("| a |\n|---|\n| `x | y` |\n| `x \\| y` |")
        self.assertEqual(2, html.count('<td align="left"><tt>x | y</tt></td>'))

    def test_break_tag_breaks_a_table_cell(self):
        html = markdown_to_html("| a |\n|---|\n| one<br>two<BR/>three |")
        self.assertIn('<td align="left">one<br>\ntwo<br>\nthree</td>', html)

    def test_text_colour(self):
        html = markdown_to_html("hi", text_colour="#ffffff")
        self.assertTrue(html.startswith('<html><body text="#ffffff">'))

    def test_windows_line_ends(self):
        self.assert_html("<p>a<br>\nb</p>", "a\r\nb")

    def test_endless_nesting_stays_text(self):
        html = markdown_to_html(">" * 2000 + " deep\n" + "- " * 2000 + "x")
        self.assertIn("deep", html)
        self.assertIn("x", html)
