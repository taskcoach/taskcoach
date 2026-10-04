#! /usr/bin/env python

"""Generate python dictionaries catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a python dictionary

Based on msgfmt.py by Martin v. Löwis <loewis@informatik.hu-berlin.de>

"""

import ast
import re

MESSAGES = {}
STRINGS = set()

# pylint: disable=W0602,W0603


def add(id_, string, fuzzy):
    "Add a non-fuzzy translation to the dictionary."
    if not fuzzy and string:
        MESSAGES[id_] = string
    STRINGS.add(id_)


def parse(filename):
    """Parse a .po file and return (dict, encoding) directly without writing a file."""
    ID = 1
    STR = 2
    global MESSAGES
    MESSAGES = {}

    if filename.endswith(".po"):
        infile = filename
    else:
        infile = filename + ".po"

    with open(infile, encoding="utf-8") as f:
        lines = f.readlines()

    section = None
    fuzzy = 0
    msgid = msgstr = ""

    for l in lines:
        if l and l[0] == "#" and section == STR:
            add(msgid, msgstr, fuzzy)
            section = None
            fuzzy = 0
        if l[:2] == "#," and "fuzzy" in l:
            fuzzy = 1
        if l and l[0] == "#":
            continue
        if l.startswith("msgid"):
            if section == STR:
                add(msgid, msgstr, fuzzy)
            section = ID
            l = l[5:]
            msgid = msgstr = ""
        elif l.startswith("msgstr"):
            section = STR
            l = l[6:]
        l = l.strip()
        if not l:
            continue
        l = ast.literal_eval(l)
        if section == ID:
            msgid += l
        elif section == STR:
            msgstr += l

    if section == STR:
        add(msgid, msgstr, fuzzy)

    metadata = MESSAGES.get("", "")
    if "" in MESSAGES:
        del MESSAGES[""]

    match = re.search(r"charset=(\S*)\n", metadata)
    encoding = match.group(1) if match else "UTF-8"

    return MESSAGES.copy(), encoding
