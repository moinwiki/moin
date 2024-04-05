#!/usr/bin/env python
# Copyright: 2012-2018 MoinMoin:RogerHaase
# Copyright: 2023 MoinMoin project
# License: GNU GPL v2 (or any later version), see LICENSE.txt for details.

"""
Detect and correct violations of the moin2 coding standards:
    - no trailing blanks
    - exactly one linefeed at file end, see PEP8
    - DOS line endings on .bat and .cmd files, unix line endings everywhere else

Detect and write informative message:
    - improper indentation of template files ending with .html suffix

Execute this script from the root directory of the moin repository
to process all files in the <root>/src directory.

Or, pass a directory path on the command line.

    python scripts/coding_std.py <starting-directory>
"""

import sys
import os
import re


# file types to be processed
# ignore help .meta and .data files; ckeditor uses tabs, markdown uses 2 trailing blanks for line break
SELECTED_SUFFIXES = set("py bat cmd html css js styl less rst".split())

# stuff considered DOS/WIN that must have \r\n line endings
WIN_SUFFIXES = set("bat cmd".split())

# these are media files from help-common namespace
BINARY_FILES = tuple(".gz.data .zip.data .mp3.data .jpg.data .png.data .mp4.data".split())

# global variables for checking Javascript messages
phrases = set()
phrases_used = set()


class NoDupsLogger:
    """
    A simple report logger that suppresses duplicate headings and messages.
    """

    def __init__(self):
        self.messages = set()
        self.headings = set()

    def log(self, heading, message):
        if heading and heading not in self.headings:
            print("\n%s" % heading)
            self.headings.add(heading)

        if message and message not in self.messages:
            print("   ", message)
            self.messages.add(message)


def directories_to_ignore(starting_dir):
    """Return a list of directories that will not be processed."""
    # list format: [(fully qualified directory name, sub-directory name), ... ]
    ignore_dirs = []
    level2_dirs = ".eggs .git .tox contrib dlc env moin.egg-info wiki HTML".split()
    for dir in level2_dirs:
        ignore_dirs.append((starting_dir, dir))
    ignore_dirs.append((starting_dir + os.sep + "moin", "translations"))
    return ignore_dirs


def files_to_ignore():
    """Return a list of files that will not be processed."""
    return os.path.join("moin", "_version.py")


def calc_indentation(line):
    """
    Return tuple (length of indentation, line stripped of leading blanks).
    """
    stripped = line.lstrip(" ")
    indentation = len(line) - len(stripped)
    return indentation, stripped


