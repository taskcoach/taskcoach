"""
Task Coach - Your friendly task manager
Copyright (C) 2011 Task Coach developers <developers@taskcoach.org>

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

from xml.etree import ElementTree as ET
import os


def anonymize(filename):
    """Anonymize the file specified by the filename by reading its contents,
    replacing the contents with X's and saving the anonymized contents to
    a copy of the file."""

    def anonymize_string(string):
        """Return an anonymized version of the string."""
        return "X" * len(string)

    def anonymize_text(text):
        """Return an anonymized version of the text, keeping the line
        breaks."""
        return "\n".join([anonymize_string(line) for line in text.split("\n")])

    def anonymize_node(node):
        """Recursively anonymize the node and all of its child nodes."""
        for child in node:
            anonymize_node(child)

        if "subject" in node.attrib:
            node.attrib["subject"] = anonymize_string(node.attrib["subject"])

        if node.tag in ("description", "data") and node.text:
            node.text = anonymize_text(node.text)
            if node.tag == "data":
                node.attrib["extension"] = anonymize_string(
                    node.attrib["extension"]
                )

        if (
            node.tag == "property"
            and "name" in node.attrib
            and node.attrib["name"] == "username"
        ):
            node.text = "XXX"  # pylint: disable=W0511

        if node.tag == "attachment" and "location" in node.attrib:
            node.attrib["location"] = anonymize_string(node.attrib["location"])

    tree = ET.parse(filename)
    anonymize_node(tree.getroot())
    name, ext = os.path.splitext(filename)
    anonymized_filename = name + ".anonymized" + ext
    tree.write(anonymized_filename)
    return anonymized_filename
