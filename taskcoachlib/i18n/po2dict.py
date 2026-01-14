#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""Generate python dictionaries catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a python dictionary 

Based on msgfmt.py by Martin v. L�wis <loewis@informatik.hu-berlin.de>

"""

import sys, re, os, ast

MESSAGES = {}
STRINGS = set()

# pylint: disable=W0602,W0603


def add(id_, string, fuzzy):
    "Add a non-fuzzy translation to the dictionary."
    global MESSAGES
    if not fuzzy and string:
        MESSAGES[id_] = string
    STRINGS.add(id_)


def generateDict():
    "Return the generated dictionary"
    global MESSAGES
    metadata = MESSAGES[""]
    del MESSAGES[""]
    encoding = re.search(r"charset=(\S*)\n", metadata).group(1)
    return (
        "# -*- coding: %s -*-\n#This is generated code - do not edit\nencoding = '%s'\ndict = %s"
        % (encoding, encoding, MESSAGES)
    )


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

    with open(infile, encoding='utf-8') as f:
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


def make(filename, outfile=None):
    ID = 1
    STR = 2
    global MESSAGES
    MESSAGES = {}

    # Compute .py name from .po name and arguments
    if filename.endswith(".po"):
        infile = filename
    else:
        infile = filename + ".po"
    if outfile is None:
        outfile = os.path.splitext(infile)[0] + ".py"

    try:
        lines = open(infile).readlines()
    except IOError as msg:
        print(msg, file=sys.stderr)
        sys.exit(1)

    section = None
    fuzzy = 0

    # Parse the catalog
    lno = 0
    for l in lines:
        lno += 1
        # If we get a comment line after a msgstr, this is a new entry
        if l[0] == "#" and section == STR:
            add(msgid, msgstr, fuzzy)  # pylint: disable=E0601
            section = None
            fuzzy = 0
        # Record a fuzzy mark
        if l[:2] == "#," and l.find("fuzzy"):
            fuzzy = 1
        # Skip comments
        if l[0] == "#":
            continue
        # Now we are in a msgid section, output previous section
        if l.startswith("msgid"):
            if section == STR:
                add(msgid, msgstr, fuzzy)
            section = ID
            l = l[5:]
            msgid = msgstr = ""
        # Now we are in a msgstr section
        elif l.startswith("msgstr"):
            section = STR
            l = l[6:]
        # Skip empty lines
        l = l.strip()
        if not l:
            continue
        # XXX: Does this always follow Python escape semantics? # pylint: disable=W0511
        l = ast.literal_eval(l)
        if section == ID:
            msgid += l
        elif section == STR:
            msgstr += l
        else:
            print(
                "Syntax error on %s:%d" % (infile, lno),
                "before:",
                file=sys.stderr,
            )
            print(l, file=sys.stderr)
            sys.exit(1)
    # Add last entry
    if section == STR:
        add(msgid, msgstr, fuzzy)

    # Compute output
    output = generateDict()

    # TODO: This is a hack to get the encoding from the output
    encoding = re.search(r"\-\*\-\s*coding\:\s*(.*)\s*\-\*\-\n", output).group(
        1
    )

    try:
        open(outfile, "w", encoding=encoding).write(output)
    except IOError as msg:
        print(msg, file=sys.stderr)

    return outfile