def check_template_indentation(lines, filename, logger):
    """
    Identify non-standard indentation, print messages to assist user in manual correction.

    In simple cases, non-standard indent, non-standard dedent messages tells users which lines to indent.
    """
    indent_after = (
        "{% block ",
        "{% if ",
        "{% elif ",
        "{% else ",
        "{% for ",
        "{% macro ",
        "{%- block ",
        "{%- if ",
        "{%- elif ",
        "{%- else ",
        "{%- for ",
        "{%- macro ",
        "{{ gen.form.open",
    )
    indent_before = (
        "{% endblock ",
        "{% endif ",
        "{% endfor ",
        "{% endmacro",
        "</",
        "{%- endblock ",
        "{%- endif ",
        "{%- endfor ",
        "{%- endmacro",
        "{{ gen.form.close",
    )
    block_endings = {
        "{% block": ("{% endblock %}", "{%- endblock %}", "{%- endblock -%}", "{% endblock -%}"),
        "{% if": ("{% endif %}", "{%- endif %}", "{%- endif -%}", "{% endif -%}"),
        "{% elif": ("{% endif %}", "{%- endif %}", "{%- endif -%}", "{% endif -%}"),
        "{% else": ("{% endif %}", "{%- endif %}", "{%- endif -%}", "{% endif -%}"),
        "{% for": ("{% endfor %}", "{%- endfor %}", "{%- endfor -%}", "{% endfor -%}"),
        "{% macro": ("{% endmacro %}", "{%- endmacro %}", "{%- endmacro -%}", "{% endmacro -%}"),
        "{{ gen.form.open": ("{{ gen.form.close }}",),
    }
    ends = ("{% end", "{%- end")

    for idx, line in enumerate(lines):
        indentation, stripped = calc_indentation(line)

        if stripped.startswith(indent_after):
            # we have found the beginning of a block
            incre = 1
            try:
                while lines[idx + incre].strip() == "":
                    incre += 1
                next_indentation, next_line = calc_indentation(lines[idx + incre])
                if next_indentation <= indentation:
                    # next non-blank line does not have expected indentation
                    # truncate "{{ gen.form.open(form, ..." to "{{ gen.form.open"; "{%- if ..." to "{% if"
                    block_start = stripped.replace("-", "").split("(")[0].split(" ")
                    block_start = " ".join(block_start[:2])
                    block_end = block_endings.get(block_start)
                    if not block_end:
                        # should never get here, mismatched indent_after and block_endings
                        logger.log(
                            filename, "Unexpected block type '%s' discovered at line %d!" % (block_start, idx + 1)
                        )
                        continue
                    if any(x in stripped for x in block_end):
                        # found line similar to: {% block ... %}...{% endblock %}
                        continue
                    if any(x in lines[idx + incre] for x in block_end):
                        # found 2 consecutive lines similar to: {% block....\n{% endblock %}
                        continue
                    logger.log(filename, "Non-standard indent after line %d -- not fixed!" % (idx + 1))
            except IndexError:
                # should never get here, there is an unclosed block near end of template
                logger.log(filename, "End of file reached with open block element at line %d!" % (idx + 1))

        elif stripped.startswith(indent_before):
            # we have found the end of a block
            decre = -1
            while idx + decre >= 0 and lines[idx + decre].strip() == "":
                decre -= 1
            if idx + decre < 0:
                # should never get here; file begins with something like {% endblock %} or </div>
                logger.log(filename, "Beginning of file reached searching for block content at line %d!" % (idx + 1))
                continue
            prior_indentation, prior_line = calc_indentation(lines[idx + decre])
            if prior_indentation <= indentation:
                # prior non-blank line does not have expected indentation
                if stripped.startswith("</"):
                    tag_open = stripped.split(">")[0].replace("/", "")  # convert </div> to <div, etc.
                    if prior_line.startswith(tag_open):
                        # found lines similar to: <td>...\n</td>
                        continue
                if stripped.startswith(ends):
                    # convert end of block to prior beginning of block by removing "end" and any "-"s
                    block_end = stripped.split(" %}")[0].split(" -%}")[0].replace("end", "").replace("-", "")
                    prior_line = prior_line.replace("-", "")
                    if prior_line.startswith(block_end):
                        # found lines similar to: {% block...\n{% endblock %}
                        continue
                logger.log(filename, "Non-standard dedent before line %d -- not fixed!" % (idx + 1))


def check_template_spacing(lines, filename, logger):
    """
    Create message if there is not a blank afer {{, {%, {#, {{-, {%-, {#- and before }}, %}, #},  -}}, -%}, -#}.
    """
    pattern = re.compile(r"(\{[{#%])|([}#%]\})")
    for idx, line in enumerate(lines):
        # log missing spaces in {{-myfunction}}, {#mycomment-#}, {%-myoperator%}
        m = pattern.search(line)
        if m:
            m_start = [m.start() for m in re.finditer("{%|{{|{#", line)]
            for index in m_start:
                if not line.startswith((" ", "- "), index + 2) and not line.strip() in (
                    "{{",
                    "{%",
                    "{#",
                    "{{-",
                    "{%-",
                    "{#-",
                ):
                    logger.log(
                        filename,
                        'Missing space within "%s" on line %d - not fixed!' % (line[index : index + 4], idx + 1),
                    )
            m_end = [m.start() for m in re.finditer("%}|}}|#}", line)]
            for index in m_end:
                if not (line.startswith(" ", index - 1) or line.startswith(" -", index - 2)) and not line.strip() in (
                    "}}",
                    "%}",
                    "#}",
                    "-}}",
                    "-%}",
                    "-#}",
                ):
                    logger.log(
                        filename,
                        'Missing space within "%s" on line %d - not fixed!' % (line[index - 2 : index + 2], idx + 1),
                    )


def check_files(filename, suffix):
    """
    Delete trailing blanks, single linefeed at file end, line ending to be \r\n for bat files and \n for all others.
    """
    if filename.endswith(BINARY_FILES):
        return

    suffix = suffix.lower()
    if suffix in WIN_SUFFIXES:
        line_end = "\r\n"
    else:
        line_end = "\n"
    logger = NoDupsLogger()

    try:
        # newline="" does not change incoming line endings
        with open(filename, encoding="utf-8", newline="") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        print("Skipping file due to UnicodeDecodeError:", filename)
        return

    if filename.endswith(".html"):
        check_template_indentation(lines, filename, logger)
        check_template_spacing(lines, filename, logger)

    if filename.endswith(".js"):
        check_js_phrases(lines, filename)

    # now look at file end and get rid of all whitespace-only lines there:
    while lines:
        if not lines[-1].strip():
            del lines[-1]
            logger.log(filename, "Empty lines at eof removed.")
        else:
            break

    with open(filename, "w", encoding="utf-8", newline="") as f:
        for idx, line in enumerate(lines):
            line_length = len(line)
            line = line.replace("\t", "    ")
            if len(line) != line_length:
                logger.log(filename, "Tab characters replaced with 4 spaces.")
            pep8_line = line.rstrip() + line_end
            f.write(pep8_line)
            # if line was changed, issue warning once for each type of change
            if suffix in WIN_SUFFIXES and not line.endswith("\r\n"):
                logger.log(filename, "Line endings changed to DOS style.")
            elif suffix not in WIN_SUFFIXES and line.endswith("\r\n"):
                logger.log(filename, "Line endings changed to Unix style.")
            elif pep8_line != line:
                if len(pep8_line) < len(line):
                    logger.log(filename, "Trailing blanks removed.")
                else:
                    logger.log(filename, "End of line character added at end of file.")


def file_picker(starting_dir):
    """Select target files and pass each to file checker."""
    ignore_dirs = directories_to_ignore(starting_dir)
    ignore_files = files_to_ignore()

    for root, dirs, files in os.walk(starting_dir):
        # delete directories in ignore list
        for mama_dir, baby_dir in ignore_dirs:
            if mama_dir == root and baby_dir in dirs:
                dirs.remove(baby_dir)
        # check files with selected suffixes
        for file in files:
            suffix = file.split(".")[-1]
            if suffix in SELECTED_SUFFIXES:
                if file not in ignore_files:
                    filename = os.path.join(root, file)
                    check_files(filename, suffix)


def find_js_phrases(starting_dir):
    """
    Create a set of phrases defined in /templates/dictionary.js.

    Create warning message if key and value are not equal.
    """
    global phrases
    target = os.path.join(starting_dir, "moin", "templates", "dictionary.js")
    with open(target, encoding="utf-8") as f:
        lines = f.readlines()

    # "Cancel": "{{ _("Cancel") }}",
    pattern = r"""
        "
        (?P<key>[,\s]*[\w\s\d~`@#$%^&*()+=:;'<,>.?/!-?]+)
        "
        [:\s]*"\{\{\s*_\(
        "
        (?P<val>[,\s]*[\w\s\d~`@#$%^&*()+=:;'<,>.?/!-?]+)
        "
        \)\s\}\}",*
        """
    pattern = re.compile(pattern, re.X)

    for count, line in enumerate(lines, start=1):
        if "{{" not in line:
            continue
        m = pattern.search(line)
        if m:
            if not m.group("key") == m.group("val"):
                print("Error: /templates/dictionary.js dict has mismatched key and value on line", count)
                print("   ", line.lstrip())
            phrases.add(m.group("key"))
        else:
            print("Warning: /templates/dictionary.js {key: val} are not equal on line", count)
            print("   ", line.lstrip())


def check_js_phrases(lines, filename):
    """
    Check incoming js file for i18n phrases similar to: _("Hide comments")

    Print error message if not defined in phrases, else add phrase to used phrases set.
    """
    global phrases_used
    if filename.endswith("jquery.i18n.min.js") or filename.endswith("dictionary.js"):
        return
    pattern = re.compile(r"""_\("([\w\s\d~`@#$%^&*()+=:;'<,>.?/!-?]+)"\)""")
    bad_pat = re.compile(r"""_\(([\w\s\d~`@#$%^&*()+=:;'<,>.?/!-?]+)\)""")
    for count, line in enumerate(lines, start=1):
        if line.lstrip().startswith("// "):
            continue
        if line.lstrip().startswith("function "):
            continue
        if line.strip() == "return $.i18n._(text);":
            continue

        m = pattern.search(line)
        if m:
            if m.group(1) in phrases:
                phrases_used.add(m.group(1))
            else:
                print(
                    "Error: %s file at line %s has phrase not defined in /templates/dictionary.js." % (filename, count)
                )
                print("   ", line.lstrip())
        else:
            m = bad_pat.search(line)
            if m:
                # _(variablename)
                print("Warning: cannot verify i18n phrase defined in %s line %s." % (filename, count))
                print("   ", line.lstrip())


def unused_phrases():
    """
    Print error message it there are unused i18n phrases defined in /templates/dictionary.js.
    """
    unused = phrases - phrases_used
    if unused:
        for phrase in unused:
            print("Warning: unused phrase defined in /templates/dictionary.js:", phrase)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        starting_dir = os.path.abspath(sys.argv[1])
    else:
        starting_dir = os.path.abspath(os.path.dirname(__file__))
        starting_dir = os.path.join(starting_dir.split(os.sep + "scripts")[0], "src")
    NoDupsLogger().log("Starting directory is %s\n" % starting_dir, None)
    find_js_phrases(starting_dir)
    file_picker(starting_dir)
    unused_phrases()
